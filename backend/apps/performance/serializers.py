from rest_framework import serializers

from .models import AppraisalCycle, AppraisalReview, FeedbackRequest, Goal, GoalCycle


class GoalCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalCycle
        fields = ['id', 'name', 'start_date', 'end_date', 'status', 'created_at']
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
    class Meta:
        model = AppraisalCycle
        fields = ['id', 'name', 'review_type', 'start_date', 'end_date', 'status', 'is_probation_review', 'created_at']
        read_only_fields = ['id', 'status', 'is_probation_review', 'created_at']


class AppraisalReviewSerializer(serializers.ModelSerializer):
    cycle = serializers.UUIDField(source='cycle_id', read_only=True)
    employee = serializers.UUIDField(source='employee_id', read_only=True)
    reviewer = serializers.UUIDField(source='reviewer_id', read_only=True, allow_null=True)

    class Meta:
        model = AppraisalReview
        fields = ['id', 'cycle', 'employee', 'reviewer', 'relationship', 'ratings', 'comments', 'status', 'submitted_at']
        read_only_fields = ['id', 'submitted_at']


class FeedbackRequestSerializer(serializers.ModelSerializer):
    cycle = serializers.UUIDField(source='cycle_id', read_only=True)
    employee = serializers.UUIDField(source='employee_id', read_only=True)
    requested_from = serializers.UUIDField(source='requested_from_id', read_only=True)

    class Meta:
        model = FeedbackRequest
        fields = ['id', 'cycle', 'employee', 'requested_from', 'status', 'due_date', 'message']
        read_only_fields = ['id']
