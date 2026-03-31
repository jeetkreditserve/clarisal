from django.db.models import Prefetch, Q

from .models import (
    EducationRecord,
    Employee,
    EmployeeBankAccount,
    EmployeeGovernmentId,
    EmployeeProfile,
)


def list_employees(organisation, status=None, search=None):
    queryset = (
        Employee.objects.filter(organisation=organisation)
        .select_related('user', 'department', 'office_location', 'reporting_to__user')
        .prefetch_related('education_records', 'government_ids', 'bank_accounts', 'documents')
        .order_by('-created_at')
    )
    if status:
        queryset = queryset.filter(status=status)
    if search:
        queryset = queryset.filter(
            Q(employee_code__icontains=search)
            | Q(user__email__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(designation__icontains=search)
        )
    return queryset


def get_employee(organisation, pk):
    return list_employees(organisation).get(id=pk)


def get_employee_self(user, organisation=None):
    queryset = (
        Employee.objects.select_related('user', 'profile', 'department', 'office_location')
        .prefetch_related('education_records', 'government_ids', 'bank_accounts', 'documents')
        .filter(user=user)
    )
    if organisation is not None:
        queryset = queryset.filter(organisation=organisation)
    return queryset.get()
