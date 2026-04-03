from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from .models import (
    BloodTypeChoice,
    EducationRecord,
    Employee,
    EmployeeBankAccount,
    EmployeeEmergencyContact,
    EmployeeFamilyMember,
    EmployeeGovernmentId,
    EmployeeOnboardingStatus,
    EmployeeOffboardingProcess,
    EmployeeOffboardingTask,
    EmployeeProfile,
    EmployeeStatus,
    EmploymentType,
    FamilyRelationChoice,
    GovernmentIdType,
    OffboardingTaskStatus,
)


class EmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    office_location_name = serializers.CharField(source='office_location.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_code',
            'full_name',
            'email',
            'designation',
            'employment_type',
            'date_of_joining',
            'status',
            'department_name',
            'office_location_name',
        ]


class CtEmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    office_location_name = serializers.CharField(source='office_location.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_code',
            'full_name',
            'designation',
            'status',
            'department_name',
            'office_location_name',
        ]


class EmployeeInviteSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    company_email = serializers.EmailField()
    designation = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    employment_type = serializers.ChoiceField(choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    office_location_id = serializers.UUIDField(required=False, allow_null=True)
    required_document_type_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)


class EmployeeUpdateSerializer(serializers.Serializer):
    designation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    employment_type = serializers.ChoiceField(choices=EmploymentType.choices, required=False)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    office_location_id = serializers.UUIDField(required=False, allow_null=True)
    leave_approval_workflow_id = serializers.UUIDField(required=False, allow_null=True)
    on_duty_approval_workflow_id = serializers.UUIDField(required=False, allow_null=True)
    attendance_regularization_approval_workflow_id = serializers.UUIDField(required=False, allow_null=True)


class EmployeeMarkJoinedSerializer(serializers.Serializer):
    employee_code = serializers.CharField(max_length=20)
    date_of_joining = serializers.DateField()
    designation = serializers.CharField(max_length=255)
    reporting_to_employee_id = serializers.UUIDField()


class EmployeeEndEmploymentSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            EmployeeStatus.RESIGNED,
            EmployeeStatus.RETIRED,
            EmployeeStatus.TERMINATED,
        ]
    )
    date_of_exit = serializers.DateField()
    exit_reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    exit_notes = serializers.CharField(required=False, allow_blank=True, default='')


class OffboardingTaskSerializer(serializers.ModelSerializer):
    completed_by_name = serializers.CharField(source='completed_by.full_name', read_only=True)

    class Meta:
        model = EmployeeOffboardingTask
        fields = [
            'id',
            'code',
            'title',
            'description',
            'owner',
            'status',
            'note',
            'due_date',
            'is_required',
            'completed_at',
            'completed_by_name',
            'created_at',
            'modified_at',
        ]


class OffboardingTaskUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OffboardingTaskStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True, default='')


class OffboardingProcessSerializer(serializers.ModelSerializer):
    tasks = OffboardingTaskSerializer(many=True, read_only=True)
    required_task_count = serializers.SerializerMethodField()
    completed_required_task_count = serializers.SerializerMethodField()
    pending_required_task_count = serializers.SerializerMethodField()
    pending_document_requests = serializers.SerializerMethodField()
    has_primary_bank_account = serializers.SerializerMethodField()
    fnf_settlement_id = serializers.SerializerMethodField()
    fnf_status = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeOffboardingProcess
        fields = [
            'id',
            'status',
            'exit_status',
            'date_of_exit',
            'exit_reason',
            'exit_notes',
            'started_at',
            'completed_at',
            'required_task_count',
            'completed_required_task_count',
            'pending_required_task_count',
            'pending_document_requests',
            'has_primary_bank_account',
            'fnf_settlement_id',
            'fnf_status',
            'tasks',
        ]

    def get_required_task_count(self, obj):
        return obj.tasks.filter(is_required=True).count()

    def get_completed_required_task_count(self, obj):
        return obj.tasks.filter(is_required=True, status__in=['COMPLETED', 'WAIVED']).count()

    def get_pending_required_task_count(self, obj):
        return max(self.get_required_task_count(obj) - self.get_completed_required_task_count(obj), 0)

    def get_pending_document_requests(self, obj):
        return obj.employee.document_requests.filter(status__in=['REQUESTED', 'REJECTED']).count()

    def get_has_primary_bank_account(self, obj):
        return obj.employee.bank_accounts.filter(is_primary=True).exists()

    def _get_fnf_settlement(self, obj):
        try:
            return obj.fnf_settlement
        except ObjectDoesNotExist:
            return None

    def get_fnf_settlement_id(self, obj):
        fnf_settlement = self._get_fnf_settlement(obj)
        return str(fnf_settlement.id) if fnf_settlement is not None else None

    def get_fnf_status(self, obj):
        fnf_settlement = self._get_fnf_settlement(obj)
        return fnf_settlement.status if fnf_settlement is not None else None


class EmployeeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfile
        exclude = ['id', 'employee']


class EducationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationRecord
        fields = [
            'id',
            'degree',
            'institution',
            'field_of_study',
            'start_year',
            'end_year',
            'grade',
            'is_current',
            'created_at',
            'modified_at',
        ]


class GovernmentIdSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(source='masked_identifier', read_only=True)

    class Meta:
        model = EmployeeGovernmentId
        fields = ['id', 'id_type', 'identifier', 'name_on_id', 'status', 'metadata', 'created_at', 'modified_at']


class GovernmentIdWriteSerializer(serializers.Serializer):
    id_type = serializers.ChoiceField(choices=GovernmentIdType.choices)
    identifier = serializers.CharField(max_length=32)
    name_on_id = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.JSONField(required=False)


class BankAccountSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='masked_account_number', read_only=True)
    ifsc = serializers.CharField(source='masked_ifsc', read_only=True)

    class Meta:
        model = EmployeeBankAccount
        fields = [
            'id',
            'account_holder_name',
            'bank_name',
            'account_number',
            'ifsc',
            'account_type',
            'branch_name',
            'is_primary',
            'created_at',
            'modified_at',
        ]


class BankAccountWriteSerializer(serializers.Serializer):
    account_holder_name = serializers.CharField(max_length=255)
    bank_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    account_number = serializers.CharField(max_length=32)
    ifsc = serializers.CharField(max_length=16)
    account_type = serializers.CharField(required=False, default='SALARY')
    branch_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    is_primary = serializers.BooleanField(required=False, default=False)


class ProfileCompletionSerializer(serializers.Serializer):
    percent = serializers.IntegerField()
    completed_sections = serializers.ListField(child=serializers.CharField())
    missing_sections = serializers.ListField(child=serializers.CharField())


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeEmergencyContact
        fields = [
            'id',
            'full_name',
            'relation',
            'phone_number',
            'alternate_phone_number',
            'address',
            'is_primary',
            'created_at',
            'modified_at',
        ]


class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeFamilyMember
        fields = [
            'id',
            'full_name',
            'relation',
            'date_of_birth',
            'contact_number',
            'is_dependent',
            'created_at',
            'modified_at',
        ]


class OnboardingBasicDetailsSerializer(serializers.Serializer):
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    marital_status = serializers.CharField(required=False, allow_blank=True)
    nationality = serializers.CharField(required=False, allow_blank=True)
    blood_type = serializers.ChoiceField(choices=BloodTypeChoice.choices, required=False, allow_blank=True)
    phone_personal = serializers.CharField(required=False, allow_blank=True)
    address_line1 = serializers.CharField(required=False, allow_blank=True)
    address_line2 = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    state_code = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    country_code = serializers.CharField(required=False, allow_blank=True)
    pincode = serializers.CharField(required=False, allow_blank=True)
    pan_identifier = serializers.CharField(required=False, allow_blank=True)
    aadhaar_identifier = serializers.CharField(required=False, allow_blank=True)


class EmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    suggested_employee_code = serializers.SerializerMethodField()
    profile = EmployeeProfileSerializer(read_only=True)
    education_records = EducationRecordSerializer(many=True, read_only=True)
    government_ids = GovernmentIdSerializer(many=True, read_only=True)
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    family_members = FamilyMemberSerializer(many=True, read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    leave_approval_workflow_id = serializers.UUIDField(source='leave_approval_workflow.id', read_only=True, allow_null=True)
    leave_approval_workflow_name = serializers.CharField(source='leave_approval_workflow.name', read_only=True, allow_null=True)
    on_duty_approval_workflow_id = serializers.UUIDField(source='on_duty_approval_workflow.id', read_only=True, allow_null=True)
    on_duty_approval_workflow_name = serializers.CharField(source='on_duty_approval_workflow.name', read_only=True, allow_null=True)
    attendance_regularization_approval_workflow_id = serializers.UUIDField(
        source='attendance_regularization_approval_workflow.id',
        read_only=True,
        allow_null=True,
    )
    attendance_regularization_approval_workflow_name = serializers.CharField(
        source='attendance_regularization_approval_workflow.name',
        read_only=True,
        allow_null=True,
    )
    effective_approval_workflows = serializers.SerializerMethodField()
    offboarding = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_code',
            'suggested_employee_code',
            'full_name',
            'email',
            'designation',
            'employment_type',
            'date_of_joining',
            'date_of_exit',
            'status',
            'onboarding_status',
            'department',
            'office_location',
            'reporting_to',
            'profile',
            'education_records',
            'government_ids',
            'bank_accounts',
            'family_members',
            'emergency_contacts',
            'leave_approval_workflow_id',
            'leave_approval_workflow_name',
            'on_duty_approval_workflow_id',
            'on_duty_approval_workflow_name',
            'attendance_regularization_approval_workflow_id',
            'attendance_regularization_approval_workflow_name',
            'effective_approval_workflows',
            'offboarding',
        ]

    def get_suggested_employee_code(self, obj):
        if obj.employee_code:
            return obj.employee_code
        from .services import get_next_employee_code

        return get_next_employee_code(obj.organisation)

    def get_effective_approval_workflows(self, obj):
        from apps.approvals.models import ApprovalRequestKind
        from apps.approvals.services import resolve_workflow_with_source

        def serialize_effective(request_kind):
            try:
                workflow, source = resolve_workflow_with_source(obj, request_kind)
            except ValueError:
                return {
                    'request_kind': request_kind,
                    'workflow_id': None,
                    'workflow_name': None,
                    'source': 'UNCONFIGURED',
                }
            return {
                'request_kind': request_kind,
                'workflow_id': str(workflow.id),
                'workflow_name': workflow.name,
                'source': source,
            }

        return {
            'leave': serialize_effective(ApprovalRequestKind.LEAVE),
            'on_duty': serialize_effective(ApprovalRequestKind.ON_DUTY),
            'attendance_regularization': serialize_effective(ApprovalRequestKind.ATTENDANCE_REGULARIZATION),
        }

    def get_offboarding(self, obj):
        try:
            process = obj.offboarding_process
        except EmployeeOffboardingProcess.DoesNotExist:
            return None
        return OffboardingProcessSerializer(process).data


class CtEmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    office_location_name = serializers.CharField(source='office_location.name', read_only=True, allow_null=True)
    reporting_to_name = serializers.CharField(source='reporting_to.user.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_code',
            'full_name',
            'designation',
            'employment_type',
            'date_of_joining',
            'date_of_exit',
            'status',
            'onboarding_status',
            'department_name',
            'office_location_name',
            'reporting_to_name',
        ]
