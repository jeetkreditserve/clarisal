from io import StringIO

import pytest
from django.core.management import call_command

from apps.attendance.models import AttendancePolicy, GeoFenceEnforcementMode, GeoFencePolicy
from apps.locations.models import OfficeLocation
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)


@pytest.mark.django_db
def test_migrate_geo_sites_to_policies_moves_safe_single_location_data():
    organisation = Organisation.objects.create(
        name='Geo Migration Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    office_location = OfficeLocation.objects.create(organisation=organisation, name='HQ')
    policy = AttendancePolicy.objects.create(
        organisation=organisation,
        name='Default Policy',
        is_default=True,
        allowed_geo_sites=[
            {
                'latitude': '12.971600',
                'longitude': '77.594600',
                'radius_meters': 150,
            }
        ],
    )

    stdout = StringIO()
    call_command('migrate_geo_sites_to_policies', stdout=stdout)

    policy.refresh_from_db()
    geo_policy = GeoFencePolicy.objects.get(organisation=organisation, location=office_location)

    assert policy.allowed_geo_sites == []
    assert float(geo_policy.latitude) == pytest.approx(12.9716)
    assert float(geo_policy.longitude) == pytest.approx(77.5946)
    assert geo_policy.radius_metres == 150
    assert geo_policy.enforcement_mode == GeoFenceEnforcementMode.BLOCK
    assert 'migrated=1' in stdout.getvalue()


@pytest.mark.django_db
def test_migrate_geo_sites_to_policies_skips_ambiguous_location_mapping():
    organisation = Organisation.objects.create(
        name='Geo Migration Ambiguous Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    OfficeLocation.objects.create(organisation=organisation, name='HQ')
    OfficeLocation.objects.create(organisation=organisation, name='Branch')
    policy = AttendancePolicy.objects.create(
        organisation=organisation,
        name='Ambiguous Policy',
        is_default=True,
        allowed_geo_sites=[
            {
                'latitude': '12.971600',
                'longitude': '77.594600',
                'radius_meters': 150,
            }
        ],
    )

    stdout = StringIO()
    call_command('migrate_geo_sites_to_policies', stdout=stdout)

    policy.refresh_from_db()

    assert policy.allowed_geo_sites != []
    assert GeoFencePolicy.objects.filter(organisation=organisation).count() == 0
    assert 'skipped=1' in stdout.getvalue()
