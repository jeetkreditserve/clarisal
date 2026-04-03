from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.audit.services import log_audit_event
from apps.departments.models import Department
from apps.locations.models import OfficeLocation

from .models import EducationRecord, Employee, EmployeeBankAccount, EmployeeEmergencyContact, EmployeeFamilyMember, EmployeeOffboardingProcess, EmployeeOffboardingTask
from .repositories import list_employees
from .serializers import (
    BankAccountSerializer,
    BankAccountWriteSerializer,
    EducationRecordSerializer,
    EmployeeDetailSerializer,
    EmployeeEndEmploymentSerializer,
    EmployeeInviteSerializer,
    EmployeeListSerializer,
    EmployeeMarkJoinedSerializer,
    EmployeeProfileSerializer,
    EmployeeUpdateSerializer,
    EmergencyContactSerializer,
    FamilyMemberSerializer,
    GovernmentIdSerializer,
    GovernmentIdWriteSerializer,
    OffboardingProcessSerializer,
    OffboardingTaskUpdateSerializer,
    OnboardingBasicDetailsSerializer,
)
from .services import (
    complete_offboarding_process,
    create_bank_account,
    create_education_record,
    create_or_update_emergency_contact,
    create_or_update_family_member,
    delete_bank_account,
    delete_education_record,
    delete_emergency_contact,
    delete_employee,
    delete_family_member,
    end_employment,
    get_employee_dashboard,
    get_onboarding_summary,
    get_profile_completion,
    invite_employee,
    mark_employee_joined,
    refresh_employee_onboarding_status,
    update_offboarding_process,
    update_offboarding_task,
    update_bank_account,
    update_education_record,
    update_employee,
    update_employee_profile,
    update_onboarding_basics,
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
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

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
        except (ValueError, Department.DoesNotExist, OfficeLocation.DoesNotExist) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'employee': EmployeeDetailSerializer(employee).data,
                'invitation': {'email': invitation.email, 'expires_at': invitation.expires_at},
            },
            status=status.HTTP_201_CREATED,
        )


class EmployeeDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(
            Employee.objects.select_related(
                'user',
                'profile',
                'leave_approval_workflow',
                'on_duty_approval_workflow',
                'attendance_regularization_approval_workflow',
                'offboarding_process',
            ),
            organisation=organisation,
            id=pk,
        )
        refresh_employee_onboarding_status(employee)
        return Response(EmployeeDetailSerializer(employee).data)

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        serializer = EmployeeUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            employee = update_employee(employee, actor=request.user, **serializer.validated_data)
        except (ValueError, Department.DoesNotExist, OfficeLocation.DoesNotExist) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmployeeDetailSerializer(employee).data)


class EmployeeMarkJoinedView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        serializer = EmployeeMarkJoinedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            employee = mark_employee_joined(employee, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmployeeDetailSerializer(employee).data)


class EmployeeEndEmploymentView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        serializer = EmployeeEndEmploymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            employee = end_employment(
                employee,
                actor=request.user,
                end_status=serializer.validated_data['status'],
                date_of_exit=serializer.validated_data['date_of_exit'],
                exit_reason=serializer.validated_data.get('exit_reason', ''),
                exit_notes=serializer.validated_data.get('exit_notes', ''),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmployeeDetailSerializer(employee).data)


class EmployeeProbationCompleteView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        employee.probation_end_date = None
        employee.save(update_fields=['probation_end_date', 'modified_at'])
        log_audit_event(
            request.user,
            'employee.probation.completed',
            organisation=organisation,
            target=employee,
        )
        return Response(EmployeeDetailSerializer(employee).data)


class EmployeeOffboardingDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        process = get_object_or_404(
            EmployeeOffboardingProcess.objects.select_related('employee'),
            organisation=organisation,
            employee_id=pk,
        )
        process = update_offboarding_process(
            process,
            exit_reason=request.data.get('exit_reason'),
            exit_notes=request.data.get('exit_notes'),
            actor=request.user,
        )
        return Response(OffboardingProcessSerializer(process).data)


class EmployeeOffboardingTaskDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk, task_id):
        organisation = _get_admin_organisation(request)
        task = get_object_or_404(
            EmployeeOffboardingTask.objects.select_related('process', 'process__employee'),
            process__organisation=organisation,
            process__employee_id=pk,
            id=task_id,
        )
        serializer = OffboardingTaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            task = update_offboarding_task(task, actor=request.user, status_value=serializer.validated_data['status'], note=serializer.validated_data.get('note', ''))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OffboardingProcessSerializer(task.process).data)


class EmployeeOffboardingCompleteView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        process = get_object_or_404(
            EmployeeOffboardingProcess.objects.select_related('employee'),
            organisation=organisation,
            employee_id=pk,
        )
        try:
            process = complete_offboarding_process(process, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OffboardingProcessSerializer(process).data)


class EmployeeDeleteView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def delete(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        try:
            delete_employee(employee, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyOnboardingView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        return Response(
            {
                'summary': get_onboarding_summary(employee),
                'employee': EmployeeDetailSerializer(employee).data,
                'profile': EmployeeProfileSerializer(getattr(employee, 'profile', None)).data,
                'family_members': FamilyMemberSerializer(employee.family_members.all(), many=True).data,
                'emergency_contacts': EmergencyContactSerializer(employee.emergency_contacts.all(), many=True).data,
                'government_ids': GovernmentIdSerializer(employee.government_ids.all(), many=True).data,
            }
        )

    def patch(self, request):
        employee = _get_self_employee(request)
        serializer = OnboardingBasicDetailsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile_fields = {key: value for key, value in serializer.validated_data.items() if key not in {'pan_identifier', 'aadhaar_identifier'}}
        try:
            profile = update_onboarding_basics(
                employee,
                actor=request.user,
                profile_fields=profile_fields,
                pan_identifier=serializer.validated_data.get('pan_identifier', ''),
                aadhaar_identifier=serializer.validated_data.get('aadhaar_identifier', ''),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'profile': EmployeeProfileSerializer(profile).data,
                'summary': get_onboarding_summary(employee),
            }
        )


class MyDashboardView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        calendar_month = request.query_params.get('month')
        return Response(get_employee_dashboard(employee, calendar_month=calendar_month))


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


class MyOffboardingView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        try:
            process = employee.offboarding_process
        except EmployeeOffboardingProcess.DoesNotExist:
            return Response(None)
        return Response(OffboardingProcessSerializer(process).data)

    def patch(self, request):
        employee = _get_self_employee(request)
        serializer = EmployeeProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            profile = update_employee_profile(employee, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        refresh_employee_onboarding_status(employee, actor=request.user)
        return Response(
            {
                'profile': EmployeeProfileSerializer(profile).data,
                'profile_completion': get_profile_completion(employee),
            }
        )


class MyFamilyMemberListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        return Response(FamilyMemberSerializer(employee.family_members.all(), many=True).data)

    def post(self, request):
        employee = _get_self_employee(request)
        serializer = FamilyMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = create_or_update_family_member(employee, actor=request.user, **serializer.validated_data)
        return Response(FamilyMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class MyFamilyMemberDetailView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def patch(self, request, pk):
        employee = _get_self_employee(request)
        member = get_object_or_404(EmployeeFamilyMember, employee=employee, id=pk)
        serializer = FamilyMemberSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        member = create_or_update_family_member(employee, actor=request.user, member_id=member.id, **serializer.validated_data)
        return Response(FamilyMemberSerializer(member).data)

    def delete(self, request, pk):
        employee = _get_self_employee(request)
        member = get_object_or_404(EmployeeFamilyMember, employee=employee, id=pk)
        delete_family_member(member, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyEmergencyContactListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        return Response(EmergencyContactSerializer(employee.emergency_contacts.all(), many=True).data)

    def post(self, request):
        employee = _get_self_employee(request)
        serializer = EmergencyContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = create_or_update_emergency_contact(employee, actor=request.user, **serializer.validated_data)
        return Response(EmergencyContactSerializer(contact).data, status=status.HTTP_201_CREATED)


class MyEmergencyContactDetailView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def patch(self, request, pk):
        employee = _get_self_employee(request)
        contact = get_object_or_404(EmployeeEmergencyContact, employee=employee, id=pk)
        serializer = EmergencyContactSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        contact = create_or_update_emergency_contact(employee, actor=request.user, contact_id=contact.id, **serializer.validated_data)
        return Response(EmergencyContactSerializer(contact).data)

    def delete(self, request, pk):
        employee = _get_self_employee(request)
        contact = get_object_or_404(EmployeeEmergencyContact, employee=employee, id=pk)
        delete_emergency_contact(contact, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
