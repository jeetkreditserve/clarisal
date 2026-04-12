from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control.services import scope_employee_queryset
from apps.accounts.permissions import BelongsToActiveOrg, HasPermission, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.audit.services import log_audit_event
from apps.departments.models import Department
from apps.locations.models import OfficeLocation

from .models import (
    CustomFieldDefinition,
    CustomFieldValue,
    Designation,
    EducationRecord,
    Employee,
    EmployeeBankAccount,
    EmployeeEmergencyContact,
    EmployeeFamilyMember,
    EmployeeOffboardingProcess,
    EmployeeOffboardingTask,
    EmployeePromotionEvent,
    EmployeeTransferEvent,
    ExitInterview,
    ExitInterviewQuestion,
    ExitInterviewTemplate,
)
from .repositories import list_employees
from .serializers import (
    BankAccountSerializer,
    BankAccountWriteSerializer,
    CareerTimelineSerializer,
    CustomFieldDefinitionSerializer,
    CustomFieldDefinitionWriteSerializer,
    CustomFieldValueSerializer,
    DesignationSerializer,
    DesignationWriteSerializer,
    DirectReportSerializer,
    EducationRecordSerializer,
    EmergencyContactSerializer,
    EmployeeDetailSerializer,
    EmployeeEndEmploymentSerializer,
    EmployeeExitInterviewSerializer,
    EmployeeExitInterviewWriteSerializer,
    EmployeeInviteSerializer,
    EmployeeListSerializer,
    EmployeeMarkJoinedSerializer,
    EmployeeProfileSerializer,
    EmployeeUpdateSerializer,
    ExitInterviewSerializer,
    ExitInterviewTemplateSerializer,
    ExitInterviewTemplateWriteSerializer,
    ExitInterviewWriteSerializer,
    FamilyMemberSerializer,
    GovernmentIdSerializer,
    GovernmentIdWriteSerializer,
    OffboardingProcessSerializer,
    OffboardingTaskUpdateSerializer,
    OnboardingBasicDetailsSerializer,
    OrgChartNodeSerializer,
    PromotionEventSerializer,
    PromotionEventWriteSerializer,
    TeamMemberSummarySerializer,
    TransferEventSerializer,
    TransferEventWriteSerializer,
)
from .services import (
    apply_promotion_event,
    apply_transfer_event,
    approve_promotion_event,
    approve_transfer_event,
    complete_exit_interview,
    complete_offboarding_process,
    create_bank_account,
    create_education_record,
    create_exit_interview_template,
    create_or_update_emergency_contact,
    create_or_update_family_member,
    create_promotion_event,
    create_transfer_event,
    delete_bank_account,
    delete_education_record,
    delete_emergency_contact,
    delete_employee,
    delete_family_member,
    end_employment,
    get_employee_career_timeline,
    get_employee_dashboard,
    get_employee_direct_reports,
    get_employee_exit_interview_payload,
    get_onboarding_summary,
    get_org_chart_tree,
    get_profile_completion,
    get_reporting_team,
    invite_employee,
    mark_employee_joined,
    record_exit_interview_response,
    refresh_employee_onboarding_status,
    schedule_exit_interview,
    update_bank_account,
    update_education_record,
    update_employee,
    update_employee_profile,
    update_offboarding_process,
    update_offboarding_task,
    update_onboarding_basics,
    upsert_employee_exit_interview,
    upsert_government_id,
    validate_org_chart_cycles,
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


def _scope_org_employees(queryset, request, organisation):
    return scope_employee_queryset(
        queryset,
        request.user,
        organisation=organisation,
        request=request,
    )


class OrgEmployeeAccessMixin:
    read_permission_code = 'org.employees.read'
    write_permission_code = 'org.employees.write'

    def get_permission_code(self, request):
        if request.method in {'GET', 'HEAD', 'OPTIONS'}:
            return self.read_permission_code
        return self.write_permission_code


class EmployeeListInviteView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = _scope_org_employees(
            list_employees(
                organisation,
                status=request.query_params.get('status'),
                search=request.query_params.get('search'),
            ),
            request,
            organisation,
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
                'employee': EmployeeDetailSerializer(employee, context={'request': request}).data,
                'invitation': {'email': invitation.email, 'expires_at': invitation.expires_at},
            },
            status=status.HTTP_201_CREATED,
        )


class EmployeeDetailView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        queryset = Employee.objects.select_related(
                'user',
                'profile',
                'leave_approval_workflow',
                'on_duty_approval_workflow',
                'attendance_regularization_approval_workflow',
                'expense_approval_workflow',
                'offboarding_process',
        )
        employee = get_object_or_404(
            _scope_org_employees(queryset.filter(organisation=organisation), request, organisation),
            id=pk,
        )
        refresh_employee_onboarding_status(employee)
        return Response(EmployeeDetailSerializer(employee, context={'request': request}).data)

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(
            _scope_org_employees(Employee.objects.filter(organisation=organisation), request, organisation),
            id=pk,
        )
        serializer = EmployeeUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            employee = update_employee(employee, actor=request.user, **serializer.validated_data)
        except (ValueError, Department.DoesNotExist, OfficeLocation.DoesNotExist) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmployeeDetailSerializer(employee, context={'request': request}).data)


class EmployeeMarkJoinedView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        serializer = EmployeeMarkJoinedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            employee = mark_employee_joined(employee, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmployeeDetailSerializer(employee, context={'request': request}).data)


class EmployeeEndEmploymentView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

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
        return Response(EmployeeDetailSerializer(employee, context={'request': request}).data)


class EmployeeProbationCompleteView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

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
        return Response(EmployeeDetailSerializer(employee, context={'request': request}).data)


class EmployeeOffboardingDetailView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

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


class EmployeeOffboardingTaskDetailView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

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


class EmployeeOffboardingCompleteView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

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


class EmployeeExitInterviewDetailView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        process = EmployeeOffboardingProcess.objects.filter(
            organisation=organisation,
            employee_id=pk,
        ).select_related('employee__user').first()
        if process is None:
            return Response(None)
        payload = get_employee_exit_interview_payload(process)
        if payload is None:
            return Response(None)
        return Response(EmployeeExitInterviewSerializer(payload).data)

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        process = get_object_or_404(
            EmployeeOffboardingProcess.objects.select_related('employee__user'),
            organisation=organisation,
            employee_id=pk,
        )
        serializer = EmployeeExitInterviewWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        interviewer_employee = None
        interviewer_id = serializer.validated_data.get('interviewer_id')
        if interviewer_id is not None:
            interviewer_employee = get_object_or_404(
                Employee.objects.select_related('user'),
                organisation=organisation,
                id=interviewer_id,
            )
        interview = upsert_employee_exit_interview(
            process,
            interview_date=serializer.validated_data.get('interview_date'),
            exit_reason=serializer.validated_data.get('exit_reason', ''),
            interviewer_employee=interviewer_employee,
            overall_satisfaction=serializer.validated_data.get('overall_satisfaction'),
            would_recommend_org=serializer.validated_data.get('would_recommend_org'),
            feedback=serializer.validated_data.get('feedback', ''),
            areas_of_improvement=serializer.validated_data.get('areas_of_improvement', ''),
            actor=request.user,
        )
        payload = get_employee_exit_interview_payload(interview.process)
        return Response(EmployeeExitInterviewSerializer(payload).data)


class EmployeeDeleteView(OrgEmployeeAccessMixin, APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission, OrgAdminMutationAllowed]

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


class MyTeamView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        team = get_reporting_team(employee)
        return Response(TeamMemberSummarySerializer(team, many=True).data)


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


class DesignationListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        designations = Designation.objects.filter(
            organisation=organisation,
            is_active=True
        ).order_by('level', 'name')
        return Response(DesignationSerializer(designations, many=True).data)


class DesignationDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        designation = get_object_or_404(
            Designation, organisation=organisation, id=pk
        )
        return Response(DesignationSerializer(designation).data)

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        designation = get_object_or_404(
            Designation, organisation=organisation, id=pk
        )
        serializer = DesignationWriteSerializer(designation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        designation = serializer.save()
        return Response(DesignationSerializer(designation).data)

    def delete(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        designation = get_object_or_404(
            Designation, organisation=organisation, id=pk
        )
        designation.is_active = False
        designation.save(update_fields=['is_active', 'modified_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomFieldDefinitionListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        placement = request.query_params.get('placement')
        fields = CustomFieldDefinition.objects.filter(
            organisation=organisation,
            is_active=True
        )
        if placement:
            fields = fields.filter(placement=placement)
        fields = fields.order_by('placement', 'display_order', 'name')
        return Response(CustomFieldDefinitionSerializer(fields, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = CustomFieldDefinitionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        field = serializer.save(organisation=organisation)
        return Response(
            CustomFieldDefinitionSerializer(field).data,
            status=status.HTTP_201_CREATED
        )


class CustomFieldDefinitionDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        field = get_object_or_404(
            CustomFieldDefinition, organisation=organisation, id=pk
        )
        return Response(CustomFieldDefinitionSerializer(field).data)

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        field = get_object_or_404(
            CustomFieldDefinition, organisation=organisation, id=pk
        )
        serializer = CustomFieldDefinitionWriteSerializer(field, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        field = serializer.save()
        return Response(CustomFieldDefinitionSerializer(field).data)

    def delete(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        field = get_object_or_404(
            CustomFieldDefinition, organisation=organisation, id=pk
        )
        field.is_active = False
        field.save(update_fields=['is_active', 'modified_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmployeeCustomFieldValuesView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(
            Employee, organisation=organisation, id=employee_id
        )
        values = CustomFieldValue.objects.filter(
            employee=employee,
            is_deleted=False
        ).select_related('field_definition')
        return Response(CustomFieldValueSerializer(values, many=True).data)

    def put(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(
            Employee, organisation=organisation, id=employee_id
        )
        custom_fields = request.data.get('custom_fields', [])
        updated = []
        for field_data in custom_fields:
            field_def_id = field_data.get('field_definition_id')
            field_def = get_object_or_404(
                CustomFieldDefinition, organisation=organisation, id=field_def_id
            )
            value, created = CustomFieldValue.objects.update_or_create(
                employee=employee,
                field_definition=field_def,
                defaults={
                    'value_text': field_data.get('value_text', ''),
                    'value_number': field_data.get('value_number'),
                    'value_date': field_data.get('value_date'),
                    'value_boolean': field_data.get('value_boolean', False),
                }
            )
            updated.append(value)
        return Response(CustomFieldValueSerializer(updated, many=True).data)

class ExitInterviewTemplateListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        templates = ExitInterviewTemplate.objects.filter(organisation=organisation, is_active=True)
        serializer = ExitInterviewTemplateSerializer(templates, many=True)
        return Response(serializer.data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = ExitInterviewTemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        template = create_exit_interview_template(
            organisation=organisation,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            questions=serializer.validated_data.get('questions', []),
            actor=request.user,
        )

        return Response(
            ExitInterviewTemplateSerializer(template).data,
            status=status.HTTP_201_CREATED
        )


class ExitInterviewTemplateDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, template_id):
        organisation = get_active_admin_organisation(request, request.user)
        template = get_object_or_404(
            ExitInterviewTemplate.objects.filter(organisation=organisation),
            id=template_id
        )
        serializer = ExitInterviewTemplateSerializer(template)
        return Response(serializer.data)


class ExitInterviewListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        process_id = request.query_params.get('process_id')

        if process_id:
            interviews = ExitInterview.objects.filter(
                process__organisation=organisation,
                process_id=process_id
            )
        else:
            interviews = ExitInterview.objects.filter(
                process__organisation=organisation
            )

        serializer = ExitInterviewSerializer(interviews, many=True)
        return Response(serializer.data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = ExitInterviewWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        process_id = serializer.validated_data.get('process_id') or request.data.get('process_id')
        process = get_object_or_404(
            EmployeeOffboardingProcess.objects.filter(organisation=organisation),
            id=process_id
        )

        template = None
        template_id = serializer.validated_data.get('template_id')
        if template_id:
            template = get_object_or_404(
                ExitInterviewTemplate.objects.filter(organisation=organisation),
                id=template_id
            )

        interview = schedule_exit_interview(
            process=process,
            scheduled_date=serializer.validated_data.get('scheduled_date'),
            stage=serializer.validated_data.get('stage', 'EXIT'),
            template=template,
            actor=request.user,
        )

        if serializer.validated_data.get('responses'):
            for resp_data in serializer.validated_data['responses']:
                question = get_object_or_404(ExitInterviewQuestion, id=resp_data['question_id'])
                record_exit_interview_response(
                    interview=interview,
                    question=question,
                    rating_value=resp_data.get('rating_value'),
                    text_value=resp_data.get('text_value', ''),
                    choice_value=resp_data.get('choice_value', ''),
                    boolean_value=resp_data.get('boolean_value'),
                    actor=request.user,
                )

        return Response(
            ExitInterviewSerializer(interview).data,
            status=status.HTTP_201_CREATED
        )


class ExitInterviewDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, interview_id):
        organisation = get_active_admin_organisation(request, request.user)
        interview = get_object_or_404(
            ExitInterview.objects.filter(process__organisation=organisation),
            id=interview_id
        )
        serializer = ExitInterviewSerializer(interview)
        return Response(serializer.data)

    def patch(self, request, interview_id):
        organisation = get_active_admin_organisation(request, request.user)
        interview = get_object_or_404(
            ExitInterview.objects.filter(process__organisation=organisation),
            id=interview_id
        )

        serializer = ExitInterviewWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get('responses'):
            for resp_data in serializer.validated_data['responses']:
                question = get_object_or_404(ExitInterviewQuestion, id=resp_data['question_id'])
                record_exit_interview_response(
                    interview=interview,
                    question=question,
                    rating_value=resp_data.get('rating_value'),
                    text_value=resp_data.get('text_value', ''),
                    choice_value=resp_data.get('choice_value', ''),
                    boolean_value=resp_data.get('boolean_value'),
                    actor=request.user,
                )

        if serializer.validated_data.get('overall_rating') is not None:
            interview = complete_exit_interview(
                interview=interview,
                notes=serializer.validated_data.get('notes', ''),
                overall_rating=serializer.validated_data.get('overall_rating'),
                conducted_by=request.user,
                actor=request.user,
            )
        elif serializer.validated_data.get('notes'):
            interview.notes = serializer.validated_data['notes']
            interview.save(update_fields=['notes', 'modified_at'])

        return Response(ExitInterviewSerializer(interview).data)

class OrgChartView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'

        tree = get_org_chart_tree(organisation, include_inactive=include_inactive)
        serializer = OrgChartNodeSerializer(tree, many=True)
        return Response(serializer.data)


class OrgChartCyclesView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        cycles = validate_org_chart_cycles(organisation)
        return Response({'cycles': cycles, 'has_cycles': len(cycles) > 0})


class EmployeeDirectReportsView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(
            Employee.objects.filter(organisation=organisation),
            id=employee_id
        )
        include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'

        direct_reports = get_employee_direct_reports(employee, include_inactive=include_inactive)
        serializer = DirectReportSerializer(direct_reports, many=True)
        return Response(serializer.data)

class TransferEventListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        employee_id = request.query_params.get('employee_id')

        if employee_id:
            transfers = EmployeeTransferEvent.objects.filter(
                employee__organisation=organisation,
                employee_id=employee_id
            )
        else:
            transfers = EmployeeTransferEvent.objects.filter(employee__organisation=organisation)

        transfers = transfers.select_related('employee', 'from_department', 'to_department', 'requested_by', 'approved_by')
        serializer = TransferEventSerializer(transfers, many=True)
        return Response(serializer.data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = TransferEventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = get_object_or_404(
            Employee.objects.filter(organisation=organisation),
            id=serializer.validated_data['employee_id']
        )

        to_department = None
        if serializer.validated_data.get('to_department_id'):
            to_department = get_object_or_404(Department, id=serializer.validated_data['to_department_id'])

        to_location = None
        if serializer.validated_data.get('to_location_id'):
            to_location = get_object_or_404(OfficeLocation, id=serializer.validated_data['to_location_id'])

        to_designation = None
        if serializer.validated_data.get('to_designation_id'):
            to_designation = get_object_or_404(Designation, id=serializer.validated_data['to_designation_id'])

        transfer = create_transfer_event(
            employee=employee,
            to_department=to_department,
            to_location=to_location,
            to_designation=to_designation,
            effective_date=serializer.validated_data['effective_date'],
            reason=serializer.validated_data.get('reason', ''),
            requested_by=request.user,
        )

        return Response(
            TransferEventSerializer(transfer).data,
            status=status.HTTP_201_CREATED
        )


class TransferEventDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, transfer_id):
        organisation = get_active_admin_organisation(request, request.user)
        transfer = get_object_or_404(
            EmployeeTransferEvent.objects.filter(employee__organisation=organisation),
            id=transfer_id
        )
        serializer = TransferEventSerializer(transfer)
        return Response(serializer.data)

    def patch(self, request, transfer_id):
        organisation = get_active_admin_organisation(request, request.user)
        transfer = get_object_or_404(
            EmployeeTransferEvent.objects.filter(employee__organisation=organisation),
            id=transfer_id
        )

        action = request.data.get('action')

        if action == 'approve':
            notes = request.data.get('notes', '')
            transfer = approve_transfer_event(transfer, approved_by=request.user, notes=notes)
        elif action == 'apply':
            transfer = apply_transfer_event(transfer, actor=request.user)
        elif action == 'reject':
            transfer.status = 'REJECTED'
            transfer.notes = request.data.get('notes', '')
            transfer.save()
        elif action == 'cancel':
            transfer.status = 'CANCELLED'
            transfer.save()

        return Response(TransferEventSerializer(transfer).data)


class PromotionEventListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        employee_id = request.query_params.get('employee_id')

        if employee_id:
            promotions = EmployeePromotionEvent.objects.filter(
                employee__organisation=organisation,
                employee_id=employee_id
            )
        else:
            promotions = EmployeePromotionEvent.objects.filter(employee__organisation=organisation)

        promotions = promotions.select_related('employee', 'from_designation', 'to_designation', 'requested_by', 'approved_by')
        serializer = PromotionEventSerializer(promotions, many=True)
        return Response(serializer.data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = PromotionEventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = get_object_or_404(
            Employee.objects.filter(organisation=organisation),
            id=serializer.validated_data['employee_id']
        )

        to_designation = get_object_or_404(
            Designation.objects.filter(organisation=organisation),
            id=serializer.validated_data['to_designation_id']
        )

        revised_compensation = None
        if serializer.validated_data.get('revised_compensation_id'):
            from apps.payroll.models import CompensationAssignment
            revised_compensation = get_object_or_404(
                CompensationAssignment,
                id=serializer.validated_data['revised_compensation_id']
            )

        promotion = create_promotion_event(
            employee=employee,
            to_designation=to_designation,
            effective_date=serializer.validated_data['effective_date'],
            revised_compensation=revised_compensation,
            reason=serializer.validated_data.get('reason', ''),
            requested_by=request.user,
        )

        return Response(
            PromotionEventSerializer(promotion).data,
            status=status.HTTP_201_CREATED
        )


class PromotionEventDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, promotion_id):
        organisation = get_active_admin_organisation(request, request.user)
        promotion = get_object_or_404(
            EmployeePromotionEvent.objects.filter(employee__organisation=organisation),
            id=promotion_id
        )
        serializer = PromotionEventSerializer(promotion)
        return Response(serializer.data)

    def patch(self, request, promotion_id):
        organisation = get_active_admin_organisation(request, request.user)
        promotion = get_object_or_404(
            EmployeePromotionEvent.objects.filter(employee__organisation=organisation),
            id=promotion_id
        )

        action = request.data.get('action')

        if action == 'approve':
            notes = request.data.get('notes', '')
            promotion = approve_promotion_event(promotion, approved_by=request.user, notes=notes)
        elif action == 'apply':
            promotion = apply_promotion_event(promotion, actor=request.user)
        elif action == 'reject':
            promotion.status = 'REJECTED'
            promotion.notes = request.data.get('notes', '')
            promotion.save()
        elif action == 'cancel':
            promotion.status = 'CANCELLED'
            promotion.save()

        return Response(PromotionEventSerializer(promotion).data)


class EmployeeCareerTimelineView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(
            Employee.objects.filter(organisation=organisation),
            id=employee_id
        )

        timeline = get_employee_career_timeline(employee)
        serializer = CareerTimelineSerializer(timeline, many=True)
        return Response(serializer.data)
