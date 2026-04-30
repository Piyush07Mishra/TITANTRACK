from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from .models import Machine, Rental, EquipmentUsage, EquipmentHealth, Operator, UserProfile, generate_secure_password


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0

# -----------------------------
# Machine Admin
# -----------------------------
@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('equipment_id', 'type', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'type')
    search_fields = ('equipment_id', 'type')
    readonly_fields = ('qr_code', 'created_at', 'updated_at')

# -----------------------------
# Rental Admin
# -----------------------------
@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ('rental_id', 'machine', 'operator_name', 'site_name', 'start_date', 'expected_end_date', 'actual_end_date', 'status', 'active')
    list_filter = ('status', 'active', 'start_date')
    search_fields = ('rental_id', 'machine__equipment_id', 'operator_name', 'site_name')
    readonly_fields = ('rental_id', 'created_at', 'updated_at')

# -----------------------------
# Equipment Usage Admin
# -----------------------------
@admin.register(EquipmentUsage)
class EquipmentUsageAdmin(admin.ModelAdmin):
    list_display = ('machine', 'rental', 'date', 'engine_hours', 'idle_hours', 'fuel_consumed', 'distance_traveled', 'productivity_score')
    list_filter = ('date', 'machine')
    search_fields = ('machine__equipment_id', 'rental__rental_id', 'operator_id', 'site_id')

# -----------------------------
# Equipment Health Admin
# -----------------------------
@admin.register(EquipmentHealth)
class EquipmentHealthAdmin(admin.ModelAdmin):
    list_display = ('machine', 'component', 'status', 'engine_temperature', 'fuel_level', 'battery_voltage', 'severity', 'timestamp', 'resolved')
    list_filter = ('status', 'component', 'resolved')
    search_fields = ('machine__equipment_id', 'component', 'alert_message')


# -----------------------------
# Admin action: Reset & resend login credentials
# -----------------------------
def resend_credentials(modeladmin, request, queryset):
    """Admin action to reset and resend login credentials."""
    for operator in queryset:
        if operator.user:
            new_password = generate_secure_password()
            operator.user.set_password(new_password)
            operator.user.save()
            operator.must_change_password = True
            operator.save()

            send_mail(
                subject="CatRent — Your Login Credentials Have Been Reset",
                message=f"""Hi {operator.name},

Your CatRent password has been reset by the administrator.

Username : {operator.operator_id}
Password : {new_password}

Please log in and change your password immediately.

— CatRent System
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[operator.email],
                fail_silently=True,
            )

resend_credentials.short_description = "Reset & resend login credentials via email"


# -----------------------------
# Operator Admin
# -----------------------------
@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = [
        'operator_id', 'name', 'email',
        'is_active', 'account_status', 'created_at'
    ]
    readonly_fields = ['user', 'login_info', 'created_at']
    actions = [resend_credentials]

    def login_info(self, obj):
        if obj.user:
            status = "⚠ Awaiting password change" if obj.must_change_password else "✓ Active"
            return f"Username: {obj.operator_id} | Status: {status}"
        return "No account created yet"
    login_info.short_description = "Login Account Info"

    def account_status(self, obj):
        if not obj.user:
            return "No Account"
        return "Pending Password Change" if obj.must_change_password else "Active"
    account_status.short_description = "Account Status"


# -----------------------------
# User Admin with Profile Inline
# -----------------------------
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
