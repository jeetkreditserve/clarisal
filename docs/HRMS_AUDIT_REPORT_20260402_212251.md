# HRMS Audit Report

- Timestamp: `20260402_212251` UTC
- Audit version: `v1.0-cycle1`
- Codebase / branch: `clarisal` / `refactor-1`
- Benchmark sources consulted:
  - Zoho People: `https://www.zoho.com/people/`
  - Zoho People User Access Control: `https://www.zoho.com/people/help/adminguide/user-access-control.html`
  - Zoho Payroll Employees: `https://www.zoho.com/in/payroll/help/employer/employees/`
  - Zoho Payroll Employee Portal: `https://www.zoho.com/in/payroll/help/employee/portal-overview.html`
  - Zoho Payroll Attendance Reports: `https://www.zoho.com/in/payroll/help/employer/reports/attendance-reports.html`
  - Rippling Permissions: `https://www.rippling.com/platform/permissions`
  - BambooHR Time & Attendance: `https://www.bamboohr.com/time-tracking/`
  - BambooHR HR Reporting: `https://www.bamboohr.com/hr-reporting/`
- Scope covered:
  - Backend review: auth, permissions, organisations, employees, audit, payroll, attendance, documents, invitations
  - Frontend review: CT routing, CT organisation detail, auth flows, audit timeline usage
  - Functional execution: backend regression tests, Playwright auth + CT organisation flows
  - Benchmarking: India-first HRMS expectations with Zoho primary and Rippling/BambooHR triangulation
- Audit status: `Cycle 1 baseline completed; Wave 2 remediation partially executed`

## 1. Executive Summary
Clarisal has a credible early HRMS foundation across CT, Org Admin, and Employee surfaces, but it is not yet at a production-trust or near-parity bar against Zoho-led market expectations. The most serious confirmed gap in this cycle was audit-trail privacy: raw PAN, address, phone, and payroll-like values could be stored and exposed through the audit timeline, including CT-facing views. That violated the intended CT support boundary and weakened privacy posture.

Wave 1 fixed that specific gap by sanitizing sensitive audit payloads at write time, redacting historical raw payloads at read time, and adding regression coverage around CT/org audit visibility. Wave 2 added CT-specific masking for employee actor/device metadata, shipped a dedicated onboarding blocker support surface that shows blocker counts and document queue pressure without exposing documents or employee PII, and added structured CT payroll/attendance diagnostics for missing setup and blocked operational states. This cycle also cleaned up brittle CT Playwright coverage that no longer matched the real UI behavior.

Even after those fixes, the product still has substantial competitive gaps in payroll completeness, attendance capture maturity, reporting/export depth, CT payroll/attendance diagnostics, and role-bounded UX polish. Current readiness remains below production trust for a serious HR/payroll deployment.

## 2. Benchmark Framework
This audit used an India-first benchmark.

Table-stakes expectations taken from Zoho People / Zoho Payroll official materials:
- Role-based form, field, and action permissions, including import/export and IP restrictions.
- Employee and manager self-service for payslips, salary details, claims, declarations, and attendance visibility.
- Attendance-to-payroll linkage, attendance reports, approvals, and reminders.
- Employee master data covering basics, salary details, personal info, and payment info.

Maturity expectations triangulated from Rippling / BambooHR official materials:
- Dynamic scope-based permissions and approval routing.
- Time tracking with mobile/geolocation and payroll sync.
- Report builder / analytics surfaces for operational confidence.
- Permission models that distinguish scope, access, and actions rather than simple page visibility.

## 3. Role-by-Role Findings
### Control Tower
- Strengths:
  - Broad org-level visibility already exists for org profile, licence state, configuration, attendance support, approval support, payroll support, and audit timeline.
  - CT employee list/detail endpoints are already sanitized compared with Org Admin employee views.
  - CT now has a dedicated onboarding support tab for blocker counts, document queue state, and top blocker types without document access.
  - CT payroll and attendance tabs now surface explicit setup and incident diagnostics instead of only showing empty summary cards.
- Gaps:
  - CT support depth is still summary-oriented. It does not yet provide rich failure drill-downs, reconciliation tools, or “what was misconfigured” guidance comparable to mature HRMS admin-support planes.
  - CT audit tooling is safer now, but still not support-optimized with benchmark-level filters, severity framing, or investigative ergonomics.

### Org Admin
- Strengths:
  - Org Admin can manage organisation setup, employees, leave plans, workflows, holidays, documents, attendance imports, and payroll setup/runs.
- Gaps:
  - Payroll remains partial versus benchmark products: missing broader ESS/compliance flows such as declarations, reimbursement claims, proof workflows, and richer salary governance.
  - Reporting/export capabilities are thin relative to market expectations.
  - Audit timeline is now safer, but still not optimized for actionable troubleshooting or structured filtering/export.

### Employee
- Strengths:
  - Employee has onboarding, profile, attendance, leave, approvals, documents, and payslips surfaces.
- Gaps:
  - ESS maturity is below Zoho Payroll expectations around tax/investment/reimbursement workflows and richer payroll visibility.
  - Attendance capture is not yet at market-standard mobile/geofence/IP-restricted maturity.
  - Several UI descriptions still reference “future payroll” or preview-like behavior, which reduces confidence.

## 4. Architecture Findings
- Positive:
  - Clear app boundaries exist in the backend by domain.
  - Session-based auth, workspace switching, and persona routing are structured coherently.
- Negative:
  - Audit safety had no centralized sanitization layer before this cycle.
  - The same audit response shape was previously used for CT and org-level views without role-specific privacy shaping; the current slice now diverges actor/device masking but still lacks richer CT-specific investigative structure.
  - CT/browser regression coverage had drifted from actual seeded data and current modal patterns, reducing verification reliability.

## 5. Security Findings
- Fixed in this cycle:
  - Sensitive audit payload exposure through CT/org audit APIs.
  - Sensitive values being persisted in audit payload storage for new writes.
  - CT audit views now mask employee actor email, IP, and user-agent details while keeping org-admin troubleshooting visibility.
- Still open:
  - CT operational surfaces remain summary-heavy; support workflows are not yet strongly privacy-scoped by investigative use case.
  - Audit explorer ergonomics are still generic compared with mature support consoles.
  - Broader field-level masking should be reviewed across exports, reports, approval subjects, and future CT drill-down views before production trust.

## 6. UI/UX Findings
- Positive:
  - CT navigation and route segmentation are clear.
  - Dialog-based suspend/restore flows are more intentional than destructive inline actions.
  - CT now has a dedicated onboarding support tab that explains blocker state in a role-appropriate way.
- Negative:
  - Regression coverage had stale assumptions about hard-coded seed counts, default tab visibility, and browser confirm dialogs.
  - Some UI copy still references future-state payroll behavior instead of confidently describing implemented workflows.
  - Search/filter depth is limited compared with benchmark products.

## 7. Functional Correctness Findings
- Verified:
  - Backend regression tests for audit sanitization now pass.
  - CT actor/device masking is covered in backend tests and CT browser regression coverage.
  - CT onboarding blocker support is covered in backend tests and CT browser regression coverage.
  - CT payroll and attendance misconfiguration diagnostics are covered in backend tests and CT browser regression coverage.
  - CT and auth Playwright suites pass after aligning tests with the actual UI behavior.
- Open concerns:
  - Competitive completeness of payroll and attendance workflows remains partial.
  - CT support/debug workflows are not yet sufficiently operational for payroll/attendance incident triage.

## 8. Content Quality Findings
- The app is not dominated by lorem ipsum or fake marketing content.
- There is still feature-forward wording that oversells future payroll/disbursement behavior in employee-facing screens.
- CT descriptions are generally clearer than employee/profile/payroll wording, but still summarize more than they guide.

## 9. Dead / Stale / Unused Code Findings
- Confirmed stale debt in this cycle:
  - `backend/apps/audit/tests/test_views.py` was effectively empty before this remediation.
  - `frontend/e2e/ct/organisations.spec.ts` had stale, brittle assumptions:
    - fixed organisation count
    - hard-coded admin identity
    - obsolete browser confirm-dialog flow
    - ordered side-effect dependence across tests
- No broad dead-route purge was completed in this cycle; that remains an open workstream.

## 10. Feature Gap Analysis vs Market
Already present but partial:
- Org setup
- Employee lifecycle
- Leave workflows
- Holiday calendars
- Approval workflows
- Attendance imports and regularization
- Payroll setup and payslips
- CT support summaries, including onboarding blocker visibility

Clearly behind benchmark:
- Fine-grained access control and service-bound support roles
- Attendance capture maturity: geolocation, IP controls, device/kiosk/mobile depth
- Employee payroll ESS: declarations, proofs, reimbursements, richer salary/tax surfaces
- Reporting and exports
- CT operational diagnostics and reconciliation tooling
- Policy-driven privacy views for audit and support workflows

## 11. Severity Matrix
| Severity | Count | Notes |
|---|---:|---|
| Critical | 2 | Both audit privacy issues were fixed in this cycle |
| High | 6 | 2 fixed this cycle; payroll, attendance, CT diagnostics, and reporting gaps remain open |
| Medium | 4 | 1 fixed this cycle; UX wording, filtering, and audit usability remain open |
| Low | 0 | Not a low-severity product at this stage |

## 12. Detailed Issue List
### HRMS-AUD-001
- Title: Audit timeline exposed raw sensitive payload values to CT and Org Admin views
- Severity: Critical
- Persona affected: CT, Org Admin, Employee
- Area/module: Audit / Security / Privacy
- Evidence: `backend/apps/audit/serializers.py` previously returned raw `payload`; tests added in `backend/apps/audit/tests/test_views.py`
- Why it matters: CT support visibility must not become a backdoor to PAN, Aadhaar, address, or payroll-like values.
- Recommended fix: Centralized audit payload redaction on read plus regression tests.
- Status: Fixed in cycle 1

### HRMS-AUD-002
- Title: Audit writers persisted sensitive PAN/address/payroll-like values in stored payloads
- Severity: Critical
- Persona affected: CT, Org Admin, Employee
- Area/module: Audit / Organisations / Employees
- Evidence: `backend/apps/organisations/services.py` and `backend/apps/employees/services.py` wrote raw payload fields before this cycle
- Why it matters: Stored raw audit data remains dangerous even if UI later changes.
- Recommended fix: Centralized audit payload sanitization on write plus service-level regression tests.
- Status: Fixed in cycle 1

### HRMS-AUD-003
- Title: CT audit visibility is not yet role-shaped for actor/device metadata
- Severity: High
- Persona affected: CT
- Area/module: Audit / CT Support
- Evidence: fixed by role-aware shaping in `backend/apps/audit/serializers.py`, `backend/apps/audit/views.py`, backend regression tests, and CT audit Playwright coverage
- Why it matters: CT needs operational visibility, but not unrestricted personal telemetry.
- Recommended fix: Add CT-specific masking and support filters for actor/device metadata.
- Status: Fixed in cycle 1

### HRMS-AUD-004
- Title: CT support flows lack deep payroll and attendance incident diagnostics
- Severity: High
- Persona affected: CT, Org Admin
- Area/module: CT / Payroll / Attendance
- Evidence: partially remediated with structured diagnostics in `backend/apps/organisations/views.py`, `frontend/src/pages/ct/OrganisationDetailPage.tsx`, backend tests, and CT Playwright coverage; richer reconciliation drill-down is still absent
- Why it matters: Mature HRMS support tooling helps diagnose misconfiguration and run failures quickly.
- Recommended fix: Add run drill-downs, exception categorization, reconciliation views, and admin-facing guidance hooks.
- Status: Partially fixed in cycle 1

### HRMS-AUD-005
- Title: Payroll workflow is materially behind Zoho Payroll ESS and compliance expectations
- Severity: High
- Persona affected: Org Admin, Employee
- Area/module: Payroll / ESS
- Evidence: codebase has payslips and compensation templates, but no full declaration/proof/reimbursement claim workflow
- Why it matters: Near-parity requires more than payroll runs and payslips.
- Recommended fix: Add declarations, investment proofs, claims/reimbursements, and richer employee payroll visibility.
- Status: Open

### HRMS-AUD-006
- Title: Attendance capture maturity is below market standard
- Severity: High
- Persona affected: Employee, Org Admin
- Area/module: Attendance
- Evidence: current implementation centers on imports, self punch APIs, and regularization; benchmark tools support broader mobile/geofence/IP controls
- Why it matters: Attendance integrity and payroll trust depend on stronger capture controls.
- Recommended fix: Add configurable capture restrictions, mobile parity, and clearer shift/clocking policy surfaces.
- Status: Open

### HRMS-AUD-007
- Title: Reporting and export surfaces are not competitive
- Severity: High
- Persona affected: CT, Org Admin
- Area/module: Reporting / Auditability
- Evidence: no report builder, saved reports, structured exports, or benchmark-level analytics surfaces were found
- Why it matters: HR/payroll operators need explainable data, not just summary cards.
- Recommended fix: Add role-safe exports, structured reports, and attendance/payroll analytics views.
- Status: Open

### HRMS-AUD-008
- Title: CT cannot inspect onboarding/document blockers through a privacy-bounded support lens
- Severity: High
- Persona affected: CT
- Area/module: CT / Documents / Onboarding
- Evidence: fixed via `backend/apps/organisations/views.py`, `backend/apps/organisations/urls.py`, `frontend/src/pages/ct/OrganisationDetailPage.tsx`, backend tests, and CT Playwright coverage
- Why it matters: Support teams need to understand operational blockers without opening full employee PII.
- Recommended fix: Add blocker summaries, document state counts, and redacted issue drill-downs.
- Status: Fixed in cycle 1

### HRMS-AUD-009
- Title: CT Playwright coverage had stale assumptions and poor isolation
- Severity: Medium
- Persona affected: Engineering / QA
- Area/module: Testability
- Evidence: `frontend/e2e/ct/organisations.spec.ts`
- Why it matters: Unreliable regression coverage lowers confidence in real changes.
- Recommended fix: Make tests data-tolerant, tab-aware, and modal-aware.
- Status: Fixed in cycle 1

### HRMS-AUD-010
- Title: Audit timeline UX is safe enough to ship this slice, but still not support-optimized
- Severity: Medium
- Persona affected: CT, Org Admin
- Area/module: Audit / UX
- Evidence: raw payload leak is fixed, but timeline still shows a generic payload + metadata stream with limited investigative ergonomics
- Why it matters: Benchmark tools use permissions plus operationally meaningful filters and summaries.
- Recommended fix: add structured filters, actor/type badges, severity grouping, and role-safe detail expansion.
- Status: Open

### HRMS-AUD-011
- Title: Employee/payroll copy still uses future-state wording that weakens trust
- Severity: Medium
- Persona affected: Employee
- Area/module: UX / Content
- Evidence: employee profile/payroll copy references “future payroll disbursement flows” and preview-oriented language
- Why it matters: HR/payroll products must be explicit about what is live vs not live.
- Recommended fix: align copy with current implemented behavior and hide aspirational wording.
- Status: Open

### HRMS-AUD-012
- Title: Search, filtering, and discoverability are shallow across admin support surfaces
- Severity: Medium
- Persona affected: CT, Org Admin
- Area/module: UX / Reporting
- Evidence: CT/org screens mostly use simple text search and status filters with no saved views or advanced filters
- Why it matters: Competitive HRMS tools reduce operational latency through better discovery.
- Recommended fix: add advanced filters, export-aware filtering, and saved views.
- Status: Open

## 13. What Competitors Do Better
- Zoho People exposes stronger permission shaping at the form, field, and action level, including import/export and IP restrictions.
- Zoho Payroll offers broader ESS depth around payslips, salary details, reimbursements, investments, and manager/reportee attendance views.
- Rippling models permissions as scope + access + actions, which is more mature than page-level or persona-only gating.
- BambooHR pairs time tracking with approvals, reminders, geolocation, payroll sync, and stronger reporting narratives.

## 14. What Must Be Fixed Before Production Trust
- Complete CT privacy shaping beyond audit payload redaction.
- Expand payroll workflows beyond template/run/payslip basics.
- Strengthen attendance capture integrity and admin controls.
- Add trustworthy reporting/export and support-grade operational diagnostics.
- Eliminate future-state or misleading wording from employee/payroll UX.

## 15. What Is Nice-to-Have vs Table Stakes
Table stakes:
- Role-safe privacy boundaries
- Payroll and attendance correctness
- ESS for payslips and core self-service
- Reliable approvals
- Reporting/export basics
- Actionable audit trails

Nice-to-have after trust baseline:
- Rich CT diagnostics UX
- Saved report views
- deeper automation/orchestration patterns
- broader mobile/kiosk/device attendance ecosystem

## 16. Overall Audit Score / Readiness Assessment
- Security/privacy: `58/100` after this cycle’s audit fix
- Core HRMS completeness: `52/100`
- Payroll maturity: `41/100`
- Attendance maturity: `44/100`
- CT support/debug maturity: `46/100`
- Reporting/auditability maturity: `48/100`
- UX/content trustworthiness: `55/100`
- Overall readiness: `49/100`

Assessment: not production-trustworthy yet for a serious HR/payroll deployment. Cycle 1 closed a real privacy flaw and repaired regression coverage, but meaningful competitive and trust gaps remain.
