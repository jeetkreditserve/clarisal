from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.payroll.statutory_seed import seed_statutory_master_data


class Command(BaseCommand):
    help = 'Seed repeatable payroll statutory master data for Professional Tax and Labour Welfare Fund.'

    @transaction.atomic
    def handle(self, *args, **options):
        result = seed_statutory_master_data()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {result['income_tax_masters']} income tax masters, "
                f"{result['professional_tax_rules']} PT rules, and "
                f"{result['labour_welfare_fund_rules']} LWF rules."
            )
        )
