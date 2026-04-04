from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from apps.common.security import decrypt_value

PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')


def decimal_to_string(value: Decimal | str | int | float | None, *, places: str = '0.00') -> str:
    if value in (None, ''):
        return Decimal(places).quantize(Decimal(places)).to_eng_string()
    return Decimal(str(value)).quantize(Decimal(places)).to_eng_string()


def decimal_to_rupee_int(value: Decimal | str | int | float | None) -> str:
    if value in (None, ''):
        return '0'
    return str(int(Decimal(str(value)).quantize(Decimal('1'))))


def build_csv(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def stable_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def fiscal_year_bounds(fiscal_year: str) -> tuple[date, date]:
    start_year_str, end_year_str = fiscal_year.split('-', 1)
    start_year = int(start_year_str)
    end_year = int(end_year_str)
    return date(start_year, 4, 1), date(end_year, 3, 31)


def quarter_months(fiscal_year: str, quarter: str) -> list[tuple[int, int]]:
    start_year_str, end_year_str = fiscal_year.split('-', 1)
    start_year = int(start_year_str)
    end_year = int(end_year_str)
    quarter_map = {
        'Q1': [(start_year, 4), (start_year, 5), (start_year, 6)],
        'Q2': [(start_year, 7), (start_year, 8), (start_year, 9)],
        'Q3': [(start_year, 10), (start_year, 11), (start_year, 12)],
        'Q4': [(end_year, 1), (end_year, 2), (end_year, 3)],
    }
    return quarter_map[quarter]


def get_employee_identifier(employee, *, id_type: str) -> str:
    record = (
        employee.government_ids.filter(id_type=id_type)
        .order_by('-modified_at', '-created_at')
        .first()
    )
    if record is None:
        return ''

    decrypted_value = decrypt_value(record.identifier_encrypted)
    if decrypted_value:
        return decrypted_value

    fallback_value = (record.masked_identifier or '').strip().upper()
    if id_type == 'PAN' and PAN_PATTERN.fullmatch(fallback_value):
        return fallback_value
    return ''


@dataclass(slots=True)
class FilingGenerationResult:
    artifact_format: str
    content_type: str
    file_name: str
    structured_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    artifact_text: str = ''
    artifact_binary: bytes = b''

    @property
    def is_blocked(self) -> bool:
        return bool(self.validation_errors)

    def payload_bytes(self) -> bytes:
        if self.artifact_binary:
            return self.artifact_binary
        return self.artifact_text.encode('utf-8')
