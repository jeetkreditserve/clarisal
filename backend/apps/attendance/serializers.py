from rest_framework import serializers

from .models import AttendanceImportJob


class AttendanceImportJobSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    normalized_file_available = serializers.SerializerMethodField()
    error_preview = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceImportJob
        fields = [
            'id',
            'mode',
            'status',
            'original_filename',
            'uploaded_by_email',
            'total_rows',
            'valid_rows',
            'error_rows',
            'posted_rows',
            'normalized_file_available',
            'error_preview',
            'created_at',
            'modified_at',
        ]

    def get_normalized_file_available(self, obj):
        return obj.mode == 'PUNCH_SHEET' and obj.valid_rows > 0

    def get_error_preview(self, obj):
        rows = obj.rows.filter(status='ERROR').order_by('row_number')[:5]
        return [
            {
                'row_number': row.row_number,
                'employee_code': row.employee_code,
                'message': row.error_message,
            }
            for row in rows
        ]

