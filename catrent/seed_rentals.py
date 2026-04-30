import os
from datetime import datetime

import django
from django.utils.timezone import make_aware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catrent.settings")
django.setup()

from catrentapp.models import Machine, Operator, Rental

MACHINE_IDS = [
    "EQX1001",
    "EQX1002",
    "CRN2001",
    "CRN2002",
    "BLD3001",
    "BLD3002",
    "LDR4001",
    "LDR4002",
]

ENTRIES = [
    ("EQX1001", 0, "SITE-N01", "North Mine", "2024-08-05T09:00", "2024-08-12T18:00"),
    ("EQX1002", 1, "SITE-N01", "North Mine", "2024-09-10T10:00", "2024-09-17T18:00"),
    ("CRN2001", 2, "SITE-S01", "South Port", "2024-11-02T08:30", "2024-11-10T17:30"),
    ("CRN2002", 3, "SITE-W01", "West Yard", "2025-01-08T09:00", "2025-01-15T18:00"),
    ("BLD3001", 0, "SITE-S01", "South Port", "2025-03-12T09:30", "2025-03-20T18:00"),
    ("BLD3002", 1, "SITE-W01", "West Yard", "2025-05-01T08:00", "2025-05-08T17:00"),
    ("LDR4001", 2, "SITE-N01", "North Mine", "2024-08-05T09:00", "2024-08-12T18:00"),
    ("LDR4002", 3, "SITE-S01", "South Port", "2024-09-10T10:00", "2024-09-17T18:00"),
    ("EQX1001", 1, "SITE-W01", "West Yard", "2024-11-02T08:30", "2024-11-10T17:30"),
    ("EQX1002", 2, "SITE-S01", "South Port", "2025-01-08T09:00", "2025-01-15T18:00"),
    ("CRN2001", 3, "SITE-N01", "North Mine", "2025-03-12T09:30", "2025-03-20T18:00"),
    ("CRN2002", 0, "SITE-W01", "West Yard", "2025-05-01T08:00", "2025-05-08T17:00"),
    ("BLD3001", 2, "SITE-N01", "North Mine", "2024-08-05T09:00", "2024-08-12T18:00"),
    ("BLD3002", 3, "SITE-S01", "South Port", "2024-09-10T10:00", "2024-09-17T18:00"),
    ("LDR4001", 0, "SITE-W01", "West Yard", "2024-11-02T08:30", "2024-11-10T17:30"),
    ("LDR4002", 1, "SITE-N01", "North Mine", "2025-01-08T09:00", "2025-01-15T18:00"),
]


def parse_dt(value: str):
    return make_aware(datetime.strptime(value, "%Y-%m-%dT%H:%M"))


def main():
    missing_machines = [
        machine_id
        for machine_id in MACHINE_IDS
        if not Machine.objects.filter(equipment_id=machine_id).exists()
    ]
    if missing_machines:
        raise SystemExit(f"Missing machines: {missing_machines}. Please add them first.")

    operators = list(Operator.objects.order_by("operator_id")[:4])
    if len(operators) < 4:
        raise SystemExit(f"Need at least 4 operators. Found {len(operators)}.")

    inserted = 0
    skipped = 0

    for machine_id, op_idx, site_id, site_name, start_s, end_s in ENTRIES:
        machine = Machine.objects.get(equipment_id=machine_id)
        operator = operators[op_idx]
        start_date = parse_dt(start_s)
        end_date = parse_dt(end_s)

        exists = Rental.objects.filter(
            machine=machine,
            operator_id=operator.operator_id,
            start_date=start_date,
            expected_end_date=end_date,
        ).exists()

        if exists:
            skipped += 1
            continue

        Rental.objects.create(
            machine=machine,
            operator_id=operator.operator_id,
            operator_name=operator.name,
            site_id=site_id,
            site_name=site_name,
            start_date=start_date,
            expected_end_date=end_date,
            actual_end_date=end_date,
            active=False,
            status="Completed",
            rate_per_day=machine.rate_per_day,
        )
        inserted += 1

    Machine.objects.filter(equipment_id__in=MACHINE_IDS).update(status="Available")

    print("OPERATORS_USED:", [operator.operator_id for operator in operators])
    print("INSERTED:", inserted)
    print("SKIPPED:", skipped)
    print("TOTAL_RENTALS_NOW:", Rental.objects.count())


if __name__ == "__main__":
    main()
