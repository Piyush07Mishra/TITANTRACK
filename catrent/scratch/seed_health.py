import os
import random
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catrent.settings")
django.setup()

from catrentapp.models import Machine, EquipmentHealth

STATUS_CHOICES = ['Good', 'Warning', 'Critical', 'Maintenance Required']
COMPONENT_CHOICES = ['Engine', 'Hydraulics', 'Transmission', 'Fuel System', 'Cooling System', 'Electrical', 'Brakes', 'MISC']

def seed_health():
    machines = Machine.objects.all()
    count = 0
    for machine in machines:
        # Create 1-3 health records for each machine
        for _ in range(random.randint(1, 3)):
            EquipmentHealth.objects.create(
                machine=machine,
                status=random.choice(STATUS_CHOICES),
                component=random.choice(COMPONENT_CHOICES),
                timestamp=timezone.now() - timezone.timedelta(hours=random.randint(0, 48))
            )
            count += 1
    print(f"Successfully seeded {count} health records for {machines.count()} machines.")

if __name__ == "__main__":
    seed_health()
