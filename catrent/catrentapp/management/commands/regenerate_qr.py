from django.core.management.base import BaseCommand
from catrentapp.models import Machine
from django.conf import settings

class Command(BaseCommand):
    help = 'Regenerates QR codes for all machines and uploads them to storage (Cloudinary if configured)'

    def handle(self, *args, **options):
        machines = Machine.objects.all()
        self.stdout.write(f"Found {machines.count()} machines. Starting regeneration...")
        self.stdout.write(f"Using SITE_URL: {settings.SITE_URL}")
        
        count = 0
        for machine in machines:
            try:
                self.stdout.write(f"Regenerating QR for {machine.equipment_id}...")
                machine.generate_qr_code(force=True)
                machine.save()
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Successfully regenerated QR for {machine.equipment_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to regenerate QR for {machine.equipment_id}: {str(e)}"))
            
        self.stdout.write(self.style.SUCCESS(f"Finished. {count} QR codes regenerated successfully."))
