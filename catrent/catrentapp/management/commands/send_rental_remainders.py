from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from catrentapp.models import Rental, Operator
from django.conf import settings
from datetime import timedelta
from pathlib import Path
import json
import os

# Run frequently and notify only for due-today rentals.
REMINDER_DAYS = [0]


def _cache_path():
    # Try to use a temp directory on Render, fallback to BASE_DIR
    temp_dir = os.environ.get('TMPDIR') or os.environ.get('TEMP') or os.path.expanduser('~/.tmp')
    if os.path.isdir(temp_dir) and os.access(temp_dir, os.W_OK):
        return Path(temp_dir) / ".reminder_sent_cache.json"
    # Fallback to BASE_DIR
    base_path = Path(settings.BASE_DIR) / ".reminder_sent_cache.json"
    if os.access(Path(settings.BASE_DIR), os.W_OK):
        return base_path
    # Last resort: use memory (dict stored in module, won't persist across restarts)
    return None


_memory_cache = {}


def _load_sent_cache():
    path = _cache_path()
    if path is None:
        return _memory_cache
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"[DEBUG] Error reading cache file: {e}, using memory cache instead")
        return _memory_cache


def _save_sent_cache(data):
    global _memory_cache
    _memory_cache = data  # Always save to memory
    
    path = _cache_path()
    if path is None:
        return
    try:
        path.write_text(json.dumps(data, indent=2, sort_keys=True))
    except Exception as e:
        print(f"[DEBUG] Error writing cache file: {e}, using memory cache instead")

class Command(BaseCommand):
    help = "Send email reminders to operators for upcoming rental check-ins (no logging)"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        today_key = today.isoformat()
        sent_cache = _load_sent_cache()
        print(f"[DEBUG] Today is {today}")

        for days_before in REMINDER_DAYS:
            reminder_date = today + timedelta(days=days_before)
            print(f"[DEBUG] Checking rentals for reminder in {days_before} days (reminder_date={reminder_date})")

            rentals_due = Rental.objects.filter(
                active=True,
                expected_end_date__date=reminder_date
            )

            if not rentals_due.exists():
                print(f"[DEBUG] No rentals due on {reminder_date}")
                continue

            for rental in rentals_due:
                print(f"[DEBUG] Found rental {rental.rental_id}, machine {rental.machine.equipment_id}")

                reminder_key = f"{rental.rental_id}:{today_key}"
                if reminder_key in sent_cache:
                    print(f"[DEBUG] Reminder already sent today for rental {rental.rental_id}, skipping")
                    continue

                # Get operator email
                operator = Operator.objects.filter(operator_id=rental.operator_id).first()
                if not operator or not operator.email:
                    print(f"[DEBUG] No email found for rental {rental.rental_id}")
                    continue

                operator_email = operator.email

                # Email content
                if days_before == 0:
                    subject_prefix = "Today: "
                    message_intro = "This is a reminder that your rental is due today"
                else:
                    subject_prefix = f"In {days_before} days: "
                    message_intro = f"This is a reminder that your rental is due in {days_before} days"

                subject = f"{subject_prefix}Rental {rental.rental_id} check-in"
                message = f"""
Hello {rental.operator_name},

{message_intro} for machine {rental.machine.equipment_id} ({rental.machine.type}) 
scheduled for check-in on {rental.expected_end_date.strftime('%Y-%m-%d %H:%M')}.

Please ensure the equipment is returned on time.

Thank you,
CatRent Team
"""

                print(f"[DEBUG] Sending email to {operator_email}...")
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [operator_email],
                    fail_silently=False,
                )

                sent_cache[reminder_key] = timezone.now().isoformat()
                _save_sent_cache(sent_cache)
                print(f"[DEBUG] Reminder sent for rental {rental.rental_id}")
