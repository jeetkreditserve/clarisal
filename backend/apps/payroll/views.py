import json

from celery.result import AsyncResult
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
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
    CompensationAssignment,
    CompensationTemplate,
    FullAndFinalSettlement,
    LabourWelfareFundRule,
    PayrollRun,
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
        tax_slab_sets = PayrollTaxSlabSet.objects.filter(organisation=organisation).prefetch_related('slabs')
        templates = CompensationTemplate.objects.filter(organisation=organisation).prefetch_related('lines__component')
        assignments = CompensationAssignment.objects.filter(employee__organisation=organisation).select_related('employee__user', 'template')
        pay_runs = PayrollRun.objects.filter(organisation=organisation).prefetch_related('items__employee__user')
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
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        ensure_org_payroll_setup(organisation, actor=request.user)
        queryset = PayrollTaxSlabSet.objects.filter(organisation=organisation).prefetch_related('slabs')
        return Response(PayrollTaxSlabSetSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = PayrollTaxSlabSetWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tax_slab_set = create_tax_slab_set(actor=request.user, organisation=organisation, **serializer.validated_data)
        return Response(PayrollTaxSlabSetSerializer(tax_slab_set).data, status=status.HTTP_201_CREATED)


class OrgPayrollTaxSlabSetDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        tax_slab_set = get_object_or_404(PayrollTaxSlabSet, organisation=organisation, id=pk)
        serializer = PayrollTaxSlabSetWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        tax_slab_set = update_tax_slab_set(tax_slab_set, actor=request.user, **serializer.validated_data)
        return Response(PayrollTaxSlabSetSerializer(tax_slab_set).data)


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
        queryset = PayrollRun.objects.filter(organisation=organisation).prefetch_related('items__employee__user')
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
        return Response(PayrollRunSerializer(pay_run).data, status=status.HTTP_201_CREATED)


class OrgPayrollRunDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun.objects.prefetch_related('items__employee__user'), organisation=organisation, id=pk)
        return Response(PayrollRunSerializer(pay_run).data)


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
        return Response(PayrollRunSerializer(pay_run).data)


class OrgPayrollRunFinalizeView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        try:
            pay_run = finalize_pay_run(pay_run, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PayrollRunSerializer(pay_run).data)


class OrgPayrollRunRerunView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        try:
            rerun = rerun_payroll_run(pay_run, actor=request.user, requester_user=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PayrollRunSerializer(rerun).data, status=status.HTTP_201_CREATED)


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


class MyPayslipDownloadView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, pk):
        employee = _get_employee(request)
        payslip = get_object_or_404(Payslip, employee=employee, id=pk)
        filename = f"{payslip.slip_number.replace('/', '-')}.txt"
        payload = payslip.rendered_text or json.dumps(payslip.snapshot, indent=2, sort_keys=True)
        response = HttpResponse(payload, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


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
