from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Machine, Rental, EquipmentUsage, Operator, UserProfile

class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = ['equipment_id', 'type', 'rate_per_day']
        widgets = {
            'equipment_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., EQX1001'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
        }


class RentalForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = ['operator_id', 'operator_name', 'site_id', 'site_name', 'expected_end_date']
        widgets = {
            'operator_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Operator ID'}),
            'operator_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Operator Name'}),
            'site_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Site ID'}),
            'site_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Site Name'}),
            'expected_end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class UsageLogForm(forms.ModelForm):
    class Meta:
        model = EquipmentUsage
        fields = ['engine_hours', 'idle_hours', 'fuel_consumed', 'distance_traveled', 'work_type', 'notes']
        widgets = {
            'engine_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'idle_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fuel_consumed': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'distance_traveled': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'work_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type of work performed'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CheckoutForm(forms.Form):
    equipment_id = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    type = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    status = forms.CharField(
        max_length=50, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    operator_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Operator ID', 'required': True})
    )
    operator_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Operator Name', 'required': True})
    )
    site_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Site ID', 'required': True})
    )
    site_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Site Name (optional)'})
    )
    checkout_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local', 'required': True})
    )
    expected_return_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local', 'required': True})
    )


class OperatorForm(forms.ModelForm):
    class Meta:
        model = Operator
        fields = ['name', 'email']


# --- Login form (used by both admin and operator) ---
class CatRentLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Username or Operator ID',
            'class': 'form-input',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-input',
        })
    )


# --- Admin signup form (admin only, not for operators) ---
class AdminSignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-input',
        }),
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm Password',
            'class': 'form-input',
        })
    )
    admin_secret_key = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Admin Registration Key',
            'class': 'form-input',
        }),
        help_text="Required to create an admin account."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Username',
                'class': 'form-input',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Email Address',
                'class': 'form-input',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        secret = cleaned.get('admin_secret_key')

        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")

        # Admin secret key check — set this in settings.py as ADMIN_SIGNUP_KEY
        from django.conf import settings
        if secret != getattr(settings, 'ADMIN_SIGNUP_KEY', 'catrent-admin-2024'):
            raise forms.ValidationError(
                "Invalid admin registration key. Contact system administrator."
            )
        return cleaned


# --- Change password form (forced on first operator login) ---
class ChangePasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'New Password',
            'class': 'form-input',
        }),
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm New Password',
            'class': 'form-input',
        })
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


# --- Legacy signup form (kept for compatibility but no longer used) ---
class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email is already in use.')
        return email
