from rest_framework import serializers

from .models import (
    AppraisalCycle,
    AppraisalReview,
    CalibrationSession,
    CalibrationSessionEntry,
    FeedbackRequest,
    Goal,
    GoalCycle,
)


class GoalCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalCycle
        fields = ['id', 'name', 'start_date', 'end_date', 'status', 'auto_create_review_cycle', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']


class GoalSerializer(serializers.ModelSerializer):
    cycle = serializers.UUIDField(source='cycle_id', read_only=True)
    employee = serializers.UUIDField(source='employee_id', read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id',
            'cycle',
            'employee',
            'title',
            'description',
            'target',
            'metric',
            'weight',
            'status',
            'due_date',
            'progress_percent',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class AppraisalCycleSerializer(serializers.ModelSerializer):
    goal_cycle = serializers.UUIDField(source='goal_cycle_id', read_only=True, allow_null=True)
    goal_cycle_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    completion_stats = serializers.SerializerMethodField()

    class Meta:
        model = AppraisalCycle
        fields = [
            'id',
            'name',
            'review_type',
            'goal_cycle',
            'goal_cycle_id',
            'start_date',
            'end_date',
            'status',
            'is_probation_review',
            'self_assessment_deadline',
            'peer_review_deadline',
            'manager_review_deadline',
            'calibration_deadline',
            'activated_at',
            'completed_at',
            'completion_stats',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'is_probation_review', 'activated_at', 'completed_at', 'completion_stats', 'created_at']

    def create(self, validated_data):
        validated_data['goal_cycle_id'] = validated_data.pop('goal_cycle_id', None)
        return super().create(validated_data)

    def get_completion_stats(self, obj):
        self_reviews = obj.reviews.filter(relationship='SELF')
        manager_reviews = obj.reviews.filter(relationship='MANAGER')
        feedback_requests = obj.feedback_requests.all()
        return {
            'self_submitted': self_reviews.filter(status='SUBMITTED').count(),
            'self_total': self_reviews.count(),
            'manager_submitted': manager_reviews.filter(status='SUBMITTED').count(),
            'manager_total': manager_reviews.count(),
            'feedback_submitted': feedback_requests.filter(status='SUBMITTED').count(),
            'feedback_total': feedback_requests.count(),
        }


class AppraisalReviewSerializer(serializers.ModelSerializer):
    cycle = serializers.UUIDField(source='cycle_id', read_only=True)
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)
    cycle_status = serializers.CharField(source='cycle.status', read_only=True)
    employee = serializers.UUIDField(source='employee_id', read_only=True)
    reviewer = serializers.UUIDField(source='reviewer_id', read_only=True, allow_null=True)

    class Meta:
        model = AppraisalReview
        fields = [
            'id',
            'cycle',
            'cycle_name',
            'cycle_status',
            'employee',
            'reviewer',
            'relationship',
            'ratings',
            'comments',
            'status',
            'submitted_at',
        ]
        read_only_fields = ['id', 'submitted_at']


class FeedbackRequestSerializer(serializers.ModelSerializer):
    cycle = serializers.UUIDField(source='cycle_id', read_only=True)
    employee = serializers.UUIDField(source='employee_id', read_only=True)
    requested_from = serializers.UUIDField(source='requested_from_id', read_only=True)

    class Meta:
        model = FeedbackRequest
        fields = ['id', 'cycle', 'employee', 'requested_from', 'status', 'due_date', 'message']
        read_only_fields = ['id']


class FeedbackSummarySerializer(serializers.Serializer):
    response_count = serializers.IntegerField()
    dimensions = serializers.DictField(child=serializers.DictField())
    comments = serializers.ListField(child=serializers.CharField())


class MyReviewCycleSerializer(serializers.ModelSerializer):
    self_assessment = serializers.SerializerMethodField()
    feedback_summary_visible = serializers.SerializerMethodField()

    class Meta:
        model = AppraisalCycle
        fields = [
            'id',
            'name',
            'review_type',
            'status',
            'start_date',
            'end_date',
            'self_assessment_deadline',
            'peer_review_deadline',
            'manager_review_deadline',
            'calibration_deadline',
            'self_assessment',
            'feedback_summary_visible',
        ]

    def get_self_assessment(self, obj):
        employee = self.context['employee']
        review = obj.reviews.filter(employee=employee, reviewer=employee, relationship='SELF').first()
        if review is None:
            return None
        return AppraisalReviewSerializer(review).data

    def get_feedback_summary_visible(self, obj):
        return obj.status in {'MANAGER_REVIEW', 'CALIBRATION', 'COMPLETED'}


class CalibrationSessionEntrySerializer(serializers.ModelSerializer):
    employee = serializers.UUIDField(source='employee_id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    original_rating = serializers.FloatField(read_only=True)
    current_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = CalibrationSessionEntry
        fields = ['id', 'employee', 'employee_name', 'original_rating', 'current_rating', 'reason']
        read_only_fields = ['id', 'employee', 'employee_name', 'original_rating']


class CalibrationSessionSerializer(serializers.ModelSerializer):
    cycle = serializers.UUIDField(source='cycle_id', read_only=True)
    entries = CalibrationSessionEntrySerializer(many=True, read_only=True)

    class Meta:
        model = CalibrationSession
        fields = ['id', 'cycle', 'locked_at', 'entries']
        read_only_fields = ['id', 'cycle', 'locked_at', 'entries']
