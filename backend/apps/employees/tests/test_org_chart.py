import pytest
from datetime import date

from apps.accounts.models import User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.employees.services import (
    get_org_chart_tree,
    get_employee_direct_reports,
    validate_org_chart_cycles,
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
def organisation(db, org_admin):
    from apps.organisations.models import Organisation, OrganisationAccessState, OrganisationBillingStatus, OrganisationStatus
    return Organisation.objects.create(
        name='Test Org',
        created_by=org_admin,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def employee_hierarchy(db, organisation):
    ceo_user = User.objects.create_user(email='ceo@test.com', password='pass123!', role=UserRole.EMPLOYEE, first_name='CEO', last_name='User')
    mgr1_user = User.objects.create_user(email='mgr1@test.com', password='pass123!', role=UserRole.EMPLOYEE, first_name='Manager', last_name='One')
    mgr2_user = User.objects.create_user(email='mgr2@test.com', password='pass123!', role=UserRole.EMPLOYEE, first_name='Manager', last_name='Two')
    emp1_user = User.objects.create_user(email='emp1@test.com', password='pass123!', role=UserRole.EMPLOYEE, first_name='Employee', last_name='One')
    emp2_user = User.objects.create_user(email='emp2@test.com', password='pass123!', role=UserRole.EMPLOYEE, first_name='Employee', last_name='Two')
    
    ceo = Employee.objects.create(organisation=organisation, user=ceo_user, employee_code='CEO001', status=EmployeeStatus.ACTIVE)
    mgr1 = Employee.objects.create(organisation=organisation, user=mgr1_user, employee_code='MGR001', status=EmployeeStatus.ACTIVE, reporting_to=ceo)
    mgr2 = Employee.objects.create(organisation=organisation, user=mgr2_user, employee_code='MGR002', status=EmployeeStatus.ACTIVE, reporting_to=ceo)
    emp1 = Employee.objects.create(organisation=organisation, user=emp1_user, employee_code='EMP001', status=EmployeeStatus.ACTIVE, reporting_to=mgr1)
    emp2 = Employee.objects.create(organisation=organisation, user=emp2_user, employee_code='EMP002', status=EmployeeStatus.ACTIVE, reporting_to=mgr1)
    
    return {
        'ceo': ceo,
        'mgr1': mgr1,
        'mgr2': mgr2,
        'emp1': emp1,
        'emp2': emp2,
    }


class TestOrgChartTree:
    def test_build_tree(self, organisation, employee_hierarchy):
        tree = get_org_chart_tree(organisation)
        
        assert len(tree) == 1
        assert tree[0]['name'] == 'CEO User'
        assert len(tree[0]['direct_reports']) == 2

    def test_tree_excludes_inactive(self, organisation, employee_hierarchy):
        employee_hierarchy['mgr1'].status = EmployeeStatus.TERMINATED
        employee_hierarchy['mgr1'].save()
        
        tree = get_org_chart_tree(organisation, include_inactive=False)
        
        mgr1_in_tree = any(n['name'] == 'Manager One' for n in tree)
        mgr1_as_report = any(
            n['name'] == 'Manager One' 
            for root in tree 
            for n in root.get('direct_reports', [])
        )
        assert not mgr1_in_tree and not mgr1_as_report

    def test_tree_includes_inactive_when_requested(self, organisation, employee_hierarchy):
        employee_hierarchy['mgr1'].status = EmployeeStatus.TERMINATED
        employee_hierarchy['mgr1'].save()
        
        tree = get_org_chart_tree(organisation, include_inactive=True)
        
        mgr1_in_tree = any(n['name'] == 'Manager One' for n in tree[0]['direct_reports'])
        assert mgr1_in_tree

    def test_employees_without_manager_are_roots(self, organisation, org_admin):
        user1 = User.objects.create_user(email='orphan@test.com', password='pass123!', role=UserRole.EMPLOYEE, first_name='Orphan', last_name='Emp')
        orphan = Employee.objects.create(organisation=organisation, user=user1, employee_code='ORP001', status=EmployeeStatus.ACTIVE)
        
        tree = get_org_chart_tree(organisation)
        
        orphan_in_roots = any(n['name'] == 'Orphan Emp' for n in tree)
        assert orphan_in_roots


class TestDirectReports:
    def test_get_direct_reports(self, organisation, employee_hierarchy):
        reports = get_employee_direct_reports(employee_hierarchy['ceo'])
        
        assert len(reports) == 2
        report_names = {r.user.full_name for r in reports}
        assert 'Manager One' in report_names
        assert 'Manager Two' in report_names

    def test_get_direct_reports_excludes_inactive(self, organisation, employee_hierarchy):
        employee_hierarchy['emp1'].status = EmployeeStatus.TERMINATED
        employee_hierarchy['emp1'].save()
        
        reports = get_employee_direct_reports(employee_hierarchy['mgr1'])
        
        assert len(reports) == 1
        assert reports[0].user.full_name == 'Employee Two'


class TestOrgChartCycles:
    def test_no_cycles_in_valid_hierarchy(self, organisation, employee_hierarchy):
        cycles = validate_org_chart_cycles(organisation)
        
        assert len(cycles) == 0

    def test_detects_cycle(self, organisation, employee_hierarchy):
        employee_hierarchy['ceo'].reporting_to = employee_hierarchy['emp1']
        employee_hierarchy['ceo'].save()
        
        cycles = validate_org_chart_cycles(organisation)
        
        assert len(cycles) > 0
