# P19 — Biometric Market Coverage & Live Attendance Feed

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `P09` from protocol support into market-ready coverage for the biometric vendors most visible in India, and add a real-time attendance event feed for device diagnostics and operational visibility.

**Architecture:** Keep the protocol abstraction introduced by `P09`, but add a second layer for vendor/product-family compatibility so multiple Indian-market vendors can map onto shared transports where possible. Introduce a real-time event stream only after attendance-domain events are normalized by `P18`.

**Tech Stack:** Django 4.2 · DRF · Celery · Redis · ASGI/Channels or equivalent event transport · React 19 · TypeScript

---

## Audit Findings Addressed

- Biometric device real-time feed missing
- Attendance integration breadth needs to cover market-leading biometric vendors in India
- Device diagnostics and compatibility evidence are not yet strong enough for a follow-up audit

---

## Vendor Coverage Targets

This plan should explicitly certify support paths for:

- eSSL attendance and eBioserver / push-data device families
- ZKTeco ADMS / ZKBio time-attendance device families
- Matrix COSEC time-attendance product line
- Hikvision time-attendance terminals
- Suprema BioStar 2 time-attendance deployments
- Mantra attendance and AEBAS-linked attendance deployments
- CP PLUS time-attendance terminals

Vendor priority is based on current official vendor positioning and product presence in India. Where a vendor can be supported through an already-implemented protocol family, the task is to certify and fixture that compatibility rather than duplicate protocol code.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/biometrics/models.py` | Modify | Add vendor/product-family metadata and capability flags |
| `backend/apps/biometrics/services.py` | Modify | Compatibility orchestration and device health |
| `backend/apps/biometrics/protocols/mantra.py` | Create | Mantra/Minop or AEBAS bridge adapter |
| `backend/apps/biometrics/protocols/cpplus.py` | Create | CP PLUS adapter or export-bridge handler |
| `backend/apps/biometrics/protocols/vendor_registry.py` | Create | Vendor capability registry |
| `backend/apps/biometrics/tests/test_protocols.py` | Modify | Vendor fixture coverage |
| `backend/apps/biometrics/tests/test_tasks.py` | Modify | Sync and health coverage |
| `backend/apps/attendance/services.py` | Modify | Publish normalized live punch events |
| `backend/clarisal/asgi.py` | Modify | Real-time transport entry point |
| `backend/clarisal/routing.py` | Create | WebSocket/SSE routing |
| `frontend/src/pages/org/BiometricDevicesPage.tsx` | Modify | Vendor setup, health, and live feed UX |
| `frontend/src/components/ui/LiveAttendanceFeed.tsx` | Create | Real-time feed component |
| `frontend/src/lib/api/org-admin.ts` | Modify | Device diagnostics and live-feed APIs |

---

## Task 1: Normalize Vendor Coverage on Top of Protocol Coverage

- [x] Extend `BiometricDevice` with vendor, product family, middleware mode, and capability flags instead of overloading protocol alone.
- [x] Create a vendor registry mapping devices to supported transport, auth, and payload normalization strategies.

## Task 6: Mobile Punch-In and GPS Geo-Fencing

> **Audit v3 finding (Gap #28, §2 Feature Matrix):** No mobile punch-in or location-based attendance exists. Darwinbox has a mobile app with GPS punch-in. This is a Medium-priority gap for field/remote workforces.

- [x] Add a `MobileAttendancePunch` model capturing employee, timestamp, latitude, longitude, accuracy, punch type (IN/OUT), and device fingerprint.
- [x] Add a `GeoFencePolicy` model per `Location` with centre coordinates, allowed radius (metres), and enforcement mode (WARN / BLOCK).
- [x] Add a self-service API endpoint for submitting a mobile punch; validate coordinates against the employee's assigned location geo-fence.
- [x] Return a clear error if the punch is outside the allowed radius when enforcement mode is BLOCK; log a warning when in WARN mode.
- [x] Reflect mobile punches in the attendance day summary alongside biometric punches — they share the same daily resolution logic.
- [x] Add org-admin UI in `BiometricDevicesPage.tsx` (or a new `GeoFencePoliciesPage.tsx`) to configure geo-fence radius per location.
- [x] Cover geo-fence distance calculation, punch validation, and day-summary merging with unit and API tests.
- [x] Record which vendors are natively supported and which are supported through shared transport families such as ADMS or push-data middleware.

## Task 2: Add Missing High-Priority Vendor Adapters

- [x] Implement adapters or compatibility bridges for Mantra and CP PLUS where current `P09` protocols are insufficient.
- [x] Where vendor products already conform to ADMS, eBioserver, Matrix, Hikvision, or Suprema families, add explicit compatibility fixtures instead of copy-pasting handlers.
- [x] Support middleware/export ingestion paths for deployments that cannot push directly into the platform.

## Task 3: Add Real-Time Attendance Event Streaming

- [x] Normalize device punch ingestion into a publishable internal attendance event.
- [x] Add an ASGI event transport for live punch and device-health updates.
- [x] Stream real-time events to org-admin diagnostics screens and optionally to employee status surfaces where appropriate.

## Task 4: Build a Compatibility Test Lab

- [x] Add golden payload fixtures for every supported vendor/product family.
- [x] Add simulator or replay tests for push, pull, duplicate, offline-recovery, and unknown-employee scenarios.
- [x] Produce a compatibility matrix document or fixture manifest showing which vendor families are certified by automated tests.

## Task 5: Upgrade Device Operations UX

- [x] Update the biometric device page to show vendor family, connectivity mode, last successful sync, current failure state, and live event previews.
- [x] Add health diagnostics and a manual replay/sync action for admins.
- [x] Make webhook/pull credentials, secrets, and bridge URLs explicit without exposing raw secrets after creation.

## Task 6: Cleanup and Verification

- [x] Remove stale device assumptions that each protocol implies a single vendor family.
- [x] Cover new adapters, registry logic, and live-stream behavior with automated tests.
- [x] Verify that live streaming degrades safely when Redis/event transport is unavailable.

## Task 7: Stabilization Follow-up

- [x] Align frontend biometric types and API helpers with the current backend response shape so Docker builds pass again.
- [x] Re-verify geo-fence and mobile-punch correctness against the attendance day resolution path instead of trusting checklist completion.
- [x] Confirm the new attendance and biometrics migrations fully cover the in-flight schema changes before declaring the feature complete.
- [x] Add or finish regression coverage for health diagnostics and live-feed degradation paths if any gaps remain during stabilization.

---

## Implementation Notes

- **Vendor Registry:** `backend/apps/biometrics/protocols/vendor_registry.py` provides a central registry of 7 vendors (ZKTeco, eSSL, Matrix, HikVision, Suprema, Mantra, CP PLUS) with protocol mappings and compatibility information.
- **Real-Time Events:** `backend/apps/biometrics/events.py` provides Redis-based event publishing; `backend/apps/biometrics/event_stream.py` provides SSE endpoints for live feeds.
- **Geo-Fencing:** `GeoFencePolicy` model supports WARN and BLOCK enforcement modes with configurable radius per location.
- **Tests:** 30 biometrics tests pass, 7 attendance day summary tests pass.
