import pytest

from apps.attendance.models import AttendanceDay, AttendancePunchActionType, GeoFenceEnforcementMode, GeoFencePolicy
from apps.attendance.services import record_employee_punch
from apps.locations.models import OfficeLocation
from apps.timeoff.tests.test_services import _create_employee, _create_organisation


@pytest.mark.django_db
def test_record_employee_punch_blocks_outside_blocking_geo_fence():
    organisation = _create_organisation('Attendance Geo Fence Org')
    employee = _create_employee(organisation, email='geo-block@test.com')
    office_location = OfficeLocation.objects.create(organisation=organisation, name='HQ')
    employee.office_location = office_location
    employee.save(update_fields=['office_location', 'modified_at'])
    GeoFencePolicy.objects.create(
        organisation=organisation,
        location=office_location,
        name='HQ Block',
        latitude='12.971600',
        longitude='77.594600',
        radius_metres=100,
        enforcement_mode=GeoFenceEnforcementMode.BLOCK,
        is_active=True,
    )

    with pytest.raises(ValueError, match='geo-fence'):
        record_employee_punch(
            employee,
            action_type=AttendancePunchActionType.CHECK_IN,
            latitude='13.035000',
            longitude='77.597000',
        )


@pytest.mark.django_db
def test_record_employee_punch_marks_warning_for_warn_only_geo_fence():
    organisation = _create_organisation('Attendance Geo Fence Warn Org')
    employee = _create_employee(organisation, email='geo-warn@test.com')
    office_location = OfficeLocation.objects.create(organisation=organisation, name='Branch')
    employee.office_location = office_location
    employee.save(update_fields=['office_location', 'modified_at'])
    GeoFencePolicy.objects.create(
        organisation=organisation,
        location=office_location,
        name='Branch Warn',
        latitude='12.971600',
        longitude='77.594600',
        radius_metres=100,
        enforcement_mode=GeoFenceEnforcementMode.WARN,
        is_active=True,
    )

    punch, attendance_day = record_employee_punch(
        employee,
        action_type=AttendancePunchActionType.CHECK_IN,
        latitude='13.035000',
        longitude='77.597000',
    )

    punch.refresh_from_db()
    attendance_day.refresh_from_db()

    assert punch.metadata.get('geo_fence_warning') is True
    assert attendance_day.metadata.get('geo_fence_warning') is True
    assert AttendanceDay.objects.filter(employee=employee).count() == 1
