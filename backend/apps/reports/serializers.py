from rest_framework import serializers

from .formulas import FormulaValidationError, validate_formula
from .models import ReportDataset, ReportExport, ReportField, ReportFolder, ReportRun, ReportTemplate


class ReportFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportField
        fields = ['id', 'code', 'label', 'data_type', 'is_filterable', 'is_groupable', 'is_summarizable', 'is_sensitive']


class ReportDatasetSerializer(serializers.ModelSerializer):
    fields = ReportFieldSerializer(many=True)

    class Meta:
        model = ReportDataset
        fields = ['id', 'code', 'label', 'description', 'default_date_field', 'fields']


class ReportFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportFolder
        fields = ['id', 'name', 'description', 'created_at', 'modified_at']


class ReportTemplateSerializer(serializers.ModelSerializer):
    dataset_code = serializers.CharField(source='dataset.code', read_only=True)
    dataset_label = serializers.CharField(source='dataset.label', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True, allow_null=True)

    class Meta:
        model = ReportTemplate
        fields = [
            'id',
            'dataset_code',
            'dataset_label',
            'folder',
            'folder_name',
            'name',
            'description',
            'status',
            'columns',
            'filters',
            'filter_logic',
            'groupings',
            'summaries',
            'formula_fields',
            'chart',
            'version',
            'is_system',
            'created_at',
            'modified_at',
        ]


class ReportTemplateWriteSerializer(serializers.Serializer):
    folder_id = serializers.UUIDField(required=False, allow_null=True)
    dataset_code = serializers.CharField(max_length=120)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    status = serializers.ChoiceField(choices=ReportTemplate.Status.choices, default=ReportTemplate.Status.DRAFT)
    columns = serializers.ListField(child=serializers.CharField(max_length=180), allow_empty=False)
    filters = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    filter_logic = serializers.CharField(required=False, allow_blank=True, default='')
    groupings = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    summaries = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    formula_fields = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    chart = serializers.DictField(required=False, default=dict)

    def validate_formula_fields(self, value):
        for formula in value:
            expression = formula.get('expression', '')
            if expression:
                try:
                    validate_formula(expression)
                except FormulaValidationError as exc:
                    raise serializers.ValidationError(str(exc)) from exc
        return value


class ReportRunSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    requested_by_email = serializers.EmailField(source='requested_by.email', read_only=True)
    exports = serializers.SerializerMethodField()

    class Meta:
        model = ReportRun
        fields = [
            'id',
            'template',
            'template_name',
            'requested_by_name',
            'requested_by_email',
            'status',
            'parameters',
            'row_count',
            'error_message',
            'started_at',
            'completed_at',
            'created_at',
            'exports',
        ]

    def get_exports(self, obj):
        exports = getattr(obj, '_prefetched_objects_cache', {}).get('exports')
        if exports is None:
            exports = obj.exports.all()
        return ReportExportSerializer(exports, many=True).data


class ReportExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportExport
        fields = ['id', 'file_format', 'file_name', 'content_type', 'byte_size', 'created_at']
