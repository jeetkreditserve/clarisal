import csv
import io

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from openpyxl import Workbook

from .models import ReportExport


def save_report_export(file_name, payload, content_type):
    return default_storage.save(f'reports/{file_name}', ContentFile(payload))


def build_export(run, result, file_format):
    if file_format == 'csv':
        content_type = 'text/csv'
        file_name = f'{run.template.name}.csv'
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=[column['code'] for column in result['columns']])
        writer.writeheader()
        writer.writerows(result['rows'])
        payload = buffer.getvalue().encode('utf-8')
    else:
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        file_name = f'{run.template.name}.xlsx'
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'Report'
        worksheet.append([column['label'] for column in result['columns']])
        for row in result['rows']:
            worksheet.append([row.get(column['code'], '') for column in result['columns']])
        output = io.BytesIO()
        workbook.save(output)
        payload = output.getvalue()

    storage_key = save_report_export(file_name, payload, content_type)
    return ReportExport.objects.create(
        run=run,
        file_format=file_format,
        storage_key=storage_key,
        file_name=file_name,
        content_type=content_type,
        byte_size=len(payload),
    )
