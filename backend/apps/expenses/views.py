from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee

from .models import ExpenseClaim, ExpenseClaimStatus
from .serializers import ExpenseClaimSerializer, ExpenseClaimStatusUpdateSerializer, ExpenseClaimWriteSerializer
from .services import create_expense_claim, submit_expense_claim


def _get_employee(request):
    employee = get_active_employee(request, request.user)
    if employee is None:
        raise ValueError('Select an employee workspace to continue.')
    return employee


class MyExpenseClaimListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        claims = (
            ExpenseClaim.objects.filter(employee=employee)
            .select_related('employee__user', 'approval_run', 'reimbursement_pay_run')
            .prefetch_related('lines')
            .order_by('-claim_date', '-created_at')
        )
        return Response(ExpenseClaimSerializer(claims, many=True).data)

    def post(self, request):
        employee = _get_employee(request)
        serializer = ExpenseClaimWriteSerializer(data=request.data, context={'employee': employee})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        claim = create_expense_claim(
            employee=employee,
            title=payload['title'],
            claim_date=payload['claim_date'],
            policy=payload.get('policy'),
            currency=payload.get('currency', 'INR'),
            lines=payload['lines'],
            actor=request.user,
        )
        if payload.get('submit', True):
            claim = submit_expense_claim(claim, requester=employee, actor=request.user)
        return Response(ExpenseClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class MyExpenseClaimDetailView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, pk):
        employee = _get_employee(request)
        claim = get_object_or_404(
            ExpenseClaim.objects.select_related('employee__user', 'approval_run', 'reimbursement_pay_run').prefetch_related('lines'),
            employee=employee,
            id=pk,
        )
        return Response(ExpenseClaimSerializer(claim).data)


class MyExpenseClaimSubmitView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request, pk):
        employee = _get_employee(request)
        claim = get_object_or_404(ExpenseClaim, employee=employee, id=pk)
        try:
            claim = submit_expense_claim(claim, requester=employee, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseClaimSerializer(claim).data)


class MyExpenseClaimStatusView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def patch(self, request, pk):
        employee = _get_employee(request)
        claim = get_object_or_404(ExpenseClaim, employee=employee, id=pk)
        serializer = ExpenseClaimStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if claim.status not in [ExpenseClaimStatus.DRAFT, ExpenseClaimStatus.REJECTED]:
            return Response({'error': 'Only draft or rejected expense claims can be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)
        claim.status = ExpenseClaimStatus.CANCELLED
        claim.save(update_fields=['status', 'modified_at'])
        return Response(ExpenseClaimSerializer(claim).data)


class OrgExpenseClaimListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        claims = ExpenseClaim.objects.filter(organisation=organisation).select_related(
            'employee__user',
            'approval_run',
            'reimbursement_pay_run',
        ).prefetch_related('lines')

        status_filter = request.query_params.get('status')
        if status_filter:
            claims = claims.filter(status=status_filter)

        reimbursement_status = request.query_params.get('reimbursement_status')
        if reimbursement_status:
            claims = claims.filter(reimbursement_status=reimbursement_status)

        employee_id = request.query_params.get('employee')
        if employee_id:
            claims = claims.filter(employee_id=employee_id)

        claims = claims.order_by('-claim_date', '-created_at')
        return Response(ExpenseClaimSerializer(claims, many=True).data)


class OrgExpenseClaimDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        claim = get_object_or_404(
            ExpenseClaim.objects.select_related('employee__user', 'approval_run', 'reimbursement_pay_run').prefetch_related('lines'),
            organisation=organisation,
            id=pk,
        )
        return Response(ExpenseClaimSerializer(claim).data)
