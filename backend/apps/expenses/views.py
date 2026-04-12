from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee

from .models import ExpenseCategory, ExpenseClaim, ExpenseClaimStatus, ExpensePolicy
from .serializers import (
    ExpenseClaimSerializer,
    ExpenseClaimStatusUpdateSerializer,
    ExpenseClaimWriteSerializer,
    ExpensePolicySerializer,
    ExpensePolicyWriteSerializer,
    ExpenseReceiptSerializer,
    ExpenseReceiptUploadSerializer,
)
from .services import (
    create_expense_claim,
    submit_expense_claim,
    summarize_expense_claims_for_org,
    update_expense_claim,
    upload_expense_receipt,
)


def _get_employee(request):
    employee = get_active_employee(request, request.user)
    if employee is None:
        raise ValueError('Select an employee workspace to continue.')
    return employee


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


def _expense_claim_queryset():
    return ExpenseClaim.objects.select_related(
        'employee__user',
        'approval_run',
        'reimbursement_pay_run',
    ).prefetch_related('lines__receipts', 'lines__category')


def _upsert_policy_categories(policy, categories):
    policy.categories.all().delete()
    for payload in categories:
        ExpenseCategory.objects.create(
            policy=policy,
            code=payload['code'],
            name=payload['name'],
            per_claim_limit=payload.get('per_claim_limit'),
            requires_receipt=payload.get('requires_receipt', False),
            is_active=payload.get('is_active', True),
        )


class MyExpensePolicyListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        policies = ExpensePolicy.objects.filter(
            organisation=employee.organisation,
            is_active=True,
        ).prefetch_related('categories')
        return Response(ExpensePolicySerializer(policies, many=True).data)


class MyExpenseClaimListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        claims = _expense_claim_queryset().filter(employee=employee).order_by('-claim_date', '-created_at')
        return Response(ExpenseClaimSerializer(claims, many=True).data)

    def post(self, request):
        employee = _get_employee(request)
        serializer = ExpenseClaimWriteSerializer(data=request.data, context={'employee': employee})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
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
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        claim.refresh_from_db()
        return Response(ExpenseClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class MyExpenseClaimDetailView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, pk):
        employee = _get_employee(request)
        claim = get_object_or_404(_expense_claim_queryset(), employee=employee, id=pk)
        return Response(ExpenseClaimSerializer(claim).data)

    def patch(self, request, pk):
        employee = _get_employee(request)
        claim = get_object_or_404(ExpenseClaim, employee=employee, id=pk)
        serializer = ExpenseClaimWriteSerializer(data=request.data, context={'employee': employee})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            claim = update_expense_claim(
                claim,
                requester=employee,
                title=payload['title'],
                claim_date=payload['claim_date'],
                lines=payload['lines'],
                policy=payload.get('policy'),
                currency=payload.get('currency', 'INR'),
                actor=request.user,
            )
            if payload.get('submit', False):
                claim = submit_expense_claim(claim, requester=employee, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        claim.refresh_from_db()
        return Response(ExpenseClaimSerializer(claim).data)


class MyExpenseReceiptUploadView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request, pk):
        employee = _get_employee(request)
        claim = get_object_or_404(ExpenseClaim, employee=employee, id=pk)
        serializer = ExpenseReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if claim.status not in [ExpenseClaimStatus.DRAFT, ExpenseClaimStatus.REJECTED]:
            return Response({'error': 'Receipts can only be uploaded while the claim is editable.'}, status=status.HTTP_400_BAD_REQUEST)
        line = get_object_or_404(claim.lines.all(), id=serializer.validated_data['line_id'])
        try:
            receipt = upload_expense_receipt(
                line=line,
                file_obj=serializer.validated_data['file'],
                uploaded_by=request.user,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)


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


class OrgExpensePolicyListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        policies = ExpensePolicy.objects.filter(organisation=organisation).prefetch_related('categories').order_by('name')
        return Response(ExpensePolicySerializer(policies, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = ExpensePolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        with transaction.atomic():
            policy = ExpensePolicy.objects.create(
                organisation=organisation,
                name=payload['name'],
                description=payload.get('description', ''),
                currency=payload.get('currency', 'INR'),
                is_active=payload.get('is_active', True),
            )
            _upsert_policy_categories(policy, payload.get('categories', []))
        return Response(ExpensePolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class OrgExpensePolicyDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        policy = get_object_or_404(ExpensePolicy.objects.filter(organisation=organisation), id=pk)
        serializer = ExpensePolicyWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        with transaction.atomic():
            for field in ['name', 'description', 'currency', 'is_active']:
                if field in payload:
                    setattr(policy, field, payload[field])
            policy.save()
            if 'categories' in payload:
                _upsert_policy_categories(policy, payload['categories'])
        return Response(ExpensePolicySerializer(policy).data)


class OrgExpenseClaimSummaryView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        return Response(summarize_expense_claims_for_org(organisation))


class OrgExpenseClaimListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        claims = _expense_claim_queryset().filter(organisation=organisation)

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
        organisation = _get_admin_organisation(request)
        claim = get_object_or_404(_expense_claim_queryset().filter(organisation=organisation), id=pk)
        return Response(ExpenseClaimSerializer(claim).data)
