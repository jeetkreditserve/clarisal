from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsControlTowerUser, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.employees.models import Employee, EmployeeStatus

from .models import CompensationAssignment, CompensationTemplate, PayrollRun, PayrollTaxSlabSet, Payslip
from .serializers import (
    CompensationAssignmentSerializer,
    CompensationAssignmentWriteSerializer,
    CompensationTemplateSerializer,
    CompensationTemplateWriteSerializer,
    PayrollComponentSerializer,
    PayrollRunSerializer,
    PayrollRunWriteSerializer,
    PayrollTaxSlabSetSerializer,
    PayrollTaxSlabSetWriteSerializer,
    PayslipSerializer,
)
from .services import (
    assign_employee_compensation,
    calculate_pay_run,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
    finalize_pay_run,
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
                'payslip_count': Payslip.objects.filter(organisation=organisation).count(),
            }
        )


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


class OrgPayrollRunCalculateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        try:
            pay_run = calculate_pay_run(pay_run, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PayrollRunSerializer(pay_run).data)


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
