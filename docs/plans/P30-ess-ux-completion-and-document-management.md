# P30 — ESS UX Completion & Document Management

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five medium/low ESS and document-management gaps from the v4 audit: replace the plain-text proof upload in IT declarations with a real file picker, remove the stale `rendered_text` pre-block from payslips, add the missing EPF column to the payroll run detail table, add document expiry tracking to the documents module, and surface the exit interview form in the Employee Detail Page.

**Architecture:** All changes are frontend-heavy with small backend additions. The proof upload uses the existing `documents` S3 upload flow — no new infrastructure required. Document expiry adds an `expiry_date` field + a Celery alert task. Exit interview adds a frontend form tab; the backend models already exist (P20).

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · Celery · React 19 · TypeScript · Radix UI · TanStack Query · pytest · Vitest

---

## Audit Findings Addressed

- `proof_file_key` in IT declarations is a plain text input; employees cannot upload proof documents (Gap #12 — Medium)
- `rendered_text` pre-block still in `PayslipsPage.tsx:236` (Gap #13 — Low)
- EPF employee deduction column missing from `PayrollRunDetailPage` table (Gap #14 — Low)
- No document expiry tracking (`expiry_date` field absent from `Document` model) (Gap #23 — Medium)
- Exit interview UI absent from `EmployeeDetailPage` (backend models complete) (Gap #16 — Medium)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/employees/serializers.py` | Modify | Expose `proof_document` FK on `InvestmentDeclaration` |
| `backend/apps/employees/services.py` | Modify | `set_proof_document(declaration_id, document_id)` helper |
| `backend/apps/documents/models.py` | Modify | Add `expiry_date`, `alert_days_before` fields |
| `backend/apps/documents/serializers.py` | Modify | Expose `expiry_date`, `expires_soon` computed field |
| `backend/apps/documents/migrations/XXXX_document_expiry.py` | Create | Migration for `expiry_date` and `alert_days_before` fields |
| `backend/apps/documents/tasks.py` | Create | Celery task: send expiry alerts for documents expiring soon |
| `backend/apps/documents/tests/test_services.py` | Modify | Expiry detection tests |
| `backend/apps/employees/models.py` | Modify | Add `proof_document` FK to `InvestmentDeclaration` if not present |
| `frontend/src/pages/employee/TaxDeclarationsPage.tsx` | Modify | Replace text input with `DocumentUploadWidget` for proof |
| `frontend/src/pages/employee/PayslipsPage.tsx` | Modify | Remove `<pre>` block at line 236 |
| `frontend/src/pages/org/PayrollRunDetailPage.tsx` | Modify | Add EPF employee deduction column |
| `frontend/src/pages/employee/EmployeeDetailPage.tsx` (or offboarding tab) | Modify | Add exit interview response form |
| `frontend/src/lib/api/employees.ts` | Modify | Add `submitExitInterview` API call |
| `frontend/src/lib/api/documents.ts` | Modify | Add document expiry fields to type definitions |
| `frontend/src/components/DocumentUploadWidget.tsx` | Create | Reusable file-picker backed by document upload endpoint |

---

## Task 1: IT Declaration Proof Document Upload

> **Finding (Gap #12 — Medium):** `TaxDeclarationsPage.tsx` renders `proof_file_key` as `<input type="text" placeholder="Optional storage key">`. Employees cannot upload actual proof documents — they would need to know their S3 key in advance. This is the single largest ESS UX gap vs Zoho People.

### Backend

- [x] Check if `InvestmentDeclaration` model already has a `proof_document` FK to `Document`. If not, add it:

```python
proof_document = models.ForeignKey(
    'documents.Document',
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name='investment_declaration_proofs',
)
```

- [x] Create the migration.
- [x] In `employees/serializers.py`, expose `proof_document_id` as a writable FK and `proof_document_url` as a read-only computed field (presigned S3 URL).
- [x] Add `set_proof_document(declaration_id, document_id, employee)` in `employees/services.py` that validates the document belongs to the same employee before linking.
- [x] Add PATCH endpoint or extend the existing declaration update endpoint to accept `proof_document_id`.

### Frontend

- [x] Create `frontend/src/components/DocumentUploadWidget.tsx`:

```tsx
// Wraps the existing /api/v1/self/documents/upload/ endpoint
// Props: onUpload(documentId: string), accept, label
// Renders: file picker → upload on select → shows filename + "Change" link
// Error state: shows upload failure inline
// Loading state: spinner during upload
```

- [x] In `TaxDeclarationsPage.tsx`, replace the `<input type="text" ...>` for `proof_file_key` with `<DocumentUploadWidget>`.
- [x] After successful upload, the component calls `PATCH /api/v1/self/declarations/:id/` with `{ proof_document_id: uploadedDocId }`.
- [x] Show the existing proof document filename (if any) with a download link next to the upload widget for already-uploaded proofs.
- [x] Add Vitest tests for `DocumentUploadWidget`:
  - Renders file input
  - Successful upload → `onUpload` called with document ID
  - Upload failure → error message rendered
  - Existing proof → filename shown with download link

## Task 2: Remove rendered_text Pre-Block from PayslipsPage

> **Finding (Gap #13 — Low):** `PayslipsPage.tsx:236` — `<pre className="...overflow-x-auto...">{selectedPayslip.rendered_text}</pre>` is still rendered unconditionally below the structured breakdown. This is a raw text fallback superseded by the branded PDF and structured panels added in P25.

- [x] Read `frontend/src/pages/employee/PayslipsPage.tsx` around line 236.
- [x] Remove the `<pre>` block entirely. Do not replace it with anything — the structured breakdown panels above it and the PDF download button are the canonical payslip views.
- [x] If `rendered_text` is still in the payslip API response type definition (`frontend/src/lib/api/payroll.ts`), mark it as `@deprecated` or remove it from the type — do not fetch it if it is no longer displayed.
- [x] Verify no other component references `rendered_text`.
- [x] Update the frontend Vitest test for `PayslipsPage` (if it exists) to remove any assertion on the `<pre>` block.

## Task 3: Add EPF Employee Column to PayrollRunDetailPage

> **Finding (Gap #14 — Low):** The P25 plan spec called for an EPF employee deduction column in the run detail table, but it was not added. EPF is the most common statutory deduction and its absence makes the table incomplete.

- [x] Read `frontend/src/pages/org/PayrollRunDetailPage.tsx` — locate the employee table column definitions.
- [x] Add an `epf_employee` column between the existing `esi_employee` and `pt` columns (or wherever it fits the existing statutory column order — EPF logically comes before ESI).
- [x] The column header: "EPF (Emp)" with a tooltip "Employee EPF contribution (12% of PF wage)".
- [x] The value comes from the `PayrollRunItem` response — confirm the serializer includes `epf_employee`. If not, add it to `PayrollRunItemSerializer`.
- [x] The column should format as currency (`₹XX,XXX`) consistent with adjacent columns.
- [x] Verify the `PayrollRunDetailPage` test covers the new column.

## Task 4: Add Document Expiry Tracking

> **Finding (Gap #23 — Medium):** The `Document` model has no `expiry_date` field. Identity documents (Aadhaar card, passport, driving licence, work permit) and insurance certificates have statutory expiry dates. BambooHR surfaces expiry prominently; Clarisal silently ignores it.

### Backend

- [x] In `documents/models.py`, add:

```python
expiry_date = models.DateField(
    null=True,
    blank=True,
    help_text='Date after which this document is no longer valid. Null = does not expire.',
)
alert_days_before = models.PositiveSmallIntegerField(
    default=30,
    help_text='Days before expiry_date to send an alert notification.',
)
```

- [x] Create the migration.
- [x] In `documents/serializers.py`, expose `expiry_date`, `alert_days_before`, and a computed `expires_soon` boolean:

```python
expires_soon = serializers.SerializerMethodField()

def get_expires_soon(self, obj):
    if obj.expiry_date is None:
        return False
    return obj.expiry_date <= date.today() + timedelta(days=obj.alert_days_before)
```

- [x] Create `documents/tasks.py` with a Celery task `send_document_expiry_alerts`:

```python
@app.task
def send_document_expiry_alerts():
    """
    Run daily. Find documents expiring within their alert window and
    send a notification to the document owner and HR.
    """
    today = date.today()
    expiring = Document.objects.filter(
        expiry_date__isnull=False,
        expiry_date__lte=today + timedelta(days=F('alert_days_before')),
        expiry_date__gte=today,
    ).select_related('employee', 'employee__organisation')

    for doc in expiring.iterator():
        # Use existing notifications app
        send_notification(
            recipient=doc.employee,
            subject=f"Document expiring soon: {doc.document_type.name}",
            body=f"Your {doc.document_type.name} expires on {doc.expiry_date}. Please upload a renewed copy.",
        )
```

- [x] Register `send_document_expiry_alerts` in `CELERY_BEAT_SCHEDULE` to run daily at 9 AM.
- [x] Add tests in `documents/tests/test_services.py`:
  - Document with `expiry_date = today + 15 days`, `alert_days_before = 30` → `expires_soon = True`
  - Document with `expiry_date = today + 45 days`, `alert_days_before = 30` → `expires_soon = False`
  - Document with `expiry_date = None` → `expires_soon = False`
  - `send_document_expiry_alerts` with 2 expiring docs → 2 notifications sent

### Frontend

- [x] In the document upload form (wherever documents are uploaded in the org admin), add an optional `expiry_date` date picker using `AppDatePicker`.
- [x] In the employee document list view, show an amber "Expiring soon" badge next to documents where `expires_soon = true`.
- [x] In the org admin employee detail, show a red "Expired" badge for documents with `expiry_date < today`.

## Task 5: Add Exit Interview UI to EmployeeDetailPage

> **Finding (Gap #16 — Medium):** The backend `ExitInterview` model is complete (P20). The frontend `EmployeeDetailPage` has an offboarding tab but no form for recording the exit interview response.

### Backend

- [x] Verify `ExitInterview` model has the required fields (reasons, feedback, last_working_day confirmation, interviewer, date).
- [x] Verify an API endpoint exists for creating/updating exit interview: `PATCH /api/v1/org/employees/:id/exit-interview/`. If not, add it to `employees/views.py` and `employees/urls.py`.
- [x] The endpoint must be org-admin only (not self-service).

### Frontend

- [x] Read `frontend/src/pages/org/EmployeeDetailPage.tsx` — locate the offboarding tab.
- [x] Add an "Exit Interview" section in the offboarding tab:

```tsx
// If no exit interview recorded: show "Record Exit Interview" button that opens a form
// If exit interview exists: show read-only summary with "Edit" action

// Form fields:
// - exit_date (AppDatePicker)
// - exit_reason (AppSelect: RESIGNATION, TERMINATION, RETIREMENT, etc.)
// - interviewer (AppSelect from org employees list)
// - overall_satisfaction (1–5 star rating or radio)
// - would_recommend_org (Yes/No)
// - feedback (Textarea)
// - areas_of_improvement (Textarea)
```

- [x] Use `useMutation` (TanStack Query) for form submission.
- [x] Show a success toast on save.
- [x] After save, show the exit interview data in read-only view with an "Edit" button.
- [x] Add `submitExitInterview` and `getExitInterview` to `frontend/src/lib/api/employees.ts`.
- [x] Add Vitest tests for the exit interview form section:
  - Renders "Record Exit Interview" when no interview exists
  - Form submission calls the API endpoint
  - After submission, read-only view is shown
