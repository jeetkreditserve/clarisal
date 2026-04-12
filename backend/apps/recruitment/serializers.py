from rest_framework import serializers

from .models import (
    Application,
    ApplicationStage,
    Candidate,
    Interview,
    InterviewFormat,
    JobPosting,
    OfferLetter,
)


class InterviewSerializer(serializers.ModelSerializer):
    interviewer_id = serializers.UUIDField(read_only=True)
    interviewer_name = serializers.CharField(source='interviewer.user.full_name', read_only=True)

    class Meta:
        model = Interview
        fields = [
            'id',
            'application',
            'interviewer_id',
            'interviewer_name',
            'scheduled_at',
            'format',
            'feedback',
            'outcome',
            'meet_link',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'interviewer_name', 'interviewer_id']


class OfferLetterSerializer(serializers.ModelSerializer):
    application_id = serializers.UUIDField(read_only=True)
    onboarded_employee_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = OfferLetter
        fields = [
            'id',
            'application_id',
            'ctc_annual',
            'joining_date',
            'status',
            'template_text',
            'sent_at',
            'accepted_at',
            'expires_at',
            'onboarded_employee_id',
        ]
        read_only_fields = ['id', 'application_id', 'status', 'sent_at', 'accepted_at', 'onboarded_employee_id']


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    candidate_email = serializers.EmailField(source='candidate.email', read_only=True)
    job_posting_id = serializers.UUIDField(read_only=True)
    job_posting_title = serializers.CharField(source='job_posting.title', read_only=True)
    interviews = InterviewSerializer(many=True, read_only=True)
    offer_letter = OfferLetterSerializer(read_only=True)

    class Meta:
        model = Application
        fields = [
            'id',
            'candidate',
            'candidate_name',
            'candidate_email',
            'job_posting_id',
            'job_posting_title',
            'stage',
            'applied_at',
            'notes',
            'rejection_reason',
            'interviews',
            'offer_letter',
        ]
        read_only_fields = ['id', 'applied_at', 'candidate_name', 'candidate_email', 'job_posting_title', 'job_posting_id']

    def get_candidate_name(self, obj):
        return f'{obj.candidate.first_name} {obj.candidate.last_name}'.strip()


class CandidateSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    converted_to_employee_id = serializers.UUIDField(read_only=True, allow_null=True)
    converted_to_employee_name = serializers.CharField(source='converted_to_employee.user.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Candidate
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'phone',
            'source',
            'converted_to_employee_id',
            'converted_to_employee_name',
            'converted_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'full_name', 'converted_to_employee_id', 'converted_to_employee_name', 'converted_at']

    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip()


class CandidateDetailSerializer(CandidateSerializer):
    applications = ApplicationSerializer(many=True, read_only=True)

    class Meta(CandidateSerializer.Meta):
        fields = CandidateSerializer.Meta.fields + ['applications']


class JobPostingSerializer(serializers.ModelSerializer):
    department_id = serializers.UUIDField(read_only=True, allow_null=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    location_id = serializers.UUIDField(read_only=True, allow_null=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = JobPosting
        fields = [
            'id',
            'title',
            'department_id',
            'department_name',
            'location_id',
            'location_name',
            'description',
            'requirements',
            'status',
            'posted_at',
            'closes_at',
            'application_count',
            'created_at',
        ]
        read_only_fields = ['id', 'application_count', 'created_at']

    def get_application_count(self, obj):
        prefetched_count = getattr(obj, 'application_count', None)
        if prefetched_count is not None:
            return prefetched_count
        return obj.applications.count()


class JobPostingWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    location_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    requirements = serializers.CharField(required=False, allow_blank=True, default='')
    closes_at = serializers.DateTimeField(required=False, allow_null=True)


class ApplicationStageUpdateSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=ApplicationStage.choices)


class InterviewWriteSerializer(serializers.Serializer):
    interviewer_id = serializers.UUIDField(required=False, allow_null=True)
    scheduled_at = serializers.DateTimeField()
    format = serializers.ChoiceField(choices=InterviewFormat.choices, default=InterviewFormat.VIDEO)
    feedback = serializers.CharField(required=False, allow_blank=True, default='')
    meet_link = serializers.URLField(required=False, allow_blank=True, default='')


class OfferLetterWriteSerializer(serializers.Serializer):
    ctc_annual = serializers.DecimalField(max_digits=14, decimal_places=2)
    joining_date = serializers.DateField(required=False, allow_null=True)
    template_text = serializers.CharField(required=False, allow_blank=True, default='')
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
