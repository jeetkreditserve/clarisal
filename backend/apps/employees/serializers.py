from rest_framework import serializers

from .models import (
    EducationRecord,
    Employee,
    EmployeeBankAccount,
    EmployeeGovernmentId,
    EmployeeProfile,
    EmploymentType,
    GovernmentIdType,
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


class EmployeeInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    designation = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    employment_type = serializers.ChoiceField(choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    office_location_id = serializers.UUIDField(required=False, allow_null=True)


class EmployeeUpdateSerializer(serializers.Serializer):
    designation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    employment_type = serializers.ChoiceField(choices=EmploymentType.choices, required=False)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    office_location_id = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.CharField(required=False)


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
            'updated_at',
        ]


class GovernmentIdSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(source='masked_identifier', read_only=True)

    class Meta:
        model = EmployeeGovernmentId
        fields = ['id', 'id_type', 'identifier', 'name_on_id', 'status', 'metadata', 'created_at', 'updated_at']


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
            'updated_at',
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


class EmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    profile = EmployeeProfileSerializer(read_only=True)
    education_records = EducationRecordSerializer(many=True, read_only=True)
    government_ids = GovernmentIdSerializer(many=True, read_only=True)
    bank_accounts = BankAccountSerializer(many=True, read_only=True)

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
            'date_of_exit',
            'status',
            'department',
            'office_location',
            'profile',
            'education_records',
            'government_ids',
            'bank_accounts',
        ]
