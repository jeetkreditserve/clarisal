from django.apps import apps
from django.db.models import Avg, Count, Max, Min, Q, Sum

from apps.access_control.services import has_permission, scope_employee_queryset

SUMMARY_FUNCTIONS = {
    'count': Count,
    'sum': Sum,
    'avg': Avg,
    'min': Min,
    'max': Max,
}

FILTER_LOOKUPS = {
    'eq': '',
    'neq': '',
    'contains': '__icontains',
    'gte': '__gte',
    'lte': '__lte',
    'in': '__in',
    'isnull': '__isnull',
}


class ReportValidationError(ValueError):
    pass


def _model_for_dataset(dataset):
    app_label, model_name = dataset.base_model.split('.', 1)
    return apps.get_model(app_label, model_name)


def _field_map(dataset):
    return {field.code: field for field in dataset.fields.filter(is_active=True)}


def _validate_field(field_map, field_code):
    field = field_map.get(field_code)
    if field is None:
        raise ReportValidationError(f'Unknown report field: {field_code}')
    return field


def _filter_q(field_map, filter_payload):
    field = _validate_field(field_map, filter_payload['field'])
    if not field.is_filterable:
        raise ReportValidationError(f'Field is not filterable: {field.code}')
    operator = filter_payload['operator']
    if operator not in FILTER_LOOKUPS:
        raise ReportValidationError(f'Unsupported filter operator: {operator}')
    value = filter_payload.get('value')
    if operator == 'neq':
        return ~Q(**{field.path: value})
    return Q(**{f'{field.path}{FILTER_LOOKUPS[operator]}': value})


def _organisation_filter(queryset, model, organisation):
    if hasattr(model, 'organisation'):
        return queryset.filter(organisation=organisation)
    if hasattr(model, 'employee'):
        return queryset.filter(employee__organisation=organisation)
    if hasattr(model, 'pay_run'):
        return queryset.filter(pay_run__organisation=organisation)
    return queryset


def build_report_queryset(template, user, organisation, parameters=None):
    parameters = parameters or {}
    dataset = template.dataset
    model = _model_for_dataset(dataset)
    queryset = _organisation_filter(model.objects.all(), model, organisation)

    if dataset.code == 'employees':
        queryset = scope_employee_queryset(queryset, user, organisation=organisation)
    elif hasattr(model, 'employee'):
        scoped_employee_ids = scope_employee_queryset(
            apps.get_model('employees', 'Employee').objects.all(),
            user,
            organisation=organisation,
        ).values_list('id', flat=True)
        queryset = queryset.filter(employee_id__in=scoped_employee_ids)

    field_map = _field_map(dataset)
    if dataset.code == 'payroll_runs' and not has_permission(user, 'org.payroll.read', organisation=organisation):
        raise ReportValidationError(f'Missing permission for dataset: {dataset.code}')

    for field_code in template.columns:
        field = _validate_field(field_map, field_code)
        if field.permission_code and not has_permission(user, field.permission_code, organisation):
            raise ReportValidationError(f'Missing permission for field: {field.code}')

    combined_q = Q()
    for filter_payload in template.filters:
        combined_q &= _filter_q(field_map, filter_payload)
    return queryset.filter(combined_q), field_map


def _value_paths(fields):
    paths = {field.path for field in fields}
    for field in fields:
        if field.code == 'employee.full_name':
            if field.path.startswith('employee__'):
                paths.update({'employee__user__first_name', 'employee__user__last_name', 'employee__user__email'})
            else:
                paths.update({'user__first_name', 'user__last_name', 'user__email'})
    return list(paths)


def _row_value(item, field):
    if field.code == 'employee.full_name':
        if field.path.startswith('employee__'):
            first_name = item.get('employee__user__first_name', '')
            last_name = item.get('employee__user__last_name', '')
            email = item.get('employee__user__email', '')
        else:
            first_name = item.get('user__first_name', '')
            last_name = item.get('user__last_name', '')
            email = item.get('user__email', '')
        full_name = f'{first_name} {last_name}'.strip()
        return full_name or email
    return item.get(field.path)


def preview_report(template, user, organisation, limit=100, parameters=None):
    queryset, field_map = build_report_queryset(template, user, organisation, parameters)
    selected_fields = [_validate_field(field_map, code) for code in template.columns]
    rows = []
    for item in queryset.values(*_value_paths(selected_fields))[:limit]:
        row = {}
        for field in selected_fields:
            row[field.code] = _row_value(item, field)
        rows.append(row)
    return {
        'columns': [{'code': field.code, 'label': field.label, 'data_type': field.data_type} for field in selected_fields],
        'rows': rows,
        'truncated': queryset.count() > limit,
    }
