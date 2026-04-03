# P07 — Notifications System

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-app notification system with a bell icon and unread count badge, approval/payroll email triggers via Celery, and polling-based delivery.

**Architecture:** New `notifications` Django app with a `Notification` model using `GenericForeignKey` for flexible object linking. Frontend polls every 30s via React Query. Emails use existing Celery infrastructure (`communications` app or direct Celery tasks). No WebSocket required.

**Tech Stack:** Django 4.2 · DRF · Celery 5.4 · React 19 · TanStack Query v5 · Radix UI Popover

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/apps/notifications/__init__.py` | Create | App package |
| `backend/apps/notifications/apps.py` | Create | Django app config |
| `backend/apps/notifications/models.py` | Create | `Notification` model with GenericFK |
| `backend/apps/notifications/services.py` | Create | `create_notification()`, `mark_read()`, `mark_all_read()` |
| `backend/apps/notifications/serializers.py` | Create | `NotificationSerializer` |
| `backend/apps/notifications/views.py` | Create | List + mark-read endpoints |
| `backend/apps/notifications/urls.py` | Create | URL patterns |
| `backend/apps/notifications/tasks.py` | Create | Email notification Celery tasks |
| `backend/apps/notifications/tests/test_services.py` | Create | Service unit tests |
| `backend/apps/approvals/services.py` | Modify | Add notification triggers on approval events |
| `backend/apps/payroll/services.py` | Modify | Add notification trigger on payroll finalization |
| `backend/clarisal/settings/base.py` | Modify | Add `notifications` to INSTALLED_APPS |
| `backend/clarisal/urls.py` | Modify | Include notifications URLs |
| `frontend/src/lib/api/notifications.ts` | Create | API functions |
| `frontend/src/hooks/useNotifications.ts` | Create | React Query hooks |
| `frontend/src/components/ui/NotificationBell.tsx` | Create | Bell icon with unread badge |
| `frontend/src/components/ui/NotificationPanel.tsx` | Create | Dropdown notification list |
| `frontend/src/components/layouts/OrgLayout.tsx` | Modify | Add NotificationBell to header |
| `frontend/src/components/layouts/EmployeeLayout.tsx` | Modify | Add NotificationBell to header |

---

## Task 1 — `notifications` Django App

**Files:**
- Create: `backend/apps/notifications/__init__.py`
- Create: `backend/apps/notifications/apps.py`
- Create: `backend/apps/notifications/models.py`
- Modify: `backend/clarisal/settings/base.py`

- [ ] **Step 1: Create app skeleton**

```bash
cd backend && python manage.py startapp notifications apps/notifications
```

- [ ] **Step 2: Update `apps.py`**

```python
# backend/apps/notifications/apps.py
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    label = 'notifications'
```

- [ ] **Step 3: Add to `INSTALLED_APPS`**

In `backend/clarisal/settings/base.py`, add `'apps.notifications'` to the `LOCAL_APPS` list.

- [ ] **Step 4: Write the model**

```python
# backend/apps/notifications/models.py
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.common.models import AuditedBaseModel


class NotificationKind(models.TextChoices):
    LEAVE_APPROVED = 'LEAVE_APPROVED', 'Leave Approved'
    LEAVE_REJECTED = 'LEAVE_REJECTED', 'Leave Rejected'
    LEAVE_CANCELLED = 'LEAVE_CANCELLED', 'Leave Cancelled'
    ATTENDANCE_REGULARIZATION_APPROVED = 'ATT_REG_APPROVED', 'Attendance Regularization Approved'
    ATTENDANCE_REGULARIZATION_REJECTED = 'ATT_REG_REJECTED', 'Attendance Regularization Rejected'
    COMPENSATION_APPROVED = 'COMP_APPROVED', 'Compensation Approved'
    COMPENSATION_REJECTED = 'COMP_REJECTED', 'Compensation Rejected'
    PAYROLL_FINALIZED = 'PAYROLL_FINALIZED', 'Payroll Finalized'
    GENERAL = 'GENERAL', 'General'


class Notification(AuditedBaseModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    kind = models.CharField(max_length=40, choices=NotificationKind.choices, default=NotificationKind.GENERAL)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)

    # Generic FK to the related object (leave request, payroll run, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=36, null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read'], name='notif_recipient_read_idx'),
        ]

    def __str__(self):
        return f'{self.kind} → {self.recipient_id} | {self.title[:40]}'
```

- [ ] **Step 5: Generate and apply migration**

```bash
cd backend && python manage.py makemigrations notifications --name initial
cd backend && python manage.py migrate
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/notifications/ backend/clarisal/settings/base.py
git commit -m "feat(notifications): create notifications app with Notification model"
```

---

## Task 2 — Notification Service Functions

**Files:**
- Create: `backend/apps/notifications/services.py`
- Create: `backend/apps/notifications/tests/__init__.py`
- Create: `backend/apps/notifications/tests/test_services.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/notifications/tests/test_services.py
from django.test import TestCase
from django.utils import timezone
from apps.notifications.models import Notification, NotificationKind
from apps.notifications.services import create_notification, mark_notification_read, mark_all_read
from apps.accounts.tests.factories import UserFactory


class TestCreateNotification(TestCase):
    def test_create_notification_persists(self):
        user = UserFactory()
        notif = create_notification(
            recipient=user,
            kind=NotificationKind.GENERAL,
            title='Test notification',
            body='Test body',
        )
        self.assertIsNotNone(notif.id)
        self.assertFalse(notif.is_read)
        self.assertEqual(notif.title, 'Test notification')

    def test_create_notification_with_related_object(self):
        from apps.accounts.tests.factories import OrganisationFactory
        user = UserFactory()
        org = OrganisationFactory()
        notif = create_notification(
            recipient=user,
            kind=NotificationKind.PAYROLL_FINALIZED,
            title='Payroll finalized',
            related_object=org,
        )
        self.assertEqual(notif.object_id, str(org.id))
        self.assertIsNotNone(notif.content_type)


class TestMarkRead(TestCase):
    def test_mark_notification_read(self):
        user = UserFactory()
        notif = create_notification(recipient=user, kind=NotificationKind.GENERAL, title='Test')
        self.assertFalse(notif.is_read)
        mark_notification_read(notif, user)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertIsNotNone(notif.read_at)

    def test_mark_read_only_marks_own_notifications(self):
        user = UserFactory()
        other_user = UserFactory()
        notif = create_notification(recipient=other_user, kind=NotificationKind.GENERAL, title='Test')
        with self.assertRaises(PermissionError):
            mark_notification_read(notif, user)

    def test_mark_all_read_marks_only_recipient_notifications(self):
        user = UserFactory()
        other_user = UserFactory()
        create_notification(recipient=user, kind=NotificationKind.GENERAL, title='Notif 1')
        create_notification(recipient=user, kind=NotificationKind.GENERAL, title='Notif 2')
        create_notification(recipient=other_user, kind=NotificationKind.GENERAL, title='Other')
        mark_all_read(user)
        self.assertEqual(Notification.objects.filter(recipient=user, is_read=False).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=other_user, is_read=False).count(), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/notifications/tests/test_services.py -v
```

Expected: `FAIL` — services module not found.

- [ ] **Step 3: Create `services.py`**

```python
# backend/apps/notifications/services.py
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import Notification, NotificationKind


def create_notification(
    recipient,
    kind: str,
    title: str,
    body: str = '',
    organisation=None,
    related_object=None,
    actor=None,
) -> Notification:
    """Create and persist a notification for a user."""
    content_type = None
    object_id = None

    if related_object is not None:
        content_type = ContentType.objects.get_for_model(related_object)
        object_id = str(related_object.pk)

    return Notification.objects.create(
        recipient=recipient,
        organisation=organisation,
        kind=kind,
        title=title,
        body=body,
        content_type=content_type,
        object_id=object_id,
        created_by=actor,
    )


def mark_notification_read(notification: Notification, requesting_user) -> Notification:
    """Mark a single notification as read. Raises PermissionError if not the recipient."""
    if notification.recipient_id != requesting_user.id:
        raise PermissionError('Cannot mark another user\'s notification as read.')
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at', 'modified_at'])
    return notification


def mark_all_read(user) -> int:
    """Mark all unread notifications for a user as read. Returns count updated."""
    now = timezone.now()
    return Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True, read_at=now
    )
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/notifications/tests/test_services.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/notifications/services.py backend/apps/notifications/tests/
git commit -m "feat(notifications): NotificationService with create, mark_read, mark_all_read"
```

---

## Task 3 — Notification API Endpoints

**Files:**
- Create: `backend/apps/notifications/serializers.py`
- Create: `backend/apps/notifications/views.py`
- Create: `backend/apps/notifications/urls.py`
- Modify: `backend/clarisal/urls.py`

- [ ] **Step 1: Create `serializers.py`**

```python
# backend/apps/notifications/serializers.py
from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'kind', 'title', 'body', 'is_read', 'read_at', 'created_at',
            'object_id',
        ]
        read_only_fields = fields
```

- [ ] **Step 2: Create `views.py`**

```python
# backend/apps/notifications/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.accounts.permissions import IsEmployee, IsOrgAdmin, BelongsToActiveOrg
from apps.accounts.workspaces import get_active_employee

from .models import Notification
from .serializers import NotificationSerializer
from .services import mark_notification_read, mark_all_read


class MyNotificationListView(APIView):
    """GET /api/me/notifications/ — paginated list, most recent first."""
    permission_classes = [IsEmployee]

    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        unread_count = qs.filter(is_read=False).count()
        # Return at most 50 most recent
        serializer = NotificationSerializer(qs[:50], many=True)
        return Response({
            'unread_count': unread_count,
            'results': serializer.data,
        })


class MyNotificationMarkReadView(APIView):
    """PATCH /api/me/notifications/{id}/read/"""
    permission_classes = [IsEmployee]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, id=pk, recipient=request.user)
        mark_notification_read(notification, request.user)
        return Response(NotificationSerializer(notification).data)


class MyNotificationMarkAllReadView(APIView):
    """POST /api/me/notifications/mark-all-read/"""
    permission_classes = [IsEmployee]

    def post(self, request):
        count = mark_all_read(request.user)
        return Response({'marked_read': count})
```

- [ ] **Step 3: Create `urls.py`**

```python
# backend/apps/notifications/urls.py
from django.urls import path
from .views import MyNotificationListView, MyNotificationMarkReadView, MyNotificationMarkAllReadView

urlpatterns = [
    path('notifications/', MyNotificationListView.as_view()),
    path('notifications/<uuid:pk>/read/', MyNotificationMarkReadView.as_view()),
    path('notifications/mark-all-read/', MyNotificationMarkAllReadView.as_view()),
]
```

- [ ] **Step 4: Register in `clarisal/urls.py`**

Add to the `_app_includes` list (and to the legacy `urlpatterns`) under the `me/` group:
```python
path('me/', include('apps.notifications.urls')),
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/notifications/serializers.py backend/apps/notifications/views.py backend/apps/notifications/urls.py backend/clarisal/urls.py
git commit -m "feat(notifications): REST endpoints for list, mark-read, mark-all-read"
```

---

## Task 4 — Approval Notification Triggers

**Files:**
- Modify: `backend/apps/approvals/services.py`

- [ ] **Step 1: Find approval outcome handlers**

```bash
grep -n "APPROVED\|REJECTED\|status" backend/apps/approvals/services.py | head -30
```

Locate the function(s) that set an approval request status to APPROVED or REJECTED (likely `process_approval_action()` or similar).

- [ ] **Step 2: Add notification calls after status change**

In the function that finalizes an approval outcome, add notification creation:

```python
from apps.notifications.services import create_notification
from apps.notifications.models import NotificationKind


def _notify_approval_outcome(approval_request, new_status: str, actor):
    """Create an in-app notification for the requester when approval is decided."""
    if new_status == 'APPROVED':
        kind = NotificationKind.LEAVE_APPROVED  # will be overridden per request type
        title = 'Your request has been approved'
    else:
        kind = NotificationKind.LEAVE_REJECTED
        title = 'Your request has been rejected'

    # Map approval request kind to notification kind
    kind_map = {
        'LEAVE_REQUEST': (NotificationKind.LEAVE_APPROVED, NotificationKind.LEAVE_REJECTED),
        'ATTENDANCE_REGULARIZATION': (
            NotificationKind.ATTENDANCE_REGULARIZATION_APPROVED,
            NotificationKind.ATTENDANCE_REGULARIZATION_REJECTED,
        ),
        'COMPENSATION_ASSIGNMENT': (
            NotificationKind.COMPENSATION_APPROVED,
            NotificationKind.COMPENSATION_REJECTED,
        ),
    }

    if approval_request.kind in kind_map:
        approved_kind, rejected_kind = kind_map[approval_request.kind]
        kind = approved_kind if new_status == 'APPROVED' else rejected_kind

    if approval_request.requester_user_id:
        create_notification(
            recipient_id=approval_request.requester_user_id,
            kind=kind,
            title=title,
            body=f'Your {approval_request.kind.replace("_", " ").lower()} request has been {new_status.lower()}.',
            organisation=approval_request.organisation,
            related_object=approval_request,
            actor=actor,
        )
```

Call `_notify_approval_outcome(approval_request, new_status, actor)` at the end of `process_approval_action()`.

- [ ] **Step 3: Run existing approval tests to verify no regression**

```bash
cd backend && python -m pytest apps/approvals/ -v --tb=short
```

Expected: All existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/approvals/services.py
git commit -m "feat(notifications): trigger in-app notification on approval approved/rejected"
```

---

## Task 5 — Payroll Finalization Notification Trigger

**Files:**
- Modify: `backend/apps/payroll/services.py`

- [ ] **Step 1: Find `finalize_pay_run` in `services.py`**

```bash
grep -n "def finalize_pay_run\|finalize" backend/apps/payroll/services.py
```

- [ ] **Step 2: Add notification for all employees after finalization**

At the end of `finalize_pay_run()`, after payslips are committed, add:

```python
from apps.notifications.services import create_notification
from apps.notifications.models import NotificationKind


def _notify_employees_payroll_finalized(pay_run, actor):
    """Notify all employees who have a payslip in this run."""
    from apps.employees.models import Employee
    employee_users = (
        pay_run.items.filter(payslip__isnull=False)
        .select_related('employee__user')
        .values_list('employee__user_id', flat=True)
        .distinct()
    )
    for user_id in employee_users:
        create_notification(
            recipient_id=user_id,
            kind=NotificationKind.PAYROLL_FINALIZED,
            title=f'Your payslip for {pay_run.month}/{pay_run.year} is ready',
            body='Your payslip has been finalized. View it in your payslips section.',
            organisation=pay_run.organisation,
            related_object=pay_run,
            actor=actor,
        )
```

Call this function at the end of `finalize_pay_run()`.

- [ ] **Step 3: Commit**

```bash
git add backend/apps/payroll/services.py
git commit -m "feat(notifications): notify employees when payroll run is finalized"
```

---

## Task 6 — Celery Email Notification Tasks

**Files:**
- Create: `backend/apps/notifications/tasks.py`

- [ ] **Step 1: Create email tasks**

```python
# backend/apps/notifications/tasks.py
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task(name='notifications.send_approval_email')
def send_approval_outcome_email(user_id: str, subject: str, message: str):
    """Send an email notification about an approval decision."""
    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            return {'status': 'SKIPPED', 'reason': 'no email'}
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return {'status': 'SENT', 'recipient': user.email}
    except User.DoesNotExist:
        return {'status': 'ERROR', 'reason': f'User {user_id} not found'}


@shared_task(name='notifications.send_payroll_ready_email')
def send_payroll_ready_email(user_id: str, pay_period: str, frontend_url: str):
    """Send payslip ready email to an employee."""
    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            return {'status': 'SKIPPED', 'reason': 'no email'}
        subject = f'Your payslip for {pay_period} is ready'
        message = (
            f'Hello {user.first_name},\n\n'
            f'Your payslip for {pay_period} has been finalized and is now available.\n\n'
            f'View your payslip: {frontend_url}\n\n'
            f'Regards,\nHR Team'
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return {'status': 'SENT', 'recipient': user.email}
    except User.DoesNotExist:
        return {'status': 'ERROR', 'reason': f'User {user_id} not found'}
```

- [ ] **Step 2: Dispatch email tasks from notification triggers**

In `backend/apps/approvals/services.py` `_notify_approval_outcome()`, after `create_notification()`:

```python
from apps.notifications.tasks import send_approval_outcome_email
send_approval_outcome_email.delay(
    str(approval_request.requester_user_id),
    subject=title,
    message=f'Your {approval_request.kind.replace("_", " ").lower()} request has been {new_status.lower()}.',
)
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/notifications/tasks.py backend/apps/approvals/services.py
git commit -m "feat(notifications): Celery email tasks for approval and payroll notifications"
```

---

## Task 7 — Frontend Notification Bell

**Files:**
- Create: `frontend/src/lib/api/notifications.ts`
- Create: `frontend/src/hooks/useNotifications.ts`
- Create: `frontend/src/components/ui/NotificationBell.tsx`
- Create: `frontend/src/components/ui/NotificationPanel.tsx`
- Modify: `frontend/src/components/layouts/OrgLayout.tsx`
- Modify: `frontend/src/components/layouts/EmployeeLayout.tsx`

- [ ] **Step 1: Create API functions**

```typescript
// frontend/src/lib/api/notifications.ts
import { apiClient } from './client';

export interface Notification {
  id: string;
  kind: string;
  title: string;
  body: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  object_id: string | null;
}

export interface NotificationListResponse {
  unread_count: number;
  results: Notification[];
}

export async function getMyNotifications(): Promise<NotificationListResponse> {
  const response = await apiClient.get('/api/me/notifications/');
  return response.data;
}

export async function markNotificationRead(id: string): Promise<Notification> {
  const response = await apiClient.patch(`/api/me/notifications/${id}/read/`);
  return response.data;
}

export async function markAllNotificationsRead(): Promise<{ marked_read: number }> {
  const response = await apiClient.post('/api/me/notifications/mark-all-read/');
  return response.data;
}
```

- [ ] **Step 2: Create React Query hooks**

```typescript
// frontend/src/hooks/useNotifications.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMyNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from '@/lib/api/notifications';

export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: getMyNotifications,
    refetchInterval: 30_000, // poll every 30 seconds
    staleTime: 25_000,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}
```

- [ ] **Step 3: Create `NotificationPanel.tsx`**

```tsx
// frontend/src/components/ui/NotificationPanel.tsx
import { formatDistanceToNow } from 'date-fns';
import { useMarkNotificationRead, useMarkAllRead } from '@/hooks/useNotifications';
import type { Notification } from '@/lib/api/notifications';

interface Props {
  notifications: Notification[];
  onClose: () => void;
}

export function NotificationPanel({ notifications, onClose }: Props) {
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllRead();

  return (
    <div className="w-80 max-h-96 overflow-y-auto bg-white rounded-lg shadow-xl border">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h3 className="font-semibold text-sm">Notifications</h3>
        <button
          className="text-xs text-blue-600 hover:underline"
          onClick={() => markAllRead.mutate()}
          aria-label="Mark all notifications as read"
        >
          Mark all read
        </button>
      </div>
      {notifications.length === 0 ? (
        <p className="text-center text-sm text-gray-400 py-8">No notifications</p>
      ) : (
        <ul role="list">
          {notifications.map(n => (
            <li
              key={n.id}
              className={`px-4 py-3 border-b last:border-0 cursor-pointer hover:bg-gray-50 ${!n.is_read ? 'bg-blue-50' : ''}`}
              onClick={() => { if (!n.is_read) markRead.mutate(n.id); }}
              role="button"
              aria-label={`Notification: ${n.title}${n.is_read ? '' : ' (unread)'}`}
            >
              <p className={`text-sm ${!n.is_read ? 'font-medium' : 'text-gray-700'}`}>{n.title}</p>
              {n.body && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>}
              <p className="text-xs text-gray-400 mt-1">
                {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create `NotificationBell.tsx`**

```tsx
// frontend/src/components/ui/NotificationBell.tsx
import * as React from 'react';
import * as Popover from '@radix-ui/react-popover';
import { BellIcon } from 'lucide-react';
import { useNotifications } from '@/hooks/useNotifications';
import { NotificationPanel } from './NotificationPanel';

export function NotificationBell() {
  const { data } = useNotifications();
  const unreadCount = data?.unread_count ?? 0;

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          className="relative p-2 rounded-full hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
        >
          <BellIcon className="h-5 w-5 text-gray-600" aria-hidden="true" />
          {unreadCount > 0 && (
            <span
              className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold"
              aria-hidden="true"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content align="end" sideOffset={8}>
          <NotificationPanel notifications={data?.results ?? []} onClose={() => {}} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
```

- [ ] **Step 5: Add to layout headers**

In `OrgLayout.tsx` and `EmployeeLayout.tsx`, find the header element and add the bell:

```tsx
import { NotificationBell } from '@/components/ui/NotificationBell';

// Inside the header JSX:
<div className="flex items-center gap-3">
  <NotificationBell />
  {/* existing profile/avatar */}
</div>
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api/notifications.ts \
        frontend/src/hooks/useNotifications.ts \
        frontend/src/components/ui/NotificationBell.tsx \
        frontend/src/components/ui/NotificationPanel.tsx \
        frontend/src/components/layouts/OrgLayout.tsx \
        frontend/src/components/layouts/EmployeeLayout.tsx
git commit -m "feat(notifications): notification bell with unread badge and dropdown panel"
```

---

## Verification

```bash
# Backend tests
cd backend && python -m pytest apps/notifications/ -v
# Expected: all pass

# Check API routes registered
python manage.py show_urls | grep notifications
# Expected: /api/me/notifications/ and variants listed
```
