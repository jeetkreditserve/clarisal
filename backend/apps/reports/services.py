from .catalog import REPORT_DATASETS
from .models import ReportDataset, ReportField, ReportFolder, ReportTemplate


def sync_report_catalog():
    for dataset_code, dataset_spec in REPORT_DATASETS.items():
        dataset, _ = ReportDataset.objects.update_or_create(
            code=dataset_code,
            defaults={
                'label': dataset_spec['label'],
                'description': dataset_spec.get('description', ''),
                'base_model': dataset_spec['base_model'],
                'default_date_field': dataset_spec.get('default_date_field', ''),
                'is_active': True,
            },
        )
        for field_spec in dataset_spec['fields']:
            ReportField.objects.update_or_create(
                dataset=dataset,
                code=field_spec['code'],
                defaults={
                    'label': field_spec['label'],
                    'path': field_spec['path'],
                    'data_type': field_spec['data_type'],
                    'is_filterable': field_spec.get('is_filterable', True),
                    'is_groupable': field_spec.get('is_groupable', True),
                    'is_summarizable': field_spec.get('is_summarizable', False),
                    'is_sensitive': field_spec.get('is_sensitive', False),
                    'permission_code': field_spec.get('permission_code', ''),
                    'is_active': True,
                },
            )


FIXED_REPORT_TEMPLATE_SEEDS = [
    {
        'name': 'Payroll Register',
        'dataset': 'payroll_runs',
        'columns': ['employee.employee_number', 'employee.full_name', 'payroll.gross_pay', 'payroll.net_pay'],
        'filters': [],
        'groupings': [{'field': 'payroll.period_year', 'position': 1}, {'field': 'payroll.period_month', 'position': 2}],
        'summaries': [{'field': 'payroll.net_pay', 'function': 'sum'}],
    },
    {
        'name': 'Headcount',
        'dataset': 'employees',
        'columns': ['department.name', 'office_location.name', 'employee.status'],
        'filters': [{'field': 'employee.status', 'operator': 'eq', 'value': 'ACTIVE'}],
        'groupings': [{'field': 'department.name', 'position': 1}],
        'summaries': [{'field': 'employee.id', 'function': 'count'}],
    },
]


def seed_system_report_templates(organisation, owner=None):
    default_folder, _ = ReportFolder.objects.get_or_create(
        organisation=organisation,
        name='System Reports',
        defaults={'description': 'Seeded reports equivalent to legacy fixed reports.', 'created_by': owner},
    )
    for seed in FIXED_REPORT_TEMPLATE_SEEDS:
        dataset = ReportDataset.objects.get(code=seed['dataset'])
        ReportTemplate.objects.update_or_create(
            organisation=organisation,
            name=seed['name'],
            defaults={
                'folder': default_folder,
                'dataset': dataset,
                'owner': owner,
                'status': ReportTemplate.Status.DEPLOYED,
                'columns': seed['columns'],
                'filters': seed['filters'],
                'groupings': seed['groupings'],
                'summaries': seed['summaries'],
                'is_system': True,
            },
        )
