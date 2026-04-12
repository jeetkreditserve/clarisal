# P35 — Recruitment → Onboarding Handoff

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Connect the Recruitment (ATS) module to the Employee Onboarding flow. When a candidate accepts an offer, HR should be able to convert the candidate to an employee in one click, with the employee invite pre-populated from the candidate/offer data (name, email, role, department, salary, start date). This eliminates the current manual re-entry between ATS and HR.

**Architecture:** Add a `convert_candidate_to_employee_invite` service function in `recruitment/services.py` that reads `Candidate` + `Offer` data and calls the existing `invite_employee` function from `employees/services.py`. Add a UI action on the offer acceptance screen. No new models are strictly required — the candidate has an FK to offer which has all the data needed for the invite.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · React 19 · TypeScript · Radix UI · TanStack Query · pytest · Vitest

---

## Audit Findings Addressed

- Recruitment/ATS pipeline present; no onboarding handoff — "Convert candidate to employee" action at offer acceptance absent (Gap #30 — Medium)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/recruitment/services.py` | Modify | Add `convert_candidate_to_employee` |
| `backend/apps/recruitment/views.py` | Modify | Add `ConvertCandidateView` action endpoint |
| `backend/apps/recruitment/urls.py` | Modify | Register convert endpoint |
| `backend/apps/recruitment/serializers.py` | Modify | Add `CandidateConversionSerializer` |
| `backend/apps/recruitment/models.py` | Modify | Add `converted_to_employee` FK and `converted_at` field on `Candidate` |
| `backend/apps/recruitment/migrations/XXXX_candidate_conversion.py` | Create | Migration for conversion tracking fields |
| `backend/apps/recruitment/tests/test_services.py` | Modify | Conversion service tests |
| `backend/apps/recruitment/tests/test_views.py` | Modify | API endpoint tests |
| `frontend/src/pages/org/CandidateDetailPage.tsx` | Modify | Add "Convert to Employee" action on offer accepted candidates |
| `frontend/src/lib/api/recruitment.ts` | Modify | Add `convertCandidateToEmployee` API call |

---

## Task 1: Audit Current Recruitment Models

- [x] Read `backend/apps/recruitment/models.py` — document: `JobPosting`, `Application`, `Candidate`, `Interview`, `Offer` models and their fields.
- [x] Confirm which fields on `Offer` map to `invite_employee()` parameters:
  - `Offer.offered_role` / `Job.title` → `designation`
  - `Offer.offered_department` → `department`
  - `Offer.offered_salary` → `monthly_gross`
  - `Offer.start_date` → `date_of_joining`
  - `Candidate.email` → `email`
  - `Candidate.name` → `first_name` + `last_name`
  - `Application.job_posting.office_location` → `office_location`
- [x] Read `employees/services.py:invite_employee()` to understand its expected parameters.
- [x] Confirm the `Offer` model has an `acceptance_status` or equivalent field — only accepted offers should be convertible.

## Task 2: Add Conversion Tracking to Candidate Model

- [x] In `recruitment/models.py`, add:

```python
converted_to_employee = models.ForeignKey(
    'employees.Employee',
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name='sourced_from_candidate',
    help_text='Set when candidate is converted to an employee via the onboarding handoff.',
)
converted_at = models.DateTimeField(null=True, blank=True)
```

- [x] Create the migration.
- [x] These fields are the canonical link between ATS and HR — they prevent double-conversion and allow tracing employee provenance.

## Task 3: Implement convert_candidate_to_employee Service

- [x] In `recruitment/services.py`, add:

```python
def convert_candidate_to_employee(
    candidate: Candidate,
    offer: Offer,
    converted_by: User,
) -> Employee:
    """
    Convert an accepted candidate to an employee invite.
    Reads offer/candidate data and calls invite_employee.
    Returns the created Employee record.
    """
    if candidate.converted_to_employee_id is not None:
        raise ConversionError(
            f"Candidate {candidate.pk} already converted to employee {candidate.converted_to_employee_id}"
        )

    if offer.acceptance_status != OfferAcceptanceStatus.ACCEPTED:
        raise ConversionError("Only accepted offers can be converted to employee invites.")

    # Split candidate name into first/last
    name_parts = candidate.name.strip().split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    # Resolve designation and department from offer
    designation = (
        Designation.objects.filter(
            organisation=offer.organisation,
            title__iexact=offer.offered_role,
        ).first()
    )
    department = offer.offered_department  # FK or name depending on model

    # Call the existing invite_employee service
    employee = invite_employee(
        organisation=offer.organisation,
        email=candidate.email,
        first_name=first_name,
        last_name=last_name,
        designation=designation,
        department=department,
        date_of_joining=offer.start_date,
        office_location=offer.application.job_posting.office_location,
        monthly_gross=offer.offered_salary,
        invited_by=converted_by,
        source='RECRUITMENT',
    )

    # Record the conversion
    candidate.converted_to_employee = employee
    candidate.converted_at = timezone.now()
    candidate.save(update_fields=['converted_to_employee', 'converted_at'])

    # Log to audit
    log_audit_event(
        user=converted_by,
        action='CANDIDATE_CONVERTED',
        model='Candidate',
        object_id=str(candidate.pk),
        data={'employee_id': str(employee.pk)},
    )

    return employee
```

## Task 4: Add API Endpoint

- [x] In `recruitment/views.py`, add `ConvertCandidateView`:

```python
class ConvertCandidateView(APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def post(self, request, candidate_id):
        candidate = get_object_or_404(
            Candidate, pk=candidate_id, organisation=get_active_admin_organisation(request)
        )
        # Get the most recent accepted offer
        offer = Offer.objects.filter(
            candidate=candidate,
            acceptance_status=OfferAcceptanceStatus.ACCEPTED,
        ).latest('created_at')

        employee = convert_candidate_to_employee(
            candidate=candidate,
            offer=offer,
            converted_by=request.user,
        )
        serializer = EmployeeBasicSerializer(employee)
        return Response({
            'employee': serializer.data,
            'message': f"Candidate converted to employee invite for {employee.email}",
        }, status=status.HTTP_201_CREATED)
```

- [x] Register at `POST /api/v1/org/recruitment/candidates/:id/convert/`.
- [x] The endpoint returns the created employee record so the frontend can navigate to the employee detail page.

## Task 5: Frontend — Convert Action on Candidate Detail

- [x] Read `frontend/src/pages/org/CandidateDetailPage.tsx` (or equivalent).
- [x] In the offer section of the candidate detail page, when `offer.acceptance_status == 'ACCEPTED'` and `candidate.converted_to_employee == null`, show a "Convert to Employee →" button.
- [x] On click, show a `ConfirmDialog`:
  - Title: "Convert Candidate to Employee"
  - Body: "This will create an employee invite for [Name] with the following details: [list offer details]"
  - Fields shown: name, email, role, department, salary, start date
  - Allow editing before confirming (override fields if needed — optional)
  - Confirm button: "Convert & Send Invite"
- [x] After successful conversion:
  - Show success toast: "Employee invite sent to [email]"
  - Show "View Employee →" link that navigates to the new employee's profile
  - Replace "Convert to Employee" button with "Converted: [employee name] ↗" (read-only)
- [x] If the candidate is already converted (`converted_to_employee != null`), show the read-only link to the existing employee.
- [x] Add `convertCandidateToEmployee` to `frontend/src/lib/api/recruitment.ts`.

## Task 6: Pre-Population Review

- [x] After conversion, verify in the employee detail page that the following fields are correctly pre-populated from the offer:
  - Name ✓
  - Email ✓
  - Department ✓
  - Designation ✓
  - Date of joining ✓
  - Monthly gross (compensation assignment) ✓
- [x] If any field is not mapped correctly, fix the mapping in `convert_candidate_to_employee`.

## Task 7: Tests

- [x] Add backend tests in `recruitment/tests/test_services.py`:
  - `convert_candidate_to_employee` with accepted offer → employee created with correct fields
  - Converting same candidate twice → `ConversionError` raised
  - Converting candidate with non-accepted offer → `ConversionError` raised
  - `candidate.converted_to_employee` FK set after conversion
  - Audit event logged on conversion
- [x] Add backend tests in `recruitment/tests/test_views.py`:
  - `POST .../convert/` with accepted offer → HTTP 201, employee data returned
  - `POST .../convert/` when already converted → HTTP 409 or 400
  - Non-org-admin user → HTTP 403
- [x] Add Vitest tests for the conversion UI:
  - [x] "Convert to Employee" button visible when offer accepted and not yet converted
  - [x] Button hidden when offer not accepted
  - [x] "Converted: [name]" shown when already converted
  - [x] ConfirmDialog shows correct offer data
