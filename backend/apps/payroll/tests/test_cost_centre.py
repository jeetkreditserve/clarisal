import pytest
from django.db import IntegrityError

from apps.accounts.models import User, UserRole
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.payroll.models import (
    CompensationTemplateLine,
    CostCentre,
    PayrollComponent,
    PayrollComponentType,
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
    return Organisation.objects.create(
        name='Test Org',
        created_by=org_admin,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def component(db, organisation):
    return PayrollComponent.objects.create(
        organisation=organisation,
        code='BASIC',
        name='Basic Salary',
        component_type=PayrollComponentType.EARNING,
    )


class TestCostCentreModel:
    def test_create_cost_centre(self, organisation):
        cc = CostCentre.objects.create(
            organisation=organisation,
            code='CC001',
            name='Engineering',
            gl_code='ENG-001',
        )
        assert cc.code == 'CC001'
        assert cc.name == 'Engineering'
        assert cc.is_active is True

    def test_cost_centre_with_parent(self, organisation):
        parent = CostCentre.objects.create(
            organisation=organisation,
            code='CC001',
            name='Engineering',
        )
        child = CostCentre.objects.create(
            organisation=organisation,
            code='CC002',
            name='Backend',
            parent=parent,
        )
        assert child.parent == parent
        assert parent.children.filter(is_active=True).count() == 1

    def test_cost_centre_unique_code_per_org(self, organisation):
        CostCentre.objects.create(
            organisation=organisation,
            code='CC001',
            name='Engineering',
        )
        with pytest.raises(IntegrityError):
            CostCentre.objects.create(
                organisation=organisation,
                code='CC001',
                name='Another',
            )

    def test_deactivate_cost_centre(self, organisation):
        cc = CostCentre.objects.create(
            organisation=organisation,
            code='CC001',
            name='Engineering',
        )
        cc.is_active = False
        cc.save()
        
        assert CostCentre.objects.filter(organisation=organisation, is_active=True).count() == 0
        assert CostCentre.objects.filter(organisation=organisation, is_active=False).count() == 1


class TestCostCentreInCompensationTemplateLine:
    def test_template_line_without_cost_centre(self, organisation, component):
        cc = CostCentre.objects.create(
            organisation=organisation,
            code='CC001',
            name='Engineering',
        )

        line = CompensationTemplateLine(
            template_id='test-id',
            component=component,
            monthly_amount=50000,
        )
        line.cost_centre = cc
        line.save = lambda: None
        
        assert line.cost_centre == cc
        assert line.cost_centre.name == 'Engineering'

    def test_template_line_with_cost_centre_null(self, organisation, component):
        line = CompensationTemplateLine(
            template_id='test-id',
            component=component,
            monthly_amount=50000,
        )
        assert line.cost_centre is None
