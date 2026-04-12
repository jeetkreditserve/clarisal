from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Document, EmployeeDocumentRequest, OnboardingDocumentType


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)
    document_type_code = serializers.CharField(source='document_type', read_only=True)
    expires_soon = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id',
            'document_type',
            'document_type_code',
            'document_request',
            'file_name',
            'file_size',
            'mime_type',
            'status',
            'metadata',
            'version',
            'expiry_date',
            'alert_days_before',
            'expires_soon',
            'is_expired',
            'uploaded_by_email',
            'reviewed_by_email',
            'reviewed_at',
            'created_at',
        ]

    def get_expires_soon(self, obj):
        if obj.expiry_date is None:
            return False
        today = timezone.localdate()
        return today <= obj.expiry_date <= today + timedelta(days=obj.alert_days_before)

    def get_is_expired(self, obj):
        if obj.expiry_date is None:
            return False
        return obj.expiry_date < timezone.localdate()


class OnboardingDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingDocumentType
        fields = [
            'id',
            'code',
            'name',
            'category',
            'description',
            'is_active',
            'is_custom',
            'requires_identifier',
            'sort_order',
        ]


class EmployeeDocumentRequestSerializer(serializers.ModelSerializer):
    document_type = OnboardingDocumentTypeSerializer(source='document_type_ref', read_only=True)
    latest_submission = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocumentRequest
        fields = [
            'id',
            'document_type',
            'is_required',
            'status',
            'note',
            'rejection_note',
            'latest_uploaded_at',
            'verified_at',
            'latest_submission',
            'created_at',
            'modified_at',
        ]

    def get_latest_submission(self, obj):
        latest = obj.submissions.order_by('-version', '-created_at').first()
        return DocumentSerializer(latest).data if latest else None


class UploadRequestedDocumentSerializer(serializers.Serializer):
    file = serializers.FileField()
    metadata = serializers.JSONField(required=False)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    alert_days_before = serializers.IntegerField(required=False, min_value=1, max_value=365, default=30)


class LegacyUploadDocumentSerializer(UploadRequestedDocumentSerializer):
    document_type = serializers.CharField(max_length=60)


class RejectDocumentSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')
