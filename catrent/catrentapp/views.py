import json
from pathlib import Path
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.db import transaction
from datetime import datetime
from datetime import timedelta
import os
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.management import call_command
from .utils import generate_operator_id
from .models import Machine, Rental, EquipmentHealth, Operator, UserProfile
from .forms import (
    MachineForm, CheckoutForm, OperatorForm, SignupForm,
    CatRentLoginForm, AdminSignupForm, ChangePasswordForm,
)
from .demand_forecasting import equipment_demand_forecast


def _candidate_project_dirs():
    return [
        Path(settings.BASE_DIR),
        Path.cwd(),
        Path('/Users/ayushmishra/Projects/cat-digital-2/catrent'),
    ]


def _resolve_existing_path(*parts):
    for base in _candidate_project_dirs():
        candidate = base.joinpath(*parts)
        if candidate.exists():
            return candidate
    return None


def _is_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        return user.userprofile.role == UserProfile.ROLE_ADMIN
    except UserProfile.DoesNotExist:
        return False


# ─── DECORATOR HELPERS ────────────────────────────────────────────────────────

def login_required_any(view_func):
    """Any logged-in user can access."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_required(view_func):
    """Only admin role can access this view."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if not _is_admin(request.user):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('operator_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def operator_required(view_func):
    """Any logged-in user can access (admin or operator)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ─── LOGIN ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        try:
            role = request.user.userprofile.role
            return redirect('rental_dashboard' if role == 'admin' else 'operator_dashboard')
        except Exception:
            return redirect('rental_dashboard')

    form = CatRentLoginForm(request, data=request.POST or None)
    error = None

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            try:
                profile = user.userprofile
            except UserProfile.DoesNotExist:
                # Fallback: create profile as admin if none exists
                profile = UserProfile.objects.create(user=user, role='admin')

            if profile.role == 'operator':
                try:
                    op = user.operator_profile
                    if op.must_change_password:
                        return redirect('change_password')
                except Exception:
                    pass
                return redirect('operator_dashboard')
            else:
                return redirect('rental_dashboard')
        else:
            error = "Invalid username or password. Please try again."

    return render(request, 'login.html', {'form': form, 'error': error})


# ─── ADMIN SIGNUP ─────────────────────────────────────────────────────────────

def admin_signup_view(request):
    """
    Only for creating admin accounts.
    Operators are NOT created here — they are created by admin adding an Operator record.
    This page requires a secret admin key to prevent public admin registrations.
    """
    if request.user.is_authenticated:
        return redirect('rental_dashboard')

    form = AdminSignupForm(request.POST or None)
    success = False

    if request.method == 'POST':
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'role': 'admin'}
            )
            success = True
            return redirect('login')

    return render(request, 'admin_signup.html', {'form': form, 'success': success})


# ─── LOGOUT ───────────────────────────────────────────────────────────────────

def logout_view(request):
    logout(request)
    return redirect('login')


# ─── CHANGE PASSWORD (forced on first operator login) ─────────────────────────

@login_required_any
def change_password_view(request):
    form = ChangePasswordForm(request.POST or None)
    error = None

    if request.method == 'POST':
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)

            # Mark must_change_password as False
            try:
                op = request.user.operator_profile
                op.must_change_password = False
                op.save()
            except Exception:
                pass

            return redirect('operator_dashboard')
        else:
            error = "Passwords do not match. Please try again."

    return render(request, 'change_password.html', {'form': form, 'error': error})


# ─── OPERATOR DASHBOARD ──────────────────────────────────────────────────────

@operator_required
def operator_dashboard(request):
    try:
        operator = request.user.operator_profile
    except Exception:
        # Logged-in user has no operator profile — show all if admin, else show error
        if _is_admin(request.user):
            rented_qs = Rental.objects.filter(active=True, status='Active').select_related('machine')
            rented = []
            for rental in rented_qs:
                rented.append({
                    'rental': rental,
                    'health': rental.machine.health_records.order_by('-timestamp').first(),
                })
            return render(request, 'operator_dashboard.html', {
                'rented': rented,
            })
        return render(request, 'operator_dashboard.html', {
            'error': 'No operator profile linked to your account. Contact admin.',
            'rented': [],
        })

    # Only show THIS operator's active rentals
    active_rentals = Rental.objects.filter(
        operator_id=operator.operator_id,
        active=True,
        status='Active'
    ).select_related('machine')

    rented = []
    kpi_total = 0
    kpi_overdue = 0
    kpi_due_today = 0
    kpi_due_soon = 0
    
    now = timezone.now()

    for rental in active_rentals:
        kpi_total += 1
        
        # Calculate days remaining (using .days truncates time)
        if rental.expected_end_date:
            days_remaining = (rental.expected_end_date.date() - now.date()).days
        else:
            days_remaining = 0
            
        if days_remaining < 0:
            urgency = 'overdue'
            kpi_overdue += 1
        elif days_remaining == 0:
            urgency = 'due_today'
            kpi_due_today += 1
        elif days_remaining <= 2:
            urgency = 'due_soon'
            kpi_due_soon += 1
        else:
            urgency = 'on_track'

        rented.append({
            'rental': rental,
            'health': rental.machine.health_records.order_by('-timestamp').first(),
            'urgency': urgency,
            'days_remaining': days_remaining,
        })

    available_machines = Machine.objects.filter(status='Available')

    return render(request, 'operator_dashboard.html', {
        'operator': operator,
        'rented': rented,
        'available_machines': available_machines,
        'user': request.user,
        'kpi_total': kpi_total,
        'kpi_overdue': kpi_overdue,
        'kpi_due_today': kpi_due_today,
        'kpi_due_soon': kpi_due_soon,
    })


# ─── ADMIN VIEWS ─────────────────────────────────────────────────────────────

@admin_required
def add(request):
    """Add and list machines"""
    machines = Machine.objects.all()
    if request.method == "POST":
        form = MachineForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Machine added successfully!')
                return redirect("add")
            except Exception as e:
                messages.error(request, 'Error adding machine.')
    else:
        form = MachineForm()
    return render(request, "add_machine.html", {"machines": machines, "form": form})


@admin_required
def delete_machine(request, pk):
    """Delete a machine"""
    try:
        machine = get_object_or_404(Machine, pk=pk)
        machine.delete()
        messages.success(request, 'Machine deleted successfully!')
    except Exception as e:
        messages.error(request, 'Error deleting machine.')
    return redirect("add")


@admin_required
def download_qr(request, pk):
    """Download QR code image"""
    machine = get_object_or_404(Machine, pk=pk)
    if not machine.qr_code:
        return HttpResponse("No QR code available for this equipment.")
    
    try:
        # Use open() which works for both local and remote storage (Cloudinary)
        with machine.qr_code.open("rb") as f:
            response = HttpResponse(f.read(), content_type="image/png")
            response["Content-Disposition"] = f'attachment; filename="qr_{machine.equipment_id}.png"'
            return response
    except Exception as e:
        # Fallback for older records or storage issues: try to fetch via URL if possible
        try:
            import requests
            resp = requests.get(machine.qr_code.url)
            if resp.status_code == 200:
                response = HttpResponse(resp.content, content_type="image/png")
                response["Content-Disposition"] = f'attachment; filename="qr_{machine.equipment_id}.png"'
                return response
        except:
            pass
        return HttpResponse(f"Error accessing QR code file: {str(e)}")


@admin_required
def rental_dashboard(request):
    """Dashboard showing rented, available machines and health chart"""
    is_admin = _is_admin(request.user)
    try:
        selected_forecast_type = request.GET.get('forecast_type', 'Bulldozer')
        forecast_cache_buster = timezone.now().strftime('%Y%m%d%H%M%S')
        # Rented machines
        rented_qs = Rental.objects.filter(active=True, status='Active').select_related('machine')
        rented = []
        
        # Count for rented machines by type
        rented_bulldozer_count = 0
        rented_excavator_count = 0
        rented_loader_count = 0
        rented_crane_count = 0
        
        for rental in rented_qs:
            latest_health = rental.machine.health_records.order_by('-timestamp').first()
            rented.append({
                "rental": rental,
                "health": latest_health,
            })
            
            # Count by machine type
            machine_type = rental.machine.type
            if machine_type == 'Bulldozer':
                rented_bulldozer_count += 1
            elif machine_type == 'Excavator':
                rented_excavator_count += 1
            elif machine_type == 'Loader':
                rented_loader_count += 1
            elif machine_type == 'Crane':
                rented_crane_count += 1

        # Available machines
        available = Machine.objects.filter(status='Available')
        
        # Count machines by type
        bulldozer_count = available.filter(type='Bulldozer').count()
        excavator_count = available.filter(type='Excavator').count()
        loader_count = available.filter(type='Loader').count()
        crane_count = available.filter(type='Crane').count()

        # Latest health per machine (cross-db safe)
        latest_health_records = []
        for machine in Machine.objects.all():
            latest = machine.health_records.order_by('-timestamp').first()
            if latest:
                latest_health_records.append(latest)

        # Health chart data
        health_counts = {'Good':0, 'Warning':0, 'Critical':0, 'Maintenance Required':0}
        for h in latest_health_records:
            if h.status in health_counts:
                health_counts[h.status] += 1
        health_chart_data = {
            "labels": list(health_counts.keys()),
            "data": list(health_counts.values())
        }

        return render(request, "rental_dashboard.html", {
            "rented": rented,
            "available": available,
            "health_chart_data": json.dumps(health_chart_data),
            "selected_forecast_type": selected_forecast_type,
            "forecast_cache_buster": forecast_cache_buster,
            "bulldozer_count": bulldozer_count,
            "excavator_count": excavator_count,
            "loader_count": loader_count,
            "crane_count": crane_count,
            "rented_bulldozer_count": rented_bulldozer_count,
            "rented_excavator_count": rented_excavator_count,
            "rented_loader_count": rented_loader_count,
            "rented_crane_count": rented_crane_count,
            "is_admin": is_admin,
        })

    except Exception as e:
        selected_forecast_type = request.GET.get('forecast_type', 'Bulldozer')
        forecast_cache_buster = timezone.now().strftime('%Y%m%d%H%M%S')
        messages.error(request, 'Error loading dashboard.')
        return render(request, "rental_dashboard.html", {
            "rented": [],
            "available": [],
            "health_chart_data": json.dumps({"labels": [], "data": []}),
            "selected_forecast_type": selected_forecast_type,
            "forecast_cache_buster": forecast_cache_buster,
            "bulldozer_count": 0,
            "excavator_count": 0,
            "loader_count": 0,
            "crane_count": 0,
            "rented_bulldozer_count": 0,
            "rented_excavator_count": 0,
            "rented_loader_count": 0,
            "rented_crane_count": 0,
            "is_admin": is_admin,
        })


@admin_required
def rent_machine(request, machine_id): 
    """Rent a machine manually""" 
    machine = get_object_or_404(Machine, equipment_id=machine_id) 
    if machine.status == 'Rented':
        messages.error(request, 'Machine already rented!') 
        return redirect("rental_dashboard") 
    if request.method == "POST": 
        operator_id = request.POST.get("operator_id") 
        operator_name = request.POST.get("operator_name", "Unknown") 
        site_id = request.POST.get("site_id") 
        site_name = request.POST.get("site_name", "") 
        days = int(request.POST.get("days", 1)) 
        expected_end_date = timezone.now() + timedelta(days=days) 
        rental = Rental.objects.create( 
            machine=machine, 
            operator_id=operator_id, 
            operator_name=operator_name, 
            site_id=site_id, 
            site_name=site_name, 
            expected_end_date=expected_end_date, 
            active=True, 
            status='Active' 
        ) 
        machine.status = 'Rented' 
        machine.save() 
        messages.success(request, f'Machine {machine.equipment_id} rented successfully!') 
        return redirect("rental_dashboard") 
    return render(request, "rent_machine.html", {"machine": machine})


@operator_required
def qr_scan_info(request, equipment_id):
    """QR scan checkout for admins and operators"""
    machine = get_object_or_404(Machine, equipment_id=equipment_id)
    current_rental = machine.current_rental

    # Keep machine.status aligned with active rental state
    if current_rental and machine.status != 'Rented':
        machine.status = 'Rented'
        machine.save(update_fields=['status'])
    elif not current_rental and machine.status == 'Rented':
        machine.status = 'Available'
        machine.save(update_fields=['status'])

    machine_display_status = 'Rented' if current_rental else machine.status

    # Get all operators and prepare JSON for JS
    operators = Operator.objects.all()
    operators_json = json.dumps([
        {"id": op.operator_id, "name": op.name, "email": op.email}
        for op in operators
    ])

    # Check if current user is an operator and get prefill info
    operator_prefill = None
    is_operator_role = False
    try:
        if request.user.userprofile.role == 'operator':
            operator_prefill = request.user.operator_profile
            is_operator_role = True
    except Exception:
        pass

    # If machine is already rented
    if current_rental:
        return render(request, 'checkout.html', {
            'machine': machine,
            'machine_display_status': machine_display_status,
            'current_rental': current_rental,
            'is_already_rented': True,
            'operators': operators,
            'operators_json': operators_json,
            'operator_prefill': operator_prefill,
            'is_operator_role': is_operator_role,
        })

    # POST - create rental
    if request.method == "POST":
        # If operator role, force their own operator_id regardless of POST data
        if is_operator_role and operator_prefill:
            operator_id = operator_prefill.operator_id
        else:
            operator_id = request.POST.get("operator_id")

        operator = Operator.objects.get(operator_id=operator_id)

        site_id = request.POST.get("site_id")
        site_name = request.POST.get("site_name", "")

        # Convert strings from datetime-local input to aware datetime objects
        checkout_date_str = request.POST.get("checkout_date")
        expected_return_date_str = request.POST.get("expected_return_date")
        
        # GPS Coordinates
        checkout_lat = request.POST.get("checkout_lat")
        checkout_lng = request.POST.get("checkout_lng")

        checkout_date = timezone.make_aware(datetime.strptime(checkout_date_str, "%Y-%m-%dT%H:%M"))
        expected_return_date = timezone.make_aware(datetime.strptime(expected_return_date_str, "%Y-%m-%dT%H:%M"))

        # Create Rental
        rental = Rental.objects.create(
            machine=machine,
            operator_id=operator.operator_id,
            operator_name=operator.name,
            site_id=site_id,
            site_name=site_name,
            start_date=checkout_date,
            expected_end_date=expected_return_date,
            active=True,
            status='Active',
            checkout_lat=float(checkout_lat) if checkout_lat else None,
            checkout_lng=float(checkout_lng) if checkout_lng else None,
        )

        # Update machine status
        machine.status = 'Rented'
        machine.save()

        messages.success(request, f'Equipment {machine.equipment_id} checked out!')
        if is_operator_role:
            return redirect('operator_dashboard')
        return redirect('rental_dashboard')

    # GET - show checkout form
    else:
        initial_data = {
            'equipment_id': machine.equipment_id,
            'type': machine.type,
            'status': machine_display_status,
            'checkout_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
        }
        # Pre-fill operator fields if operator is logged in
        if is_operator_role and operator_prefill:
            initial_data['operator_id'] = operator_prefill.operator_id
            initial_data['operator_name'] = operator_prefill.name
        form = CheckoutForm(initial=initial_data)

    return render(request, 'checkout.html', {
        'machine': machine,
        'machine_display_status': machine_display_status,
        'form': form,
        'is_already_rented': False,
        'operators': operators,
        'operators_json': operators_json,
        'operator_prefill': operator_prefill,
        'is_operator_role': is_operator_role,
    })


@csrf_exempt  # We'll handle CSRF in JS fetch headers
@operator_required
def checkin_machine(request, rental_id):
    """
    Check-in a rented machine after QR validation.
    Expects POST with optional equipment_id for double validation.
    """
    rental = get_object_or_404(Rental, id=rental_id)

    if request.method == "POST":
        # Authorization check: if operator role, verify this rental belongs to them
        try:
            profile = request.user.userprofile
            if profile.role == 'operator':
                try:
                    operator = request.user.operator_profile
                    if rental.operator_id != operator.operator_id:
                        return JsonResponse({
                            'success': False,
                            'message': 'Unauthorized: This rental is not assigned to you.'
                        }, status=403)
                except Exception:
                    return JsonResponse({
                        'success': False,
                        'message': 'Operator profile missing.'
                    }, status=403)
        except Exception:
            pass

        # Get equipment ID from POST for validation
        equipment_id = request.POST.get("scanned_equipment_id", None)
        if not equipment_id:
            equipment_id = request.POST.get("equipment_id", None)
            
        if equipment_id and equipment_id != rental.machine.equipment_id:
            return JsonResponse({
                "success": False,
                "message": "Equipment ID does not match. Check-in failed!"
            }, status=400)

        rental.active = False
        rental.status = 'Completed'
        rental.actual_end_date = timezone.now()
        rental.machine.status = 'Available'
        rental.machine.save()
        rental.save()

        return JsonResponse({
            "success": True,
            "message": f"Machine {rental.machine.equipment_id} checked in successfully!"
        })

    return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)


@admin_required
def manual_regenerate_qr(request):
    """Manual trigger for QR regeneration since Shell is not available on Free Tier."""
    from django.core.management import call_command
    from django.conf import settings
    import io
    import os

    out = io.StringIO()
    
    # Debug variables
    c_name = os.getenv('CLOUDINARY_CLOUD_NAME', 'MISSING')
    c_key = os.getenv('CLOUDINARY_API_KEY', 'MISSING')
    c_secret = os.getenv('CLOUDINARY_API_SECRET', 'MISSING')
    
    # Check if storage is actually Cloudinary
    from django.core.files.storage import default_storage
    storage_class = default_storage.__class__.__name__
    
    debug_info = f"Storage: {storage_class} | Name: {c_name[:3]}... | Key: {c_key[:3]}... | Secret: {c_secret[:3]}..."
    
    try:
        call_command('regenerate_qr', stdout=out)
        output = out.getvalue()
        messages.success(request, f"QR Regeneration complete! {debug_info}")
        print(f"QR Regeneration Output:\n{output}")
    except Exception as e:
        messages.error(request, f"Error: {str(e)} | {debug_info}")
    
    return redirect('rental_dashboard')


@require_POST
@admin_required
def send_rental_reminders(request):
    """Send rental reminders manually"""
    try:
        from django.core.management import call_command
        import io
        import sys
        
        out = io.StringIO()
        err = io.StringIO()
        
        # Try to send reminders
        call_command('send_rental_remainders', stdout=out, stderr=err)
        
        output = out.getvalue()
        errors = err.getvalue()
        
        if errors:
            print(f"[REMINDER] Errors: {errors}", file=sys.stderr)
        
        if output:
            print(f"[REMINDER] Output: {output}", file=sys.stderr)
        
        messages.success(request, 'Rental reminders processed for today.')
    except BaseException as e:
        import traceback
        import sys
        error_msg = f"Failed to send reminders: {str(e)}"
        print(f"[REMINDER ERROR] {error_msg}", file=sys.stderr)
        traceback_str = traceback.format_exc()
        print(f"[REMINDER TRACEBACK] {traceback_str}", file=sys.stderr)
        messages.error(request, error_msg)
    
    return redirect('rental_dashboard')


@admin_required
def generate_forecast(request, equipment_type):
    """Generate demand forecast for a specific equipment type"""
    try:
        # Create forecast directory if it doesn't exist
        forecast_dir = os.path.join(settings.BASE_DIR, 'forecast')
        os.makedirs(forecast_dir, exist_ok=True)
        
        # Get data from the Rental model
        rentals = Rental.objects.all().select_related('machine')
        
        # Convert to DataFrame
        data = []
        for rental in rentals:
            # Build a data dictionary with required fields for forecasting
            # Only include fields that definitely exist in the model
            rental_data = {
                'equipment_id': rental.machine.equipment_id,
                'equipment_type': rental.machine.type,
                'checkout_date': rental.start_date,
                'checkin_date': rental.expected_end_date if rental.expected_end_date else rental.actual_end_date,
                'site_id': rental.site_id,
                'rate_per_day': float(rental.rate_per_day) if hasattr(rental, 'rate_per_day') else 0.0,
                'year_week': rental.week if hasattr(rental, 'week') else datetime.now().strftime("%Y-W%U")
            }
            
            # Add optional fields if they exist
            if hasattr(rental, 'maintenance'):
                rental_data['maintenance_count'] = rental.maintenance
            
            if hasattr(rental, 'engine_hours'):
                rental_data['engine_hours'] = rental.engine_hours
                
            if hasattr(rental, 'idle_hours'):
                rental_data['idle_hours'] = rental.idle_hours
                
            # Add demand forecast specific fields
            for field in [
                'target_checkout_count', 'checkout_count_t_1', 'checkout_count_t_4',
                'rolling_mean_4w', 'price_index', 'pct_maint', 'engine_hours_avg',
                'idle_ratio_avg', 'equipment_type_encoded', 'usage_efficiency',
                'rental_duration', 'rate_relative', 'recent_maintenance',
                'maintenance_per_day', 'engine_hours_per_day', 'month_sin',
                'month_cos', 'week_sin', 'week_cos', 'rolling_std_4w', 'rolling_max_4w'
            ]:
                if hasattr(rental, field) and getattr(rental, field) is not None:
                    # Use the actual field name in the model (t_1 vs t-1)
                    actual_field = field.replace('-', '_') if '-' in field else field
                    rental_data[field] = getattr(rental, actual_field)
            
            data.append(rental_data)
        
        df = pd.DataFrame(data)
        
        # Only proceed if we have data
        if len(df) == 0:
            return JsonResponse({
                'status': 'error',
                'message': 'No rental data available for forecasting'
            })
        
        # Generate forecast
        forecast_result = equipment_demand_forecast(df, output_folder=forecast_dir)
        
        # Log successful forecast generation
        print(f"Successfully generated forecast for {equipment_type}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Forecast generated for {equipment_type}',
            'image_url': f'/forecast_image/{equipment_type}/',
        })
        
    except Exception as e:
        import traceback
        print(f"Error generating forecast for {equipment_type}: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Error generating forecast: {str(e)}'
        }, status=500)


@login_required_any
def get_forecast_image(request, equipment_type):
    """Return the forecast image for a specific equipment type"""
    image_path = _resolve_existing_path('forecast', f"{equipment_type}_demand_forecast_2025.png")
    
    if not image_path:
        # Try fallbacks
        image_path = _resolve_existing_path('forecast', "equipment_demand_forecast_2025_combined.png")
    
    if not image_path:
        image_path = _resolve_existing_path('forecast', "feature_importance.png")

    if image_path and image_path.exists():
        size = image_path.stat().st_size
        print(f"[DEBUG] Serving forecast image: {image_path} ({size} bytes)")
        
        # Use open explicitly and set content_length
        f = open(image_path, 'rb')
        response = FileResponse(f, content_type='image/png')
        response['Content-Length'] = size
        response['Cache-Control'] = 'public, max-age=3600' # Cache for 1 hour
        return response

    print(f"[ERROR] Forecast image not found for type: {equipment_type}")
    return HttpResponse("Forecast image not found. Please generate a forecast first.", status=404)


@admin_required
def operator_list_api(request):
    search = request.GET.get('search', '').lower()
    status_filter = request.GET.get('status', 'all')
    
    operators = Operator.objects.all().order_by('-created_at')
    
    if search:
        from django.db.models import Q
        operators = operators.filter(
            Q(name__icontains=search) | 
            Q(operator_id__icontains=search) | 
            Q(email__icontains=search)
        )
        
    stats = {
        'total': operators.count(),
        'active': operators.filter(is_active=True, user__isnull=False).count(),
        'pending': operators.filter(user__isnull=True).count(),
        'deactivated': operators.filter(is_active=False).count()
    }
    
    if status_filter == 'active':
        operators = operators.filter(is_active=True, user__isnull=False)
    elif status_filter == 'pending':
        operators = operators.filter(user__isnull=True)
    elif status_filter == 'deactivated':
        operators = operators.filter(is_active=False)

    data = []
    for op in operators:
        # Only count rentals after the operator was created to avoid reused IDs inflating totals
        rentals_qs = Rental.objects.filter(operator_id=op.operator_id, start_date__gte=op.created_at)
        active_rentals = rentals_qs.filter(active=True).count()
        total_rentals = rentals_qs.count()
        
        status = 'Active' if op.is_active else 'Deactivated'
        if not op.user:
            status = 'No Account'
        elif op.must_change_password:
            status = 'Pending'
            
        data.append({
            'id': op.id,
            'operator_id': op.operator_id,
            'name': op.name,
            'email': op.email,
            'phone': op.phone or '',
            'site_location': op.site_location or '',
            'designation': op.designation or '',
            'is_active': op.is_active,
            'status': status,
            'active_rentals': active_rentals,
            'total_rentals': total_rentals,
            'created_at': op.created_at.strftime("%b %d, %Y"),
        })
        
    return JsonResponse({'stats': stats, 'operators': data})

@admin_required
@csrf_exempt
@require_POST
def operator_save_api(request):
    data = json.loads(request.body)
    op_id = data.get('id')
    email = data.get('email').strip().lower()
    
    # check email unique
    email_query = Operator.objects.filter(email=email)
    if op_id:
        email_query = email_query.exclude(id=op_id)
    if email_query.exists():
        return JsonResponse({'success': False, 'message': 'Email already exists.'})
        
    if op_id:
        op = get_object_or_404(Operator, id=op_id)
        
        is_active = data.get('is_active', True)
        if not is_active and op.is_active:
            active_rentals = Rental.objects.filter(operator_id=op.operator_id, active=True).count()
            if active_rentals > 0:
                return JsonResponse({'success': False, 'message': 'Cannot deactivate operator with active rentals.'})
                
        op.name = data.get('name')
        op.email = email
        op.phone = data.get('phone')
        op.site_location = data.get('site_location')
        op.designation = data.get('designation')
        op.is_active = is_active
        op.save()
        
        if op.user:
            op.user.email = email
            op.user.is_active = is_active
            op.user.save()
            
        return JsonResponse({'success': True, 'message': 'Operator updated successfully.'})
    else:
        op = Operator(
            operator_id=generate_operator_id(),
            name=data.get('name'),
            email=email,
            phone=data.get('phone'),
            site_location=data.get('site_location'),
            designation=data.get('designation'),
            is_active=data.get('is_active', True)
        )
        op.save()
        return JsonResponse({'success': True, 'message': 'Operator added successfully. Email sent.'})

@admin_required
@csrf_exempt
def operator_delete_api(request, operator_id):
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
        
    op = get_object_or_404(Operator, id=operator_id)
    
    active_rentals_count = Rental.objects.filter(operator_id=op.operator_id, active=True).count()
    if active_rentals_count > 0:
        return JsonResponse({'success': False, 'message': 'Cannot delete operator with active rentals.'})
        
    if op.user:
        op.user.delete()
        
    op.delete()
    return JsonResponse({'success': True, 'message': 'Operator deleted successfully.'})

@admin_required
@csrf_exempt
@require_POST
def operator_reset_credentials_api(request, operator_id):
    op = get_object_or_404(Operator, id=operator_id)
    
    if not op.user:
        return JsonResponse({'success': False, 'message': 'Operator has no user account.'})
        
    from .models import generate_secure_password
    raw_password = generate_secure_password()
    
    op.user.set_password(raw_password)
    op.user.save()
    
    op.must_change_password = True
    op.save()
    
    try:
        from django.core.mail import send_mail
        send_mail(
            subject="Your CatRent Operator Password has been reset",
            message=f"Hi {op.name},\n\nYour CatRent operator password has been reset.\n\nUsername: {op.user.username}\nNew Password: {raw_password}\n\nPlease log in and change your password.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[op.email],
            fail_silently=False,
        )
        return JsonResponse({'success': True, 'message': 'Credentials reset and email sent.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Password reset but email failed: {str(e)}'})


@admin_required
def anomaly_dashboard(request):
    """Display the anomaly monitoring dashboard"""
    return render(request, "rental_dashboard.html")


@admin_required
def anomaly_data(request):
    """API endpoint to serve anomaly data as JSON"""
    try:
        anomaly_file_path = _resolve_existing_path('detailed_anomaly_report.json')
        if not anomaly_file_path:
            return JsonResponse({"error": "Anomaly data file not found"}, status=404)

        with open(anomaly_file_path, 'r') as file:
            anomaly_data = json.load(file)

        limited_data = anomaly_data[:100] if len(anomaly_data) > 100 else anomaly_data

        return JsonResponse(limited_data, safe=False)
        
    except FileNotFoundError:
        return JsonResponse({"error": "Anomaly data file not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format in anomaly data file"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Error loading anomaly data: {str(e)}"}, status=500)
