from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from catrentapp.models import Operator, UserProfile, generate_secure_password
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Create login accounts for all existing operators who have no user linked'

    def handle(self, *args, **kwargs):
        operators = Operator.objects.filter(user__isnull=True)
        self.stdout.write(f"Found {operators.count()} operators without accounts.")

        for op in operators:
            username = op.operator_id
            if User.objects.filter(username=username).exists():
                username = f"{username}_{op.pk}"

            raw_password = generate_secure_password()
            user = User.objects.create_user(
                username=username,
                email=op.email,
                password=raw_password
            )
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'role': 'operator'}
            )
            Operator.objects.filter(pk=op.pk).update(
                user=user,
                must_change_password=True
            )

            try:
                send_mail(
                    subject="Your CatRent Operator Account is Ready",
                    message=f"""Hi {op.name},

Your CatRent operator account has been set up.

Login at: {settings.SITE_URL}/login/

Username : {username}
Password : {raw_password}

Please log in and change your password immediately.

— CatRent System
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[op.email],
                    fail_silently=True,
                )
                self.stdout.write(self.style.SUCCESS(
                    f"[OK] Created account for {op.name} ({username}) -- email sent"
                ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"[OK] Created account for {op.name} ({username}) -- email FAILED: {e}"
                ))

        self.stdout.write(self.style.SUCCESS("Done."))
