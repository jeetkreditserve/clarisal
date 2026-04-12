# P33 — CT Guided Onboarding Wizard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the Control Tower's "new organisation" flow from a flat form + detail-tab checklist into a step-driven wizard UX that guides CT users through all required configuration steps at org creation time. Also clean up the stale P17 T6 inline CT setup logic that was never completed.

**Architecture:** The wizard is a purely frontend change — the backend org creation API already exists. The wizard is a multi-step form that calls the existing APIs in sequence: create org → add licences → configure settings → seed payroll masters → invite first admin. Server-persisted step state uses the existing `OnboardingChecklist` model from P17.

**Tech Stack:** React 19 · TypeScript · Radix UI · TanStack Query · Vitest · Playwright

---

## Audit Findings Addressed

- CT guided onboarding is a static checklist in the org detail tab, not a wizard UX at new org creation time (Gap #25 — Medium)
- P17 T6 stale CT inline setup logic still unchecked in plan (§8.2)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `frontend/src/pages/ct/NewOrganisationPage.tsx` | Rewrite | Convert from flat form to multi-step wizard |
| `frontend/src/components/wizard/WizardStep.tsx` | Create | Shared step container with progress indicator |
| `frontend/src/components/wizard/WizardProgress.tsx` | Create | Step progress sidebar/stepper component |
| `frontend/src/lib/api/organisations.ts` | Modify | Add `updateOnboardingStep` API call |
| `frontend/src/pages/ct/NewOrganisationPage.test.tsx` | Create | Wizard step navigation and submission tests |
| `backend/apps/organisations/views.py` | Modify | Clean up P17 T6 stale inline setup logic |
| `backend/apps/organisations/serializers.py` | Modify | Clean up P17 T6 stale inline setup logic if needed |
| `docs/plans/P17-guided-onboarding-checklist.md` | Modify | Mark T6 as complete after cleanup |

---

## Task 1: Audit Current NewOrganisationPage and Checklist State

- [x] Read `frontend/src/pages/ct/NewOrganisationPage.tsx` — understand current form structure.
- [x] Read the P17 plan (`docs/plans/P17-guided-onboarding-checklist.md`) — locate T6 and understand what "stale CT inline setup logic" refers to.
- [x] Read the `OnboardingChecklist` model in `organisations/models.py` — understand the persisted step state.
- [x] Identify which wizard steps already have backend API support:
  - Create org: `POST /api/v1/ct/organisations/`
  - Configure settings: `PATCH /api/v1/ct/organisations/:id/settings/`
  - Seed payroll masters: management command (may need an API trigger)
  - Invite first admin: `POST /api/v1/ct/organisations/:id/invite-admin/`
  - Enable feature flags: `PATCH /api/v1/ct/organisations/:id/feature-flags/`
- [x] For any missing API endpoints, plan where to add them.

## Task 2: Design the Wizard Steps

The wizard replaces the flat form with 6 steps. Each step is independently completable (user can go back). Step state is persisted server-side via `OnboardingChecklist`.

**Step 1: Organisation Profile**
- Organisation name, slug/subdomain, industry, country
- Primary billing contact email
- Logo upload (optional)
- Call: `POST /api/v1/ct/organisations/`

**Step 2: Licence Configuration**
- Select plan tier (Starter / Growth / Enterprise)
- Set licence seat count
- Set billing cycle (monthly / annual)
- Set trial end date (optional)
- Call: `POST /api/v1/ct/organisations/:id/licences/`

**Step 3: Feature Flags**
- Module toggles: Payroll, Expenses, Assets, Recruitment, Performance
- Description of each module shown inline so CT user knows what they're enabling
- Pre-selected defaults based on plan tier
- Call: `PATCH /api/v1/ct/organisations/:id/feature-flags/`

**Step 4: Payroll & Compliance Settings**
- State (for PT/LWF seeding)
- ESI branch code
- EPF establishment number
- TDS TAN number
- Fiscal year start (April or custom)
- PT applicable (yes/no)
- Call: `PATCH /api/v1/ct/organisations/:id/settings/`

**Step 5: Seed Payroll Masters**
- One-click "Seed Default Masters" button that triggers seeding of:
  - Default tax slabs (FY2025-26)
  - PT rules for selected state
  - LWF rules for selected state
  - Default cost centre ("General")
  - Default leave types (PL, CL, SL, ML, comp-off)
  - Default document types
- Shows a checklist of what was seeded
- Call: `POST /api/v1/ct/organisations/:id/seed-masters/`

**Step 6: Invite First Admin**
- Admin email, name, phone
- Send invite immediately or save for later
- Call: `POST /api/v1/ct/organisations/:id/invite-admin/`
- Complete: marks the `OnboardingChecklist` as `WIZARD_COMPLETE`

## Task 3: Build Wizard Components

- [x] Create `frontend/src/components/wizard/WizardProgress.tsx`:

```tsx
// Vertical step indicator on the left side of the wizard
// Props: steps: Step[], currentStep: number, completedSteps: number[]
// Renders: numbered circles with check marks for completed, active indicator for current
// Click on completed step: navigate back to it
```

- [x] Create `frontend/src/components/wizard/WizardStep.tsx`:

```tsx
// Wraps each step's content
// Props: title, description, children, onBack, onNext, isLoading, canProceed
// Footer: Back button (disabled on step 1) + "Next →" / "Complete" button
// Loading state: spinner on Next while API call is in-flight
// Error state: inline error banner below form
```

## Task 4: Rewrite NewOrganisationPage as Wizard

- [x] Rewrite `frontend/src/pages/ct/NewOrganisationPage.tsx` to use the wizard components:

```tsx
export function NewOrganisationPage() {
    const [currentStep, setCurrentStep] = useState(0);
    const [createdOrgId, setCreatedOrgId] = useState<string | null>(null);
    const [completedSteps, setCompletedSteps] = useState<number[]>([]);

    const steps = [
        { id: 'profile', title: 'Organisation Profile', component: OrgProfileStep },
        { id: 'licences', title: 'Licence Configuration', component: LicenceStep },
        { id: 'features', title: 'Feature Flags', component: FeatureFlagsStep },
        { id: 'payroll', title: 'Payroll Settings', component: PayrollSettingsStep },
        { id: 'seed', title: 'Seed Masters', component: SeedMastersStep },
        { id: 'admin', title: 'Invite Admin', component: InviteAdminStep },
    ];

    // Each step component receives: orgId, onComplete(nextStep, data)
    // On completion, update the server-side OnboardingChecklist
    ...
}
```

- [x] Route: `/ct/organisations/new` — keep existing route, replace page implementation.
- [x] The "Save & Exit" affordance: allows CT user to abandon wizard and resume later. Resume derives the next unresolved step from persisted org state plus onboarding progress.
- [x] When opening an existing org in CT that has an incomplete wizard, surface a "Resume Onboarding" banner in `OrganisationDetailPage`.

## Task 5: Backend — Seed Masters API Endpoint

> The wizard Step 5 needs a server-side trigger to run seeding for a specific org.

- [x] In `organisations/views.py`, add `SeedOrgMastersView`:

```python
class SeedOrgMastersView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, org_id):
        org = get_object_or_404(Organisation, pk=org_id)
        results = {}

        # Seed payroll masters (tax slabs, PT, LWF, cost centres)
        results['payroll_masters'] = seed_payroll_masters_for_org(org)

        # Seed default leave types
        results['leave_types'] = seed_default_leave_types(org)

        # Seed default document types
        results['document_types'] = ensure_default_document_types(org)

        return Response({'seeded': results}, status=status.HTTP_200_OK)
```

- [x] Register at `POST /api/v1/ct/organisations/:id/seed-masters/`.
- [x] The endpoint is idempotent — calling it twice produces the same result (use `get_or_create` in all seed functions).
- [x] Return a summary of what was created vs already existed.

## Task 6: Clean Up P17 T6 Stale Logic

- [x] Read P17 Task 6 description in `docs/plans/P17-control-tower-governance-and-billing-automation.md`.
- [x] Read the relevant backend view/serializer code identified by P17 T6.
- [x] Remove or complete the stale inline CT setup logic. Options:
  - If the logic was superseded by the wizard, remove it.
  - If it was a partial implementation, complete it as part of this plan.
- [x] Mark P17 T6 as `[x]` in the plan document.

## Task 7: Tests

- [x] Create `NewOrganisationPage.test.tsx`:
  - Step 1: fill out org profile form → click Next → `POST /api/v1/ct/organisations/` called
  - Step 2: configure licences → Next → licence API called
  - Back navigation: clicking Back from Step 3 returns to Step 2 with previous values preserved
  - Step 6 completion → redirects to org detail page
  - Incomplete wizard: org created with `WIZARD_COMPLETE = false` → "Resume Onboarding" banner appears in org detail
  - "Save & Exit" → wizard state persisted; resuming from `/ct/organisations/:id` restores step
  Status: the new Vitest coverage now exercises step progression, batch save, back navigation, Save-and-Exit, final redirect, and the resume banner.
- [x] Add Playwright E2E test: full 6-step wizard flow → verify org appears in org list with correct settings.
