from rest_framework import serializers

from .models import Document, DocumentType


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'document_type',
            'file_name',
            'file_size',
            'mime_type',
            'status',
            'metadata',
            'uploaded_by_email',
            'reviewed_by_email',
            'reviewed_at',
            'created_at',
        ]


class UploadDocumentSerializer(serializers.Serializer):
    file = serializers.FileField()
    document_type = serializers.ChoiceField(choices=DocumentType.choices)
    metadata = serializers.JSONField(required=False)


class RejectDocumentSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')
