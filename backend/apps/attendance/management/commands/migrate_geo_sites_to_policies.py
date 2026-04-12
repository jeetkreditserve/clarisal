from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.attendance.models import AttendancePolicy, GeoFenceEnforcementMode, GeoFencePolicy
from apps.locations.models import OfficeLocation


def _parse_decimal(raw_value, *, field_name: str) -> Decimal:
    try:
        return Decimal(str(raw_value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f'invalid {field_name}: {raw_value!r}') from exc


def _parse_radius(raw_site: dict) -> int:
    raw_radius = raw_site.get('radius_meters', raw_site.get('radius_metres', raw_site.get('radius', 200)))
    try:
        return max(1, int(raw_radius))
    except (TypeError, ValueError) as exc:
        raise ValueError(f'invalid radius: {raw_radius!r}') from exc


class Command(BaseCommand):
    help = (
        'Migrate deprecated AttendancePolicy.allowed_geo_sites JSON data into '
        'GeoFencePolicy records when the organisation has an unambiguous single office location.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0
        skipped = 0
        migrated = 0

        queryset = AttendancePolicy.objects.select_related('organisation').order_by('organisation_id', 'created_at')
        for policy in queryset.iterator():
            sites = policy.allowed_geo_sites or []
            if not sites:
                continue

            active_locations = list(
                OfficeLocation.objects.filter(organisation=policy.organisation, is_active=True).order_by('created_at', 'id')
            )
            if len(active_locations) != 1 or len(sites) != 1:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped policy {policy.id}: expected exactly one active office location and one geo site."
                    )
                )
                continue

            site = sites[0]
            latitude = _parse_decimal(site.get('latitude', site.get('lat')), field_name='latitude')
            longitude = _parse_decimal(site.get('longitude', site.get('lng')), field_name='longitude')
            radius_metres = _parse_radius(site)

            geo_policy, was_created = GeoFencePolicy.objects.update_or_create(
                organisation=policy.organisation,
                location=active_locations[0],
                defaults={
                    'name': f'{policy.name} migrated geo-fence',
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius_metres': radius_metres,
                    'enforcement_mode': GeoFenceEnforcementMode.BLOCK,
                    'is_active': True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

            policy.allowed_geo_sites = []
            policy.save(update_fields=['allowed_geo_sites', 'modified_at'])
            migrated += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrated policy {policy.id} to geo-fence {geo_policy.id} for location {active_locations[0].name}."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Geo-site migration completed: migrated={migrated}, created={created}, updated={updated}, skipped={skipped}.'
            )
        )
