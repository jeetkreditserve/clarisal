import json

from .filings.payslip_pdf import download_payslip_pdf_response

from celery.result import AsyncResult
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (
    BelongsToActiveOrg,
    IsControlTowerUser,
    IsEmployee,
    IsOrgAdmin,
    OrgAdminMutationAllowed,
)
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.employees.models import Employee, EmployeeStatus

from .models import (
    Arrears,
    CostCentre,
    CompensationAssignment,
    CompensationTemplate,
    FullAndFinalSettlement,
    LabourWelfareFundRule,
    PayrollRun,
    PayrollRunItem,
    PayrollRunItemStatus,
    SurchargeRule,
    PayrollTaxSlabSet,
    PayrollTDSChallan,
    Payslip,
    ProfessionalTaxRule,
    StatutoryFilingBatch,
    StatutoryFilingStatus,
)
from .serializers import (
    ArrearsCreateSerializer,
    ArrearsSerializer,
    CompensationAssignmentSerializer,
    CompensationAssignmentWriteSerializer,
    CompensationTemplateSerializer,
    CompensationTemplateWriteSerializer,
    FullAndFinalSettlementSerializer,
    InvestmentDeclarationSerializer,
    InvestmentDeclarationWriteSerializer,
    LabourWelfareFundRuleSerializer,
    PayrollComponentSerializer,
    PayrollRunCalculationStatusSerializer,
    PayrollRunItemDetailSerializer,
    PayrollRunItemSerializer,
    PayrollRunSerializer,
    PayrollRunWriteSerializer,
    PayrollTaxSlabSetSerializer,
    PayrollTaxSlabSetWriteSerializer,
    PayrollTDSChallanSerializer,
    PayrollTDSChallanWriteSerializer,
    PayslipSerializer,
    ProfessionalTaxRuleSerializer,
    StatutoryFilingBatchSerializer,
    StatutoryFilingBatchWriteSerializer,
)
from .services import (
    assign_employee_compensation,
    cancel_statutory_filing_batch,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    delete_tax_slab_set,
    download_statutory_filing_batch,
    ensure_org_payroll_setup,
    finalize_pay_run,
    generate_form16_data,
    generate_statutory_filing_batch,
    list_statutory_filing_batches,
    regenerate_statutory_filing_batch,
    rerun_payroll_run,
    submit_compensation_assignment_for_approval,
    submit_compensation_template_for_approval,
    submit_pay_run_for_approval,
    update_compensation_template,
    update_tax_slab_set,
)


def _annotated_pay_run_qs(organisation=None):
    """Return a PayrollRun queryset with aggregated totals annotated."""
    qs = PayrollRun.objects
    if organisation is not None:
        qs = qs.filter(organisation=organisation)
    return qs.annotate(
        total_gross=Sum("items__gross_pay"),
        total_net=Sum("items__net_pay"),
        total_deductions=Sum("items__total_deductions"),
        employee_count=Count("items__employee", distinct=True),
        exception_count=Count(
            "items",
            filter=Q(items__status=PayrollRunItemStatus.EXCEPTION),
        ),
    )


def _serialize_pay_run(pay_run):
    """Re-fetch a single PayrollRun with annotations and serialize it."""
    annotated = _annotated_pay_run_qs().filter(id=pay_run.id).first() or pay_run
    return PayrollRunSerializer(annotated).data


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


def _get_employee(request):
    employee = get_active_employee(request, request.user)
    if employee is None:
        raise ValueError('Select an employee workspace to continue.')
    return employee


def _parse_query_bool(value):
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise ValueError('Boolean query parameter must be one of true/false, 1/0, yes/no, or on/off.')


def _statutory_master_payload(*, state_code=None):
    professional_tax_rules = ProfessionalTaxRule.objects.filter(is_active=True)
    labour_welfare_fund_rules = LabourWelfareFundRule.objects.filter(is_active=True)
    if state_code:
        professional_tax_rules = professional_tax_rules.filter(state_code=state_code)
        labour_welfare_fund_rules = labour_welfare_fund_rules.filter(state_code=state_code)
    return {
        'professional_tax_rules': ProfessionalTaxRuleSerializer(professional_tax_rules.prefetch_related('slabs'), many=True).data,
        'labour_welfare_fund_rules': LabourWelfareFundRuleSerializer(
            labour_welfare_fund_rules.prefetch_related('contributions'),
            many=True,
        ).data,
    }




class SurchargeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurchargeRule
        fields = ['id', 'fiscal_year', 'tax_regime', 'income_threshold', 'surcharge_rate_percent', 'effective_from']






class CostCentreSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, allow_null=True)
    children_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CostCentre
        fields = [
            'id', 'code', 'name', 'gl_code', 'parent', 'parent_name',
            'is_active', 'created_at', 'children_count'
        ]
    
    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()


class CostCentreWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=200)
    gl_code = serializers.CharField(max_length=50, required=False, default='', allow_blank=True)
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)




class OrgCostCentreListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
        
        queryset = CostCentre.objects.filter(organisation=organisation)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        queryset = queryset.select_related('parent').order_by('code')
        serializer = CostCentreSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = CostCentreWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        parent = None
        if serializer.validated_data.get('parent_id'):
            parent = CostCentre.objects.filter(
                organisation=organisation,
                id=serializer.validated_data['parent_id']
            ).first()
        
        cost_centre = CostCentre.objects.create(
            organisation=organisation,
            code=serializer.validated_data['code'],
            name=serializer.validated_data['name'],
            gl_code=serializer.validated_data.get('gl_code', ''),
            parent=parent,
            is_active=serializer.validated_data.get('is_active', True),
        )
        
        return Response(
            CostCentreSerializer(cost_centre).data,
            status=status.HTTP_201_CREATED
        )


class OrgCostCentreDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, cost_centre_id):
        organisation = get_active_admin_organisation(request, request.user)
        cost_centre = get_object_or_404(
            CostCentre.objects.filter(organisation=organisation),
            id=cost_centre_id
        )
        serializer = CostCentreSerializer(cost_centre)
        return Response(serializer.data)

    def patch(self, request, cost_centre_id):
        organisation = get_active_admin_organisation(request, request.user)
        cost_centre = get_object_or_404(
            CostCentre.objects.filter(organisation=organisation),
            id=cost_centre_id
        )
        
        serializer = CostCentreWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        if 'code' in serializer.validated_data:
            cost_centre.code = serializer.validated_data['code']
        if 'name' in serializer.validated_data:
            cost_centre.name = serializer.validated_data['name']
        if 'gl_code' in serializer.validated_data:
            cost_centre.gl_code = serializer.validated_data['gl_code']
        if 'is_active' in serializer.validated_data:
            cost_centre.is_active = serializer.validated_data['is_active']
        if 'parent_id' in serializer.validated_data:
            if serializer.validated_data['parent_id']:
                cost_centre.parent = CostCentre.objects.filter(
                    organisation=organisation,
                    id=serializer.validated_data['parent_id']
                ).first()
            else:
                cost_centre.parent = None
        
        cost_centre.save()
        
        return Response(CostCentreSerializer(cost_centre).data)

    def delete(self, request, cost_centre_id):
        organisation = get_active_admin_organisation(request, request.user)
        cost_centre = get_object_or_404(
            CostCentre.objects.filter(organisation=organisation),
            id=cost_centre_id
        )
        
        cost_centre.is_active = False
        cost_centre.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class CtSurchargeRuleListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        fiscal_year = request.query_params.get('fiscal_year')
        tax_regime = request.query_params.get('tax_regime')
        
        queryset = SurchargeRule.objects.all()
        if fiscal_year:
            queryset = queryset.filter(fiscal_year=fiscal_year)
        if tax_regime:
            queryset = queryset.filter(tax_regime=tax_regime.upper())
        
        queryset = queryset.order_by('fiscal_year', 'tax_regime', 'income_threshold')
        serializer = SurchargeRuleSerializer(queryset, many=True)
        return Response(serializer.data)


class CtPayrollTaxSlabSetListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request):
        queryset = PayrollTaxSlabSet.objects.filter(organisation__isnull=True).prefetch_related('slabs')
        return Response(PayrollTaxSlabSetSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = PayrollTaxSlabSetWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tax_slab_set = create_tax_slab_set(actor=request.user, organisation=None, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PayrollTaxSlabSetSerializer(tax_slab_set).data, status=status.HTTP_201_CREATED)


class CtPayrollTaxSlabSetDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk):
        tax_slab_set = get_object_or_404(PayrollTaxSlabSet, organisation__isnull=True, id=pk)
        serializer = PayrollTaxSlabSetWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            tax_slab_set = update_tax_slab_set(tax_slab_set, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        tax_slab_set.refresh_from_db()
        return Response(PayrollTaxSlabSetSerializer(tax_slab_set).data)

    def delete(self, request, pk):
        tax_slab_set = get_object_or_404(PayrollTaxSlabSet, organisation__isnull=True, id=pk)
        delete_tax_slab_set(tax_slab_set, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CtPayrollStatutoryMasterListView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request):
        state_code = (request.query_params.get('state_code') or '').strip().upper() or None
        return Response(_statutory_master_payload(state_code=state_code))


class OrgPayrollSummaryView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        setup = ensure_org_payroll_setup(organisation, actor=request.user)
        tax_slab_sets = PayrollTaxSlabSet.objects.filter(
            organisation__isnull=True, is_system_master=True, country_code='IN', is_active=True,
        ).prefetch_related('slabs').order_by('fiscal_year', 'is_old_regime', 'tax_category')
        templates = CompensationTemplate.objects.filter(organisation=organisation).prefetch_related('lines__component')
        assignments = CompensationAssignment.objects.filter(employee__organisation=organisation).select_related('employee__user', 'template')
        pay_runs = _annotated_pay_run_qs(organisation=organisation)
        return Response(
            {
                'tax_slab_sets': PayrollTaxSlabSetSerializer(tax_slab_sets, many=True).data,
                'components': PayrollComponentSerializer(setup['components'], many=True).data,
                'compensation_templates': CompensationTemplateSerializer(templates, many=True).data,
                'compensation_assignments': CompensationAssignmentSerializer(assignments, many=True).data,
                'pay_runs': PayrollRunSerializer(pay_runs, many=True).data,
                'statutory_filing_batches': StatutoryFilingBatchSerializer(
                    StatutoryFilingBatch.objects.filter(organisation=organisation).prefetch_related('source_pay_runs'),
                    many=True,
                ).data,
                'tds_challans': PayrollTDSChallanSerializer(
                    PayrollTDSChallan.objects.filter(organisation=organisation),
                    many=True,
                ).data,
                'payslip_count': Payslip.objects.filter(organisation=organisation).count(),
                **_statutory_master_payload(),
            }
        )


class OrgPayrollStatutoryMasterListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        _get_admin_organisation(request)
        state_code = (request.query_params.get('state_code') or '').strip().upper() or None
        return Response(_statutory_master_payload(state_code=state_code))


class OrgPayrollTaxSlabSetListCreateView(APIView):
    """Read-only view of CT-level statutory tax slab masters for org admins."""

    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        _get_admin_organisation(request)
        queryset = PayrollTaxSlabSet.objects.filter(
            organisation__isnull=True,
            is_system_master=True,
            country_code='IN',
            is_active=True,
        ).prefetch_related('slabs').order_by('fiscal_year', 'is_old_regime', 'tax_category')
        return Response(PayrollTaxSlabSetSerializer(queryset, many=True).data)


class OrgPayrollTDSChallanListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = PayrollTDSChallan.objects.filter(organisation=organisation)
        fiscal_year = (request.query_params.get('fiscal_year') or '').strip()
        if fiscal_year:
            queryset = queryset.filter(fiscal_year=fiscal_year)
        return Response(PayrollTDSChallanSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = PayrollTDSChallanWriteSerializer(data=request.data, context={'organisation': organisation})
        serializer.is_valid(raise_exception=True)
        challan = PayrollTDSChallan.objects.create(organisation=organisation, **serializer.validated_data)
        return Response(PayrollTDSChallanSerializer(challan).data, status=status.HTTP_201_CREATED)


class OrgPayrollTDSChallanDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        challan = get_object_or_404(PayrollTDSChallan, organisation=organisation, id=pk)
        serializer = PayrollTDSChallanWriteSerializer(
            challan,
            data=request.data,
            partial=True,
            context={'organisation': organisation},
        )
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(challan, field, value)
        challan.save()
        return Response(PayrollTDSChallanSerializer(challan).data)


class OrgCompensationTemplateListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = CompensationTemplate.objects.filter(organisation=organisation).prefetch_related('lines__component')
        return Response(CompensationTemplateSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = CompensationTemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = create_compensation_template(organisation, actor=request.user, **serializer.validated_data)
        return Response(CompensationTemplateSerializer(template).data, status=status.HTTP_201_CREATED)


class OrgCompensationTemplateDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        template = get_object_or_404(CompensationTemplate, organisation=organisation, id=pk)
        serializer = CompensationTemplateWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        template = update_compensation_template(template, actor=request.user, **serializer.validated_data)
        return Response(CompensationTemplateSerializer(template).data)


class OrgCompensationTemplateSubmitView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        template = get_object_or_404(CompensationTemplate, organisation=organisation, id=pk)
        requester_employee = Employee.objects.filter(organisation=organisation, user=request.user, status=EmployeeStatus.ACTIVE).first()
        try:
            template = submit_compensation_template_for_approval(
                template,
                requester_user=request.user,
                requester_employee=requester_employee,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CompensationTemplateSerializer(template).data)


class OrgCompensationAssignmentListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = CompensationAssignment.objects.filter(employee__organisation=organisation).select_related('employee__user', 'template').prefetch_related('lines')
        return Response(CompensationAssignmentSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = CompensationAssignmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = get_object_or_404(Employee, organisation=organisation, id=serializer.validated_data['employee_id'])
        template = get_object_or_404(CompensationTemplate, organisation=organisation, id=serializer.validated_data['template_id'])
        assignment = assign_employee_compensation(
            employee,
            template,
            effective_from=serializer.validated_data['effective_from'],
            actor=request.user,
            auto_approve=serializer.validated_data.get('auto_approve', False),
            tax_regime=serializer.validated_data.get('tax_regime'),
            is_pf_opted_out=serializer.validated_data.get('is_pf_opted_out', False),
            is_epf_exempt=serializer.validated_data.get('is_epf_exempt', False),
            vpf_rate_percent=serializer.validated_data.get('vpf_rate_percent'),
        )
        return Response(CompensationAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class OrgCompensationAssignmentSubmitView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        assignment = get_object_or_404(CompensationAssignment, employee__organisation=organisation, id=pk)
        requester_employee = Employee.objects.filter(organisation=organisation, user=request.user, status=EmployeeStatus.ACTIVE).first()
        try:
            assignment = submit_compensation_assignment_for_approval(
                assignment,
                requester_user=request.user,
                requester_employee=requester_employee,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CompensationAssignmentSerializer(assignment).data)


class OrgPayrollRunListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = _annotated_pay_run_qs(organisation=organisation)
        return Response(PayrollRunSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = PayrollRunWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pay_run = create_payroll_run(
            organisation,
            actor=request.user,
            requester_user=request.user,
            **serializer.validated_data,
        )
        return Response(_serialize_pay_run(pay_run), status=status.HTTP_201_CREATED)


class OrgPayrollRunDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(_annotated_pay_run_qs(organisation=organisation), id=pk)
        return Response(PayrollRunSerializer(pay_run).data)



def _serialize_run_item(item):
    """Build a PayrollRunItemDetailSerializer-compatible dict from a PayrollRunItem."""
    snap = item.snapshot or {}
    return {
        'id': str(item.id),
        'employee_id': str(item.employee_id),
        'employee_name': item.employee.user.full_name,
        'employee_code': item.employee.employee_code,
        'department': item.employee.department.name if item.employee.department_id else None,
        'status': item.status,
        'has_exception': item.status == 'EXCEPTION',
        'gross_pay': str(item.gross_pay),
        'employee_deductions': str(item.employee_deductions),
        'employer_contributions': str(item.employer_contributions),
        'income_tax': str(item.income_tax),
        'total_deductions': str(item.total_deductions),
        'net_pay': str(item.net_pay),
        'snapshot': snap,
        'message': item.message or '',
        'arrears': snap.get('arrears', '0'),
        'lop_days': snap.get('lop_days', '0'),
        'esi_employee': snap.get('esi_employee', '0'),
        'esi_employer': snap.get('esi_employer', '0'),
        'pf_employer': snap.get('pf_employer', '0'),
        'lwf_employee': snap.get('lwf_employee', '0'),
        'lwf_employer': snap.get('lwf_employer', '0'),
        'pt_monthly': snap.get('pt_monthly', '0'),
        'tax_regime': snap.get('tax_regime'),
    }


class OrgPayrollRunItemListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        queryset = PayrollRunItem.objects.filter(pay_run=pay_run).select_related('employee__user', 'employee__department').order_by(
            'employee__employee_code',
            'employee__user__last_name',
            'created_at',
        )

        employee_id = (request.query_params.get('employee') or '').strip()
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)

        has_exception = request.query_params.get('has_exception')
        if has_exception is not None:
            try:
                has_exception = _parse_query_bool(has_exception)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(
                status=PayrollRunItemStatus.EXCEPTION if has_exception else PayrollRunItemStatus.READY,
            )

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        items_data = [_serialize_run_item(i) for i in page]
        serializer = PayrollRunItemDetailSerializer(items_data, many=True)
        return paginator.get_paginated_response(serializer.data)


class OrgPayrollRunForm16View(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun.objects.prefetch_related('payslips__employee__user'), organisation=organisation, id=pk)
        if pay_run.status != 'FINALIZED':
            return Response(
                {'error': 'Form 16 is only available for finalized payroll runs.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(generate_form16_data(pay_run))


class OrgPayrollRunCalculateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        from .tasks import calculate_pay_run_task

        result = calculate_pay_run_task.delay(str(pay_run.id), str(request.user.id))
        return Response(
            {'task_id': result.id, 'pay_run_id': str(pay_run.id)},
            status=status.HTTP_202_ACCEPTED,
        )


class OrgPayrollRunCalculationStatusView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id query param required'}, status=status.HTTP_400_BAD_REQUEST)
        result = AsyncResult(task_id)
        payload = {
            'task_id': task_id,
            'state': result.state,
            'result': result.result if result.successful() else None,
            'error': str(result.result) if result.failed() else None,
        }
        serializer = PayrollRunCalculationStatusSerializer(payload)
        return Response(serializer.data)


class OrgPayrollRunSubmitView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        requester_employee = Employee.objects.filter(organisation=organisation, user=request.user, status=EmployeeStatus.ACTIVE).first()
        try:
            pay_run = submit_pay_run_for_approval(
                pay_run,
                requester_user=request.user,
                requester_employee=requester_employee,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_pay_run(pay_run))


class OrgPayrollRunFinalizeView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        try:
            pay_run = finalize_pay_run(pay_run, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_pay_run(pay_run))


class OrgPayrollRunRerunView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        try:
            rerun = rerun_payroll_run(pay_run, actor=request.user, requester_user=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_pay_run(rerun), status=status.HTTP_201_CREATED)


class OrgStatutoryFilingBatchListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = list_statutory_filing_batches(organisation)
        return Response(StatutoryFilingBatchSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = StatutoryFilingBatchWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            batch = generate_statutory_filing_batch(organisation, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        status_code = status.HTTP_201_CREATED if batch.status != StatutoryFilingStatus.BLOCKED else status.HTTP_200_OK
        return Response(StatutoryFilingBatchSerializer(batch).data, status=status_code)


class OrgStatutoryFilingBatchDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        batch = get_object_or_404(StatutoryFilingBatch.objects.prefetch_related('source_pay_runs'), organisation=organisation, id=pk)
        return Response(StatutoryFilingBatchSerializer(batch).data)


class OrgStatutoryFilingBatchRegenerateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        batch = get_object_or_404(StatutoryFilingBatch, organisation=organisation, id=pk)
        try:
            regenerated = regenerate_statutory_filing_batch(batch, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StatutoryFilingBatchSerializer(regenerated).data, status=status.HTTP_201_CREATED)


class OrgStatutoryFilingBatchCancelView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        batch = get_object_or_404(StatutoryFilingBatch, organisation=organisation, id=pk)
        batch = cancel_statutory_filing_batch(batch, actor=request.user)
        return Response(StatutoryFilingBatchSerializer(batch).data)


class OrgStatutoryFilingBatchDownloadView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        batch = get_object_or_404(StatutoryFilingBatch, organisation=organisation, id=pk)
        try:
            payload, content_type, file_name = download_statutory_filing_batch(batch, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(payload, content_type=content_type or 'application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{file_name or "statutory-filing"}"'
        return response


class OrgFullAndFinalSettlementListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = FullAndFinalSettlement.objects.filter(employee__organisation=organisation).select_related('employee__user', 'offboarding_process')
        return Response(FullAndFinalSettlementSerializer(queryset, many=True).data)


class OrgFullAndFinalSettlementDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        settlement = get_object_or_404(
            FullAndFinalSettlement.objects.select_related('employee__user', 'offboarding_process'),
            employee__organisation=organisation,
            id=pk,
        )
        return Response(FullAndFinalSettlementSerializer(settlement).data)


class OrgArrearsListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = Arrears.objects.filter(employee__organisation=organisation).select_related('employee__user', 'pay_run')
        return Response(ArrearsSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = ArrearsCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = get_object_or_404(Employee, organisation=organisation, id=serializer.validated_data['employee_id'])
        arrear = Arrears.objects.create(
            employee=employee,
            for_period_year=serializer.validated_data['for_period_year'],
            for_period_month=serializer.validated_data['for_period_month'],
            reason=serializer.validated_data['reason'],
            amount=serializer.validated_data['amount'],
        )
        return Response(ArrearsSerializer(arrear).data, status=status.HTTP_201_CREATED)


class OrgArrearsDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        arrear = get_object_or_404(
            Arrears.objects.select_related('employee__user', 'pay_run'),
            employee__organisation=organisation,
            id=pk,
        )
        return Response(ArrearsSerializer(arrear).data)


class MyPayslipListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        queryset = Payslip.objects.filter(employee=employee)
        return Response(PayslipSerializer(queryset, many=True).data)


class MyPayslipDetailView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, pk):
        employee = _get_employee(request)
        payslip = get_object_or_404(Payslip, employee=employee, id=pk)
        return Response(PayslipSerializer(payslip).data)


class OrgPayslipDownloadView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        payslip = get_object_or_404(Payslip, organisation=organisation, id=pk)
        return download_payslip_pdf_response(payslip)


class MyPayslipDownloadView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, pk):
        employee = _get_employee(request)
        payslip = get_object_or_404(Payslip, employee=employee, id=pk)
        return download_payslip_pdf_response(payslip)


class MyInvestmentDeclarationListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        queryset = employee.investment_declarations.all()
        return Response(InvestmentDeclarationSerializer(queryset, many=True).data)

    def post(self, request):
        employee = _get_employee(request)
        serializer = InvestmentDeclarationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        declaration = employee.investment_declarations.create(**serializer.validated_data)
        return Response(InvestmentDeclarationSerializer(declaration).data, status=status.HTTP_201_CREATED)
