from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin
from apps.employees.models import EducationRecord, Employee, EmployeeBankAccount

from .repositories import get_employee, get_employee_self, list_employees
from .serializers import (
    BankAccountSerializer,
    BankAccountWriteSerializer,
    EducationRecordSerializer,
    EmployeeDetailSerializer,
    EmployeeInviteSerializer,
    EmployeeListSerializer,
    EmployeeProfileSerializer,
    EmployeeUpdateSerializer,
    GovernmentIdSerializer,
    GovernmentIdWriteSerializer,
    ProfileCompletionSerializer,
)
from .services import (
    create_bank_account,
    create_education_record,
    delete_bank_account,
    delete_education_record,
    get_employee_dashboard,
    get_profile_completion,
    invite_employee,
    terminate_employee,
    update_bank_account,
    update_education_record,
    update_employee,
    update_employee_profile,
    upsert_government_id,
)


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


def _get_self_employee(request):
    employee = get_active_employee(request, request.user)
    if employee is None:
        raise ValueError('Select an employee workspace to continue.')
    return employee


class EmployeeListInviteView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = list_employees(
            organisation,
            status=request.query_params.get('status'),
            search=request.query_params.get('search'),
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = EmployeeListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = EmployeeInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organisation = _get_admin_organisation(request)
        try:
            employee, invitation = invite_employee(
                organisation,
                invited_by=request.user,
                **serializer.validated_data,
            )
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'employee': EmployeeDetailSerializer(employee).data,
                'invitation': {'email': invitation.email, 'expires_at': invitation.expires_at},
            },
            status=status.HTTP_201_CREATED,
        )


class EmployeeDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee.objects.select_related('user', 'profile'), organisation=organisation, id=pk)
        return Response(EmployeeDetailSerializer(employee).data)

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        serializer = EmployeeUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            employee = update_employee(employee, actor=request.user, **serializer.validated_data)
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmployeeDetailSerializer(employee).data)


class EmployeeTerminateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        try:
            employee = terminate_employee(employee, terminated_by=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmployeeDetailSerializer(employee).data)


class MyDashboardView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        return Response(get_employee_dashboard(employee))


class MyProfileView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        profile = getattr(employee, 'profile', None)
        profile_data = EmployeeProfileSerializer(profile).data if profile else {}
        return Response(
            {
                'employee': EmployeeDetailSerializer(employee).data,
                'profile': profile_data,
                'profile_completion': get_profile_completion(employee),
            }
        )

    def patch(self, request):
        employee = _get_self_employee(request)
        serializer = EmployeeProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = update_employee_profile(employee, actor=request.user, **serializer.validated_data)
        return Response(
            {
                'profile': EmployeeProfileSerializer(profile).data,
                'profile_completion': get_profile_completion(employee),
            }
        )


class MyEducationListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        return Response(EducationRecordSerializer(employee.education_records.all(), many=True).data)

    def post(self, request):
        employee = _get_self_employee(request)
        serializer = EducationRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = create_education_record(employee, actor=request.user, **serializer.validated_data)
        return Response(EducationRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class MyEducationDetailView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def patch(self, request, pk):
        employee = _get_self_employee(request)
        record = get_object_or_404(EducationRecord, employee=employee, id=pk)
        serializer = EducationRecordSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        record = update_education_record(record, actor=request.user, **serializer.validated_data)
        return Response(EducationRecordSerializer(record).data)

    def delete(self, request, pk):
        employee = _get_self_employee(request)
        record = get_object_or_404(EducationRecord, employee=employee, id=pk)
        delete_education_record(record, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyGovernmentIdListUpsertView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        return Response(GovernmentIdSerializer(employee.government_ids.all(), many=True).data)

    def post(self, request):
        employee = _get_self_employee(request)
        serializer = GovernmentIdWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record = upsert_government_id(employee, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(GovernmentIdSerializer(record).data, status=status.HTTP_201_CREATED)


class MyBankAccountListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        return Response(BankAccountSerializer(employee.bank_accounts.all(), many=True).data)

    def post(self, request):
        employee = _get_self_employee(request)
        serializer = BankAccountWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            account = create_bank_account(employee, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BankAccountSerializer(account).data, status=status.HTTP_201_CREATED)


class MyBankAccountDetailView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def patch(self, request, pk):
        employee = _get_self_employee(request)
        account = get_object_or_404(EmployeeBankAccount, employee=employee, id=pk)
        serializer = BankAccountWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            account = update_bank_account(account, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BankAccountSerializer(account).data)

    def delete(self, request, pk):
        employee = _get_self_employee(request)
        account = get_object_or_404(EmployeeBankAccount, employee=employee, id=pk)
        delete_bank_account(account, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
