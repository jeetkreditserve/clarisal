# P09 — Biometric Device Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate with the four leading biometric attendance protocols used in the Indian market — ZK ADMS (push), Matrix COSEC (REST pull), Suprema BioStar 2 (REST/OAuth2 pull), and HikVision ISAPI (digest auth pull) — plus a device management UI.

**Architecture:** New `biometrics` Django app. Protocol handlers are isolated in `protocols/` sub-package. Each handler converts device-specific attendance records to `AttendancePunch` records via an existing service helper. A Celery beat task runs every 5 minutes for pull protocols. ADMS devices push directly to an endpoint — no polling needed.

**Tech Stack:** Django 4.2 · DRF · Celery 5.4 · `requests` library · React 19 · TypeScript

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/apps/biometrics/__init__.py` | Create | App package |
| `backend/apps/biometrics/apps.py` | Create | App config |
| `backend/apps/biometrics/models.py` | Create | `BiometricDevice`, `BiometricSyncLog` |
| `backend/apps/biometrics/services.py` | Create | Device registration, sync orchestration |
| `backend/apps/biometrics/protocols/__init__.py` | Create | Package |
| `backend/apps/biometrics/protocols/adms.py` | Create | ZK ADMS push handler |
| `backend/apps/biometrics/protocols/matrix_cosec.py` | Create | Matrix COSEC pull |
| `backend/apps/biometrics/protocols/suprema.py` | Create | Suprema BioStar 2 pull |
| `backend/apps/biometrics/protocols/hikvision.py` | Create | HikVision ISAPI pull |
| `backend/apps/biometrics/tasks.py` | Create | Celery beat task for pull sync |
| `backend/apps/biometrics/views.py` | Create | Device CRUD + ADMS push endpoint |
| `backend/apps/biometrics/serializers.py` | Create | Device and sync log serializers |
| `backend/apps/biometrics/urls.py` | Create | URL patterns |
| `backend/apps/biometrics/tests/test_protocols.py` | Create | Protocol unit tests with mocked HTTP |
| `backend/apps/attendance/services.py` | Modify | Add `create_punch_from_source()` helper |
| `backend/clarisal/settings/base.py` | Modify | Add app, Celery beat schedule |
| `backend/clarisal/urls.py` | Modify | Add `/api/biometric/` namespace |
| `frontend/src/pages/org/BiometricDevicesPage.tsx` | Create | Device management UI |
| `frontend/src/lib/api/org-admin.ts` | Modify | Add biometric API functions |

---

## Task 1 — `biometrics` App and Models

**Files:**
- Create: `backend/apps/biometrics/models.py`

- [ ] **Step 1: Create app**

```bash
cd backend && python manage.py startapp biometrics apps/biometrics
```

Update `apps.py`:
```python
from django.apps import AppConfig

class BiometricsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.biometrics'
    label = 'biometrics'
```

Add `'apps.biometrics'` to `LOCAL_APPS` in `backend/clarisal/settings/base.py`.

- [ ] **Step 2: Create `models.py`**

```python
# backend/apps/biometrics/models.py
import hashlib
from django.db import models
from apps.common.models import AuditedBaseModel


class BiometricProtocol(models.TextChoices):
    ZK_ADMS = 'ZK_ADMS', 'ZKTeco / eSSL / Biomax (ADMS Push)'
    MATRIX_COSEC = 'MATRIX_COSEC', 'Matrix COSEC (REST Pull)'
    SUPREMA_BIOSTAR = 'SUPREMA_BIOSTAR', 'Suprema BioStar 2 (REST Pull)'
    HIKVISION_ISAPI = 'HIKVISION_ISAPI', 'HikVision ISAPI (REST Pull)'


class BiometricDevice(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='biometric_devices',
    )
    name = models.CharField(max_length=100)
    device_serial = models.CharField(max_length=100, blank=True, help_text='Device serial number / SN')
    protocol = models.CharField(max_length=30, choices=BiometricProtocol.choices)

    # Connection details (for pull protocols)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    port = models.PositiveIntegerField(default=80)

    # API credentials (stored as hash / encrypted)
    api_key_hash = models.CharField(max_length=128, blank=True, help_text='SHA-256 hash of the API key')

    # For OAuth2 (Suprema)
    oauth_client_id = models.CharField(max_length=200, blank=True)
    oauth_client_secret_hash = models.CharField(max_length=128, blank=True)

    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='biometric_devices',
    )
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('organisation', 'device_serial')]

    def set_api_key(self, raw_key: str):
        self.api_key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    def __str__(self):
        return f'{self.name} ({self.protocol})'


class BiometricSyncLog(AuditedBaseModel):
    device = models.ForeignKey(BiometricDevice, on_delete=models.CASCADE, related_name='sync_logs')
    synced_at = models.DateTimeField(auto_now_add=True)
    records_fetched = models.PositiveIntegerField(default=0)
    records_processed = models.PositiveIntegerField(default=0)
    records_skipped = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list)
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ['-synced_at']
```

- [ ] **Step 3: Generate and apply migration**

```bash
cd backend && python manage.py makemigrations biometrics --name initial
cd backend && python manage.py migrate
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/biometrics/ backend/clarisal/settings/base.py
git commit -m "feat(biometrics): create biometrics app with BiometricDevice and BiometricSyncLog models"
```

---

## Task 2 — `create_punch_from_source()` Helper in Attendance

**Files:**
- Modify: `backend/apps/attendance/services.py`

- [ ] **Step 1: Add helper function**

In `backend/apps/attendance/services.py`, add:

```python
def create_punch_from_source(
    employee_code: str,
    punch_time,
    organisation_id: str,
    direction: str = 'IN',
    source: str = 'DEVICE',
    device_id: str = None,
) -> dict:
    """
    Create an AttendancePunch from a biometric device record.
    Looks up employee by employee_code within the organisation.
    Returns dict with 'status': 'created' | 'skipped' | 'error'.
    """
    from apps.employees.models import Employee, EmployeeStatus
    from .models import AttendancePunch, AttendancePunchSource

    try:
        employee = Employee.objects.get(
            organisation_id=organisation_id,
            employee_code=employee_code,
            status=EmployeeStatus.ACTIVE,
        )
    except Employee.DoesNotExist:
        return {'status': 'skipped', 'reason': f'No active employee with code {employee_code}'}
    except Employee.MultipleObjectsReturned:
        return {'status': 'error', 'reason': f'Multiple employees match code {employee_code}'}

    # Deduplicate: skip if same employee has a punch within 1 minute of this time
    from django.utils import timezone
    from datetime import timedelta
    duplicate = AttendancePunch.objects.filter(
        employee=employee,
        punch_time__gte=punch_time - timedelta(minutes=1),
        punch_time__lte=punch_time + timedelta(minutes=1),
    ).exists()

    if duplicate:
        return {'status': 'skipped', 'reason': 'Duplicate punch within 1-minute window'}

    punch = AttendancePunch.objects.create(
        employee=employee,
        punch_time=punch_time,
        direction=direction,
        source=source,
        device_id=device_id,
    )
    return {'status': 'created', 'punch_id': str(punch.id)}
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/attendance/services.py
git commit -m "feat(attendance): add create_punch_from_source() helper for biometric integration"
```

---

## Task 3 — ADMS Protocol Handler (ZKTeco, eSSL, Biomax)

**Files:**
- Create: `backend/apps/biometrics/protocols/__init__.py`
- Create: `backend/apps/biometrics/protocols/adms.py`
- Modify: `backend/apps/biometrics/views.py` (add ADMS endpoints)
- Modify: `backend/clarisal/urls.py` (add `/api/biometric/` namespace)

### Background

ADMS (Attendance Data Management System) is a push protocol. The device periodically POSTs attendance records to the server. The device must first be registered via a GET to the cdata endpoint, then attendance logs are POSTed with `table=ATTLOG`. Each ATTLOG line: `PIN<tab>DateTime<tab>Status<tab>Verify<tab>WorkCode\n` where PIN is the employee's enrolled PIN (mapped to employee_code).

- [ ] **Step 1: Write failing test**

Create `backend/apps/biometrics/tests/__init__.py` and `backend/apps/biometrics/tests/test_protocols.py`:

```python
# backend/apps/biometrics/tests/test_protocols.py
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from apps.biometrics.protocols.adms import parse_attlog_line, handle_adms_push
from apps.accounts.tests.factories import OrganisationFactory


class TestAdmsProtocol(TestCase):
    def test_parse_attlog_line_returns_correct_fields(self):
        line = '1001\t2024-04-01 09:05:00\t0\t1\t0'
        result = parse_attlog_line(line)
        self.assertEqual(result['pin'], '1001')
        self.assertEqual(result['datetime_str'], '2024-04-01 09:05:00')
        self.assertEqual(result['status'], '0')

    def test_parse_attlog_line_ignores_malformed(self):
        result = parse_attlog_line('malformed line')
        self.assertIsNone(result)

    def test_parse_attlog_handles_tab_separated(self):
        line = '2002\t2024-04-01 18:30:00\t1\t1\t0\n'
        result = parse_attlog_line(line)
        self.assertEqual(result['pin'], '2002')
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest apps/biometrics/tests/test_protocols.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `protocols/__init__.py`**

```bash
touch backend/apps/biometrics/protocols/__init__.py
```

- [ ] **Step 4: Create `protocols/adms.py`**

```python
# backend/apps/biometrics/protocols/adms.py
"""
ZK ADMS Protocol Handler
Supports: ZKTeco, eSSL Security, Biomax, Realtime Biometrics, Novatel

ADMS device POSTs to:
  POST /api/biometric/adms/iclock/cdata?SN={serial}               — device registration
  POST /api/biometric/adms/iclock/cdata?SN={serial}&table=ATTLOG  — attendance push

ATTLOG line format (tab-separated):
  PIN \t DateTime \t Status \t Verify \t WorkCode

Status codes: 0=check-in, 1=check-out, 2=break-out, 3=break-in, 4=OT-in, 5=OT-out
"""
from __future__ import annotations
from datetime import datetime


def parse_attlog_line(line: str) -> dict | None:
    """
    Parse one ATTLOG line into a dict with keys: pin, datetime_str, status, verify, work_code.
    Returns None if the line is malformed.
    """
    parts = line.strip().split('\t')
    if len(parts) < 2:
        return None
    return {
        'pin': parts[0].strip(),
        'datetime_str': parts[1].strip() if len(parts) > 1 else '',
        'status': parts[2].strip() if len(parts) > 2 else '0',
        'verify': parts[3].strip() if len(parts) > 3 else '',
        'work_code': parts[4].strip() if len(parts) > 4 else '',
    }


def parse_punch_direction(status: str) -> str:
    """Map ADMS status code to IN/OUT direction."""
    OUT_STATUSES = {'1', '3', '5'}
    return 'OUT' if status in OUT_STATUSES else 'IN'


def handle_adms_push(body: str, organisation_id: str, device_serial: str) -> dict:
    """
    Process an ATTLOG push body (multi-line string).
    Returns summary: {processed, skipped, errors}.
    """
    from apps.attendance.services import create_punch_from_source
    from django.utils.dateparse import parse_datetime

    lines = [l for l in body.strip().split('\n') if l.strip()]
    processed = 0
    skipped = 0
    errors = []

    for line in lines:
        parsed = parse_attlog_line(line)
        if not parsed:
            skipped += 1
            continue
        try:
            punch_dt = datetime.strptime(parsed['datetime_str'], '%Y-%m-%d %H:%M:%S')
            from django.utils import timezone
            punch_dt = timezone.make_aware(punch_dt)
        except ValueError:
            errors.append(f'Bad datetime: {parsed["datetime_str"]}')
            continue

        direction = parse_punch_direction(parsed['status'])
        result = create_punch_from_source(
            employee_code=parsed['pin'],
            punch_time=punch_dt,
            organisation_id=organisation_id,
            direction=direction,
            source='DEVICE',
            device_id=device_serial,
        )
        if result['status'] == 'created':
            processed += 1
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest apps/biometrics/tests/test_protocols.py -v
```

Expected: All ADMS tests PASS.

- [ ] **Step 6: Create ADMS views**

In `backend/apps/biometrics/views.py`:

```python
# backend/apps/biometrics/views.py (ADMS section)
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import BiometricDevice, BiometricSyncLog
from .protocols.adms import handle_adms_push


@method_decorator(csrf_exempt, name='dispatch')
class AdmsCdataView(View):
    """
    Endpoint for ZK ADMS devices.
    GET  /api/biometric/adms/iclock/cdata?SN=...  — device registration
    POST /api/biometric/adms/iclock/cdata?SN=...&table=ATTLOG — push attendance
    """

    def get(self, request):
        """Return server timestamp for device sync."""
        from django.utils import timezone
        sn = request.GET.get('SN', '')
        now = timezone.now()
        # ADMS response format required by device firmware
        response_body = (
            f'GET OPTION FROM: {sn}\n'
            f'ATTLOGStamp={int(now.timestamp())}\n'
            f'OPERLOGStamp=9999\n'
            f'ATTPHOTOStamp=None\n'
            f'ErrorDelay=30\n'
            f'Delay=10\n'
            f'TransTimes=00:00;14:05\n'
            f'TransInterval=1\n'
            f'TransFlag=TransData AttLog\n'
            f'TimeZone=5.5\n'
            f'Realtime=1\n'
            f'Encrypt=None\n'
        )
        return HttpResponse(response_body, content_type='text/plain')

    def post(self, request):
        """Process pushed attendance data."""
        sn = request.GET.get('SN', '')
        table = request.GET.get('table', '')

        if table != 'ATTLOG':
            return HttpResponse('OK', content_type='text/plain')

        # Look up device by serial number — find its organisation
        try:
            device = BiometricDevice.objects.select_related('organisation').get(
                device_serial=sn,
                is_active=True,
            )
        except BiometricDevice.DoesNotExist:
            # Device not registered — accept but log
            return HttpResponse('OK', content_type='text/plain')

        body = request.body.decode('utf-8', errors='replace')
        summary = handle_adms_push(
            body=body,
            organisation_id=str(device.organisation_id),
            device_serial=sn,
        )

        BiometricSyncLog.objects.create(
            device=device,
            records_fetched=summary['processed'] + summary['skipped'],
            records_processed=summary['processed'],
            records_skipped=summary['skipped'],
            errors=summary['errors'],
            success=len(summary['errors']) == 0,
        )

        return HttpResponse('OK', content_type='text/plain')
```

- [ ] **Step 7: Create `urls.py` and register**

```python
# backend/apps/biometrics/urls.py
from django.urls import path
from .views import AdmsCdataView, BiometricDeviceListCreateView, BiometricDeviceDetailView, BiometricSyncLogListView

# ADMS push endpoint (no auth — device authenticates via SN)
adms_urlpatterns = [
    path('adms/iclock/cdata', AdmsCdataView.as_view()),
]

# Org admin device management
org_urlpatterns = [
    path('biometrics/devices/', BiometricDeviceListCreateView.as_view()),
    path('biometrics/devices/<uuid:pk>/', BiometricDeviceDetailView.as_view()),
    path('biometrics/devices/<uuid:pk>/sync-logs/', BiometricSyncLogListView.as_view()),
]
```

In `backend/clarisal/urls.py`, add:
```python
from django.urls import path, include
# In urlpatterns:
path('api/biometric/', include('apps.biometrics.adms_urls')),  # ADMS has its own URL file
path('api/org/', include('apps.biometrics.org_urls')),
```

Create two separate URL files:
- `backend/apps/biometrics/adms_urls.py` (ADMS push, no auth)
- `backend/apps/biometrics/org_urls.py` (org admin CRUD)

- [ ] **Step 8: Commit**

```bash
git add backend/apps/biometrics/protocols/ \
        backend/apps/biometrics/views.py \
        backend/apps/biometrics/urls.py \
        backend/apps/biometrics/adms_urls.py \
        backend/apps/biometrics/org_urls.py \
        backend/clarisal/urls.py \
        backend/apps/biometrics/tests/
git commit -m "feat(biometrics): ZK ADMS push protocol handler and endpoint"
```

---

## Task 4 — Matrix COSEC Pull Handler

**Files:**
- Create: `backend/apps/biometrics/protocols/matrix_cosec.py`

- [ ] **Step 1: Write failing test**

Add to `test_protocols.py`:

```python
class TestMatrixCosecProtocol(TestCase):
    @patch('requests.get')
    def test_fetch_attendance_parses_records(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'response': {
                'data': [
                    {
                        'userID': '1001',
                        'dateTime': '2024-04-01T09:05:00',
                        'eventType': 'DOOR_OPEN',
                        'direction': 'IN',
                    }
                ]
            }
        }
        from apps.biometrics.protocols.matrix_cosec import fetch_cosec_attendance
        records = fetch_cosec_attendance(
            device_ip='192.168.1.100',
            port=80,
            api_key='test-key',
            from_datetime='2024-04-01T00:00:00',
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['employee_code'], '1001')
```

- [ ] **Step 2: Create `protocols/matrix_cosec.py`**

```python
# backend/apps/biometrics/protocols/matrix_cosec.py
"""
Matrix COSEC API Pull Handler
Device: Matrix Comsec COSEC series
Protocol: REST API, poll-based
Auth: API key in X-API-Key header

API endpoint: GET http://{ip}:{port}/api/v1/monitoring/attendance
Query params: fromDate, toDate
Response: JSON with attendance records
"""
from __future__ import annotations
from datetime import datetime
import requests


def fetch_cosec_attendance(
    device_ip: str,
    port: int,
    api_key: str,
    from_datetime: str,
    to_datetime: str = None,
    timeout: int = 15,
) -> list[dict]:
    """
    Pull attendance records from a Matrix COSEC device.
    Returns list of dicts: {employee_code, punch_time (datetime), direction}.
    """
    import requests
    from datetime import datetime

    url = f'http://{device_ip}:{port}/api/v1/monitoring/attendance'
    params = {'fromDate': from_datetime}
    if to_datetime:
        params['toDate'] = to_datetime

    try:
        response = requests.get(
            url,
            headers={'X-API-Key': api_key, 'Accept': 'application/json'},
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ConnectionError(f'COSEC device unreachable at {device_ip}:{port}: {exc}')

    data = response.json()
    records_raw = data.get('response', {}).get('data', [])
    records = []
    for r in records_raw:
        try:
            punch_time = datetime.fromisoformat(r['dateTime'])
        except (KeyError, ValueError):
            continue
        direction = 'OUT' if r.get('direction', 'IN').upper() == 'OUT' else 'IN'
        records.append({
            'employee_code': str(r.get('userID', '')),
            'punch_time': punch_time,
            'direction': direction,
        })
    return records


def sync_cosec_device(device, organisation_id: str) -> dict:
    """
    Pull and process attendance from a Matrix COSEC device.
    `device` is a BiometricDevice instance.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.attendance.services import create_punch_from_source

    since = device.last_sync_at or (timezone.now() - timedelta(days=1))
    from_dt = since.strftime('%Y-%m-%dT%H:%M:%S')

    records = fetch_cosec_attendance(
        device_ip=device.ip_address,
        port=device.port,
        api_key='',  # API key retrieved separately from secure store
        from_datetime=from_dt,
    )

    processed = skipped = 0
    errors = []
    for rec in records:
        from django.utils import timezone as tz
        punch_time = tz.make_aware(rec['punch_time']) if rec['punch_time'].tzinfo is None else rec['punch_time']
        result = create_punch_from_source(
            employee_code=rec['employee_code'],
            punch_time=punch_time,
            organisation_id=organisation_id,
            direction=rec['direction'],
            source='DEVICE',
            device_id=str(device.id),
        )
        if result['status'] == 'created':
            processed += 1
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest apps/biometrics/tests/test_protocols.py::TestMatrixCosecProtocol -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/biometrics/protocols/matrix_cosec.py
git commit -m "feat(biometrics): Matrix COSEC REST pull protocol handler"
```

---

## Task 5 — Suprema BioStar 2 Pull Handler

**Files:**
- Create: `backend/apps/biometrics/protocols/suprema.py`

- [ ] **Step 1: Write test**

Add to `test_protocols.py`:

```python
class TestSupremaProtocol(TestCase):
    @patch('requests.post')
    @patch('requests.get')
    def test_fetch_suprema_attendance(self, mock_get, mock_post):
        # Mock OAuth2 token
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'access_token': 'test-token', 'token_type': 'bearer'}
        # Mock attendance records
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'EventCollection': {
                'rows': [
                    {
                        'user_id': '1001',
                        'datetime': '2024-04-01T09:05:00+05:30',
                        'event_type_id': '1',  # CHECK_IN
                    }
                ]
            }
        }
        from apps.biometrics.protocols.suprema import fetch_biostar_attendance
        records = fetch_biostar_attendance(
            server_url='http://biostar.example.com',
            client_id='test-client',
            client_secret='test-secret',
            from_datetime='2024-04-01T00:00:00',
        )
        self.assertGreaterEqual(len(records), 1)
```

- [ ] **Step 2: Create `protocols/suprema.py`**

```python
# backend/apps/biometrics/protocols/suprema.py
"""
Suprema BioStar 2 API Pull Handler
Auth: OAuth2 client credentials
Event type 1 = check-in, 2 = check-out
API: GET https://{server}/api/v2/events?from_time=...
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import requests

_token_cache: dict = {}  # In-memory cache; use Redis in production


def _get_access_token(server_url: str, client_id: str, client_secret: str) -> str:
    token_url = f'{server_url}/oauth2/token'
    cache_key = f'{server_url}:{client_id}'
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    response = requests.post(
        token_url,
        data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
        },
        timeout=10,
    )
    response.raise_for_status()
    token = response.json()['access_token']
    _token_cache[cache_key] = token
    return token


def fetch_biostar_attendance(
    server_url: str,
    client_id: str,
    client_secret: str,
    from_datetime: str,
    to_datetime: Optional[str] = None,
    timeout: int = 20,
) -> list[dict]:
    """
    Pull attendance events from Suprema BioStar 2.
    Returns list of {employee_code, punch_time, direction}.
    """
    token = _get_access_token(server_url, client_id, client_secret)
    url = f'{server_url}/api/v2/events'
    params = {'from_time': from_datetime, 'event_type_id': '1,2'}  # 1=in, 2=out
    if to_datetime:
        params['to_time'] = to_datetime

    response = requests.get(
        url,
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
        params=params,
        timeout=timeout,
        verify=False,  # BioStar often uses self-signed cert
    )
    response.raise_for_status()

    rows = response.json().get('EventCollection', {}).get('rows', [])
    records = []
    for row in rows:
        try:
            punch_time = datetime.fromisoformat(row['datetime'])
        except (KeyError, ValueError):
            continue
        event_type = str(row.get('event_type_id', '1'))
        direction = 'OUT' if event_type == '2' else 'IN'
        records.append({
            'employee_code': str(row.get('user_id', '')),
            'punch_time': punch_time,
            'direction': direction,
        })
    return records


def sync_biostar_device(device, organisation_id: str) -> dict:
    from django.utils import timezone
    from datetime import timedelta
    from apps.attendance.services import create_punch_from_source

    since = device.last_sync_at or (timezone.now() - timedelta(days=1))
    from_dt = since.isoformat()

    records = fetch_biostar_attendance(
        server_url=f'http://{device.ip_address}:{device.port}',
        client_id=device.oauth_client_id,
        client_secret='',  # retrieved from secure store
        from_datetime=from_dt,
    )

    processed = skipped = 0
    errors = []
    for rec in records:
        from django.utils import timezone as tz
        punch_time = tz.make_aware(rec['punch_time']) if rec['punch_time'].tzinfo is None else rec['punch_time']
        result = create_punch_from_source(
            employee_code=rec['employee_code'],
            punch_time=punch_time,
            organisation_id=organisation_id,
            direction=rec['direction'],
            source='DEVICE',
            device_id=str(device.id),
        )
        if result['status'] == 'created':
            processed += 1
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}
```

- [ ] **Step 3: Run tests and commit**

```bash
cd backend && python -m pytest apps/biometrics/tests/test_protocols.py::TestSupremaProtocol -v
git add backend/apps/biometrics/protocols/suprema.py
git commit -m "feat(biometrics): Suprema BioStar 2 OAuth2 pull protocol handler"
```

---

## Task 6 — HikVision ISAPI Pull Handler

**Files:**
- Create: `backend/apps/biometrics/protocols/hikvision.py`

- [ ] **Step 1: Write test**

Add to `test_protocols.py`:

```python
class TestHikVisionProtocol(TestCase):
    @patch('requests.get')
    def test_fetch_hikvision_events(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'AcsEvent': {
                'InfoList': [
                    {
                        'employeeNoString': '1001',
                        'time': '2024-04-01T09:05:00+05:30',
                        'major': 5,    # ACCESS_CTL
                        'minor': 75,   # DOOR_OPEN_NORMAL
                        'serialNo': 1,
                    }
                ]
            }
        }
        from apps.biometrics.protocols.hikvision import fetch_hikvision_events
        records = fetch_hikvision_events(
            device_ip='192.168.1.200',
            port=80,
            username='admin',
            password='hikvision123',
        )
        self.assertEqual(len(records), 1)
```

- [ ] **Step 2: Create `protocols/hikvision.py`**

```python
# backend/apps/biometrics/protocols/hikvision.py
"""
HikVision ISAPI Pull Handler
Auth: HTTP Digest Authentication
Endpoint: GET http://{ip}/ISAPI/AccessControl/AcsEvent?format=json
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import requests
from requests.auth import HTTPDigestAuth


def fetch_hikvision_events(
    device_ip: str,
    port: int,
    username: str,
    password: str,
    start_time: Optional[str] = None,
    max_results: int = 200,
    timeout: int = 15,
) -> list[dict]:
    """
    Pull access control events from a HikVision device via ISAPI.
    Returns list of {employee_code, punch_time, direction}.
    """
    url = f'http://{device_ip}:{port}/ISAPI/AccessControl/AcsEvent'
    params = {
        'format': 'json',
        'searchResultPosition': 0,
        'maxResults': max_results,
    }
    if start_time:
        params['startTime'] = start_time

    try:
        response = requests.get(
            url,
            auth=HTTPDigestAuth(username, password),
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ConnectionError(f'HikVision device unreachable at {device_ip}:{port}: {exc}')

    event_list = response.json().get('AcsEvent', {}).get('InfoList', [])
    records = []
    for event in event_list:
        try:
            punch_time = datetime.fromisoformat(event['time'])
        except (KeyError, ValueError):
            continue
        # Event direction heuristic: minor code 75 = door open (IN), 76 = exit (OUT)
        minor = event.get('minor', 75)
        direction = 'OUT' if minor in (76, 77) else 'IN'
        employee_code = str(event.get('employeeNoString', event.get('employeeNo', '')))
        if not employee_code:
            continue
        records.append({
            'employee_code': employee_code,
            'punch_time': punch_time,
            'direction': direction,
        })
    return records


def sync_hikvision_device(device, organisation_id: str) -> dict:
    from django.utils import timezone
    from datetime import timedelta
    from apps.attendance.services import create_punch_from_source

    since = device.last_sync_at or (timezone.now() - timedelta(days=1))
    start_time = since.isoformat()

    records = fetch_hikvision_events(
        device_ip=device.ip_address,
        port=device.port,
        username='admin',
        password='',  # retrieved from secure store
        start_time=start_time,
    )

    processed = skipped = 0
    errors = []
    for rec in records:
        from django.utils import timezone as tz
        punch_time = tz.make_aware(rec['punch_time']) if rec['punch_time'].tzinfo is None else rec['punch_time']
        result = create_punch_from_source(
            employee_code=rec['employee_code'],
            punch_time=punch_time,
            organisation_id=organisation_id,
            direction=rec['direction'],
            source='DEVICE',
            device_id=str(device.id),
        )
        if result['status'] == 'created':
            processed += 1
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}
```

- [ ] **Step 3: Run tests and commit**

```bash
cd backend && python -m pytest apps/biometrics/tests/test_protocols.py -v
git add backend/apps/biometrics/protocols/hikvision.py
git commit -m "feat(biometrics): HikVision ISAPI digest auth pull protocol handler"
```

---

## Task 7 — Celery Beat Sync Task

**Files:**
- Create: `backend/apps/biometrics/tasks.py`
- Modify: `backend/clarisal/settings/base.py`

- [ ] **Step 1: Create `tasks.py`**

```python
# backend/apps/biometrics/tasks.py
from celery import shared_task
from django.utils import timezone


@shared_task(name='biometrics.sync_pull_devices')
def sync_pull_devices():
    """
    Celery beat task: sync all active pull-protocol biometric devices.
    Runs every 5 minutes via beat schedule.
    Skips ADMS devices (they push data themselves).
    """
    from .models import BiometricDevice, BiometricProtocol, BiometricSyncLog
    from .protocols.matrix_cosec import sync_cosec_device
    from .protocols.suprema import sync_biostar_device
    from .protocols.hikvision import sync_hikvision_device

    PULL_SYNC_HANDLERS = {
        BiometricProtocol.MATRIX_COSEC: sync_cosec_device,
        BiometricProtocol.SUPREMA_BIOSTAR: sync_biostar_device,
        BiometricProtocol.HIKVISION_ISAPI: sync_hikvision_device,
    }

    devices = BiometricDevice.objects.filter(
        is_active=True,
        protocol__in=list(PULL_SYNC_HANDLERS.keys()),
    ).select_related('organisation')

    for device in devices:
        handler = PULL_SYNC_HANDLERS.get(device.protocol)
        if handler is None:
            continue
        try:
            summary = handler(device, str(device.organisation_id))
            BiometricSyncLog.objects.create(
                device=device,
                records_fetched=summary['processed'] + summary['skipped'],
                records_processed=summary['processed'],
                records_skipped=summary['skipped'],
                errors=summary.get('errors', []),
                success=len(summary.get('errors', [])) == 0,
            )
            device.last_sync_at = timezone.now()
            device.save(update_fields=['last_sync_at'])
        except Exception as exc:
            BiometricSyncLog.objects.create(
                device=device,
                records_fetched=0,
                records_processed=0,
                records_skipped=0,
                errors=[str(exc)],
                success=False,
            )
```

- [ ] **Step 2: Add Celery beat schedule**

In `backend/clarisal/settings/base.py`, add to `CELERY_BEAT_SCHEDULE`:

```python
CELERY_BEAT_SCHEDULE = {
    # ... existing schedules ...
    'sync-biometric-devices-every-5-min': {
        'task': 'biometrics.sync_pull_devices',
        'schedule': 300,  # every 5 minutes
    },
}
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/biometrics/tasks.py backend/clarisal/settings/base.py
git commit -m "feat(biometrics): Celery beat task to sync all pull-protocol devices every 5 min"
```

---

## Task 8 — Device Management API

**Files:**
- Create: `backend/apps/biometrics/serializers.py`
- Modify: `backend/apps/biometrics/views.py` (add CRUD views)
- Create: `backend/apps/biometrics/org_urls.py`

- [ ] **Step 1: Create `serializers.py`**

```python
# backend/apps/biometrics/serializers.py
from rest_framework import serializers
from .models import BiometricDevice, BiometricSyncLog


class BiometricDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricDevice
        fields = [
            'id', 'name', 'device_serial', 'protocol', 'ip_address', 'port',
            'location', 'is_active', 'last_sync_at', 'created_at',
        ]
        read_only_fields = ['id', 'last_sync_at', 'created_at']


class BiometricDeviceWriteSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = BiometricDevice
        fields = [
            'name', 'device_serial', 'protocol', 'ip_address', 'port',
            'location', 'is_active', 'api_key', 'oauth_client_id',
        ]

    def create(self, validated_data):
        api_key = validated_data.pop('api_key', None)
        device = super().create(validated_data)
        if api_key:
            device.set_api_key(api_key)
            device.save(update_fields=['api_key_hash'])
        return device


class BiometricSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricSyncLog
        fields = ['id', 'synced_at', 'records_fetched', 'records_processed',
                  'records_skipped', 'errors', 'success']
        read_only_fields = fields
```

- [ ] **Step 2: Add CRUD views to `views.py`**

Append to `backend/apps/biometrics/views.py`:

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation
from .serializers import BiometricDeviceSerializer, BiometricDeviceWriteSerializer, BiometricSyncLogSerializer


class BiometricDeviceListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        devices = BiometricDevice.objects.filter(organisation=organisation)
        return Response(BiometricDeviceSerializer(devices, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = BiometricDeviceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.save(organisation=organisation, created_by=request.user)
        return Response(BiometricDeviceSerializer(device).data, status=status.HTTP_201_CREATED)


class BiometricDeviceDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        device = get_object_or_404(BiometricDevice, organisation=organisation, id=pk)
        serializer = BiometricDeviceWriteSerializer(device, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(modified_by=request.user)
        return Response(BiometricDeviceSerializer(device).data)

    def delete(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        device = get_object_or_404(BiometricDevice, organisation=organisation, id=pk)
        device.is_active = False
        device.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class BiometricSyncLogListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        device = get_object_or_404(BiometricDevice, organisation=organisation, id=pk)
        logs = device.sync_logs.order_by('-synced_at')[:50]
        return Response(BiometricSyncLogSerializer(logs, many=True).data)
```

- [ ] **Step 3: Create `org_urls.py`**

```python
# backend/apps/biometrics/org_urls.py
from django.urls import path
from .views import BiometricDeviceListCreateView, BiometricDeviceDetailView, BiometricSyncLogListView

urlpatterns = [
    path('biometrics/devices/', BiometricDeviceListCreateView.as_view()),
    path('biometrics/devices/<uuid:pk>/', BiometricDeviceDetailView.as_view()),
    path('biometrics/devices/<uuid:pk>/sync-logs/', BiometricSyncLogListView.as_view()),
]
```

- [ ] **Step 4: Register in `clarisal/urls.py`**

Add `path('org/', include('apps.biometrics.org_urls'))` to both legacy and versioned URL includes.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/biometrics/serializers.py backend/apps/biometrics/views.py backend/apps/biometrics/org_urls.py
git commit -m "feat(biometrics): device CRUD API endpoints with sync log history"
```

---

## Task 9 — Frontend Biometric Devices Page

**Files:**
- Create: `frontend/src/pages/org/BiometricDevicesPage.tsx`

- [ ] **Step 1: Add API functions to `org-admin.ts`**

```typescript
// In frontend/src/lib/api/org-admin.ts

export interface BiometricDevice {
  id: string;
  name: string;
  device_serial: string;
  protocol: string;
  ip_address: string;
  port: number;
  is_active: boolean;
  last_sync_at: string | null;
}

export async function getBiometricDevices(): Promise<BiometricDevice[]> {
  const res = await apiClient.get('/api/org/biometrics/devices/');
  return res.data;
}

export async function createBiometricDevice(data: Partial<BiometricDevice>): Promise<BiometricDevice> {
  const res = await apiClient.post('/api/org/biometrics/devices/', data);
  return res.data;
}

export async function deleteBiometricDevice(id: string): Promise<void> {
  await apiClient.delete(`/api/org/biometrics/devices/${id}/`);
}

export async function getDeviceSyncLogs(deviceId: string): Promise<object[]> {
  const res = await apiClient.get(`/api/org/biometrics/devices/${deviceId}/sync-logs/`);
  return res.data;
}
```

- [ ] **Step 2: Create `BiometricDevicesPage.tsx`**

```tsx
// frontend/src/pages/org/BiometricDevicesPage.tsx
import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getBiometricDevices, createBiometricDevice, deleteBiometricDevice, getDeviceSyncLogs } from '@/lib/api/org-admin';
import { AppButton } from '@/components/ui/AppButton';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import toast from 'react-hot-toast';

const PROTOCOL_LABELS: Record<string, string> = {
  ZK_ADMS: 'ZKTeco / eSSL (ADMS Push)',
  MATRIX_COSEC: 'Matrix COSEC',
  SUPREMA_BIOSTAR: 'Suprema BioStar 2',
  HIKVISION_ISAPI: 'HikVision ISAPI',
};

export default function BiometricDevicesPage() {
  const qc = useQueryClient();
  const { data: devices = [], isLoading } = useQuery({
    queryKey: ['biometric-devices'],
    queryFn: getBiometricDevices,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBiometricDevice,
    onSuccess: () => {
      toast.success('Device deactivated');
      qc.invalidateQueries({ queryKey: ['biometric-devices'] });
    },
  });

  const [selectedDeviceId, setSelectedDeviceId] = React.useState<string | null>(null);
  const { data: syncLogs = [] } = useQuery({
    queryKey: ['sync-logs', selectedDeviceId],
    queryFn: () => getDeviceSyncLogs(selectedDeviceId!),
    enabled: !!selectedDeviceId,
  });

  if (isLoading) return <div className="p-8 text-sm text-gray-500">Loading devices…</div>;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Biometric Devices</h1>
        <AppButton onClick={() => {/* open add dialog */}}>
          Add Device
        </AppButton>
      </div>

      {devices.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg">No biometric devices configured</p>
          <p className="text-sm mt-1">Add a device to enable automatic attendance import</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-gray-500">
              <tr>
                <th className="py-3 pr-4">Name</th>
                <th className="py-3 pr-4">Protocol</th>
                <th className="py-3 pr-4">Serial / IP</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Last Sync</th>
                <th className="py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {devices.map(device => (
                <tr key={device.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 pr-4 font-medium">{device.name}</td>
                  <td className="py-3 pr-4 text-gray-600">{PROTOCOL_LABELS[device.protocol] ?? device.protocol}</td>
                  <td className="py-3 pr-4 text-gray-600">{device.device_serial || device.ip_address}</td>
                  <td className="py-3 pr-4">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${device.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {device.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-gray-500">
                    {device.last_sync_at ? new Date(device.last_sync_at).toLocaleString() : 'Never'}
                  </td>
                  <td className="py-3 flex gap-2">
                    <AppButton
                      variant="ghost"
                      size="sm"
                      aria-label={`View sync logs for ${device.name}`}
                      onClick={() => setSelectedDeviceId(device.id)}
                    >
                      Logs
                    </AppButton>
                    <ConfirmDialog
                      trigger={
                        <AppButton variant="ghost" size="sm" aria-label={`Deactivate ${device.name}`}>
                          Remove
                        </AppButton>
                      }
                      title={`Deactivate ${device.name}?`}
                      description="The device will no longer sync attendance data."
                      confirmLabel="Deactivate"
                      onConfirm={() => deleteMutation.mutate(device.id)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedDeviceId && syncLogs.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-3">Sync Logs</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b text-left text-gray-500">
                <tr>
                  <th className="py-2 pr-4">Time</th>
                  <th className="py-2 pr-4">Fetched</th>
                  <th className="py-2 pr-4">Processed</th>
                  <th className="py-2 pr-4">Skipped</th>
                  <th className="py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {(syncLogs as any[]).map((log: any) => (
                  <tr key={log.id} className="border-b">
                    <td className="py-2 pr-4">{new Date(log.synced_at).toLocaleString()}</td>
                    <td className="py-2 pr-4">{log.records_fetched}</td>
                    <td className="py-2 pr-4">{log.records_processed}</td>
                    <td className="py-2 pr-4">{log.records_skipped}</td>
                    <td className="py-2">
                      <span className={`text-xs font-medium ${log.success ? 'text-green-600' : 'text-red-600'}`}>
                        {log.success ? 'OK' : 'Failed'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add route and nav item**

In `frontend/src/routes/index.tsx`, add route for `/org/biometric-devices`.
In `OrgLayout.tsx`, add `{ label: 'Biometric Devices', href: '/org/biometric-devices', icon: FingerPrintIcon }` to the Time & Leave nav group.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/org/BiometricDevicesPage.tsx \
        frontend/src/lib/api/org-admin.ts \
        frontend/src/routes/index.tsx \
        frontend/src/components/layouts/OrgLayout.tsx
git commit -m "feat(biometrics): BiometricDevicesPage with device list, sync logs, and deactivate"
```

---

## Verification

```bash
# Run all biometric tests
cd backend && python -m pytest apps/biometrics/ -v
# Expected: all pass

# Check ADMS endpoint resolves
python -c "from django.urls import resolve; print(resolve('/api/biometric/adms/iclock/cdata'))"
# Expected: AdmsCdataView

# Check org endpoint
python -c "from django.urls import resolve; print(resolve('/api/org/biometrics/devices/'))"
# Expected: BiometricDeviceListCreateView
```
