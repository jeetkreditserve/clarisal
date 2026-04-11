from datetime import date

import pytest

from apps.accounts.models import User, UserRole
from apps.assets.models import AssetAssignmentStatus, AssetCondition, AssetLifecycleStatus
from apps.assets.services import (
    acknowledge_asset_assignment,
    assign_asset_to_employee,
    complete_asset_maintenance,
    create_asset_category,
    create_asset_incident,
    create_asset_item,
    create_asset_maintenance,
    mark_asset_as_lost,
    return_asset,
)
from apps.employees.models import Employee
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)


@pytest.fixture
def org_admin(db):
    return User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )


@pytest.fixture
def employee_user(db):
    return User.objects.create_user(
        email='john@org.com',
        password='pass123!',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )


@pytest.fixture
def organisation(db, org_admin):
    return Organisation.objects.create(
        name='Test Org',
        created_by=org_admin,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def employee(db, organisation, employee_user):
    return Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP001',
    )


class TestAssetCategoryService:
    def test_create_category(self, organisation, org_admin):
        category = create_asset_category(
            organisation=organisation,
            name="Laptops",
            description="Portable computers",
            actor=org_admin,
        )
        assert category.name == "Laptops"
        assert category.organisation == organisation


class TestAssetItemService:
    def test_create_asset_item(self, organisation, org_admin):
        category = create_asset_category(
            organisation=organisation,
            name="Laptops",
            actor=org_admin,
        )
        item = create_asset_item(
            organisation=organisation,
            name="MacBook Pro 14",
            category=category,
            asset_tag="LAP-001",
            serial_number="SN12345",
            purchase_cost=2499.99,
            actor=org_admin,
        )
        assert item.name == "MacBook Pro 14"
        assert item.asset_tag == "LAP-001"
        assert item.lifecycle_status == AssetLifecycleStatus.AVAILABLE


class TestAssetAssignmentService:
    def test_assign_asset_to_employee(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Phones")
        asset = create_asset_item(organisation=organisation, name="iPhone 15", category=category)
        
        assignment = assign_asset_to_employee(
            asset=asset,
            employee=employee,
            expected_return_date='2026-06-01',
            actor=org_admin,
        )
        asset.refresh_from_db()
        
        assert assignment.employee == employee
        assert assignment.status == AssetAssignmentStatus.ACTIVE
        assert asset.lifecycle_status == AssetLifecycleStatus.ASSIGNED

    def test_cannot_assign_already_assigned_asset(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Phones")
        asset = create_asset_item(organisation=organisation, name="iPhone 15", category=category)
        
        assign_asset_to_employee(asset=asset, employee=employee)
        
        emp2_user = User.objects.create_user(
            email='jane@org.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        emp2 = Employee.objects.create(
            organisation=organisation,
            user=emp2_user,
            employee_code='EMP002',
        )
        
        with pytest.raises(ValueError, match="not available"):
            assign_asset_to_employee(asset=asset, employee=emp2)

    def test_acknowledge_assignment(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Phones")
        asset = create_asset_item(organisation=organisation, name="iPhone 15", category=category)
        
        assignment = assign_asset_to_employee(asset=asset, employee=employee)
        ack_assignment = acknowledge_asset_assignment(assignment, actor=org_admin)
        
        assert ack_assignment.acknowledged_at is not None

    def test_return_asset(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Phones")
        asset = create_asset_item(organisation=organisation, name="iPhone 15", category=category)
        
        assignment = assign_asset_to_employee(asset=asset, employee=employee)
        returned = return_asset(assignment=assignment, condition_on_return=AssetCondition.GOOD, actor=org_admin)
        asset.refresh_from_db()
        
        assert returned.status == AssetAssignmentStatus.RETURNED
        assert asset.lifecycle_status == AssetLifecycleStatus.AVAILABLE

    def test_return_asset_damaged(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Phones")
        asset = create_asset_item(organisation=organisation, name="iPhone 15", category=category)
        
        assignment = assign_asset_to_employee(asset=asset, employee=employee)
        return_asset(assignment=assignment, condition_on_return=AssetCondition.DAMAGED, actor=org_admin)
        asset.refresh_from_db()
        
        assert asset.lifecycle_status == AssetLifecycleStatus.IN_MAINTENANCE

    def test_mark_asset_as_lost(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Phones")
        asset = create_asset_item(organisation=organisation, name="iPhone 15", category=category)
        
        assignment = assign_asset_to_employee(asset=asset, employee=employee)
        lost = mark_asset_as_lost(assignment, notes="Lost in transit", actor=org_admin)
        asset.refresh_from_db()
        
        assert lost.status == AssetAssignmentStatus.LOST
        assert asset.lifecycle_status == AssetLifecycleStatus.LOST


class TestAssetIncidentService:
    def test_create_incident(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Tablets")
        asset = create_asset_item(organisation=organisation, name="iPad Pro", category=category)
        
        incident = create_asset_incident(
            asset=asset,
            incident_type='DAMAGE',
            description="Screen cracked",
            employee=employee,
            actor=org_admin,
        )
        
        assert incident.incident_type == 'DAMAGE'
        assert incident.description == "Screen cracked"

    def test_loss_incident_updates_status(self, organisation, org_admin):
        category = create_asset_category(organisation=organisation, name="Tablets")
        asset = create_asset_item(organisation=organisation, name="iPad Pro", category=category)
        
        create_asset_incident(
            asset=asset,
            incident_type='LOSS',
            description="Device lost",
            actor=org_admin,
        )
        asset.refresh_from_db()
        
        assert asset.lifecycle_status == AssetLifecycleStatus.LOST


class TestAssetMaintenanceService:
    def test_create_maintenance(self, organisation, org_admin):
        category = create_asset_category(organisation=organisation, name="Monitors")
        asset = create_asset_item(organisation=organisation, name="Dell 27 inch", category=category)
        
        maintenance = create_asset_maintenance(
            asset=asset,
            maintenance_type='REPAIR',
            description="Screen repair",
            scheduled_date='2026-05-01',
            cost=150.00,
            vendor="Dell Service",
            actor=org_admin,
        )
        
        assert maintenance.maintenance_type == 'REPAIR'
        asset.refresh_from_db()
        assert asset.lifecycle_status == AssetLifecycleStatus.IN_MAINTENANCE

    def test_complete_maintenance(self, organisation, org_admin):
        category = create_asset_category(organisation=organisation, name="Monitors")
        asset = create_asset_item(organisation=organisation, name="Dell 27 inch", category=category)
        
        maintenance = create_asset_maintenance(
            asset=asset,
            maintenance_type='SERVICE',
            description="Regular service",
            actor=org_admin,
        )
        
        completed = complete_asset_maintenance(
            maintenance=maintenance,
            completed_date='2026-05-15',
            notes="All good",
            actor=org_admin,
        )
        asset.refresh_from_db()
        
        assert completed.completed_date is not None
        assert asset.lifecycle_status == AssetLifecycleStatus.AVAILABLE


class TestAssetOffboardingIntegration:
    def test_get_unresolved_asset_assignments(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Laptops")
        asset = create_asset_item(organisation=organisation, name="MacBook", category=category)

        assign_asset_to_employee(asset=asset, employee=employee, actor=org_admin)

        from apps.assets.services import get_unresolved_asset_assignments
        unresolved = list(get_unresolved_asset_assignments(employee))
        
        assert len(unresolved) == 1
        assert unresolved[0].asset == asset

    def test_get_employee_asset_summary(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Laptops")
        asset = create_asset_item(organisation=organisation, name="MacBook", category=category)

        assign_asset_to_employee(asset=asset, employee=employee, actor=org_admin)

        from apps.assets.services import get_employee_asset_summary
        summary = get_employee_asset_summary(employee)
        
        assert summary['active_assignments'] == 1
        assert summary['has_unresolved'] is True
        assert len(summary['unresolved_assets']) == 1
        assert summary['unresolved_assets'][0]['asset_name'] == 'MacBook'

    def test_return_clears_unresolved(self, organisation, employee, org_admin):
        category = create_asset_category(organisation=organisation, name="Laptops")
        asset = create_asset_item(organisation=organisation, name="MacBook", category=category)
        
        assignment = assign_asset_to_employee(asset=asset, employee=employee, actor=org_admin)
        return_asset(assignment=assignment, actor=org_admin)
        
        from apps.assets.services import get_employee_asset_summary
        summary = get_employee_asset_summary(employee)
        
        assert summary['active_assignments'] == 0
        assert summary['has_unresolved'] is False
        assert summary['returned_assignments'] == 1


class TestAssetOffboardingServiceIntegration:
    def test_offboarding_summary_includes_asset_info(self, organisation, org_admin):
        user = User.objects.create_user(email='emp2@test.com', password='pass123!', role=UserRole.EMPLOYEE, is_active=True)
        employee2 = Employee.objects.create(organisation=organisation, user=user, employee_code='EMP002')

        category = create_asset_category(organisation=organisation, name="Phones")
        asset = create_asset_item(organisation=organisation, name="iPhone", category=category)
        assign_asset_to_employee(asset=asset, employee=employee2, actor=org_admin)

        from apps.employees.services import create_or_update_offboarding_process, get_employee_offboarding_summary

        create_or_update_offboarding_process(
            employee=employee2,
            exit_status='NOTICE_PERIOD',
            date_of_exit=date(2026, 4, 30),
            actor=org_admin,
        )
        
        summary = get_employee_offboarding_summary(employee2)
        assert 'asset_summary' in summary
        assert summary['asset_summary']['active_assignments'] == 1
        assert summary['asset_summary']['has_unresolved'] is True
