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

- [ ] Extend `BiometricDevice` with vendor, product family, middleware mode, and capability flags instead of overloading protocol alone.
- [ ] Create a vendor registry mapping devices to supported transport, auth, and payload normalization strategies.
- [ ] Record which vendors are natively supported and which are supported through shared transport families such as ADMS or push-data middleware.

## Task 2: Add Missing High-Priority Vendor Adapters

- [ ] Implement adapters or compatibility bridges for Mantra and CP PLUS where current `P09` protocols are insufficient.
- [ ] Where vendor products already conform to ADMS, eBioserver, Matrix, Hikvision, or Suprema families, add explicit compatibility fixtures instead of copy-pasting handlers.
- [ ] Support middleware/export ingestion paths for deployments that cannot push directly into the platform.

## Task 3: Add Real-Time Attendance Event Streaming

- [ ] Normalize device punch ingestion into a publishable internal attendance event.
- [ ] Add an ASGI event transport for live punch and device-health updates.
- [ ] Stream real-time events to org-admin diagnostics screens and optionally to employee status surfaces where appropriate.

## Task 4: Build a Compatibility Test Lab

- [ ] Add golden payload fixtures for every supported vendor/product family.
- [ ] Add simulator or replay tests for push, pull, duplicate, offline-recovery, and unknown-employee scenarios.
- [ ] Produce a compatibility matrix document or fixture manifest showing which vendor families are certified by automated tests.

## Task 5: Upgrade Device Operations UX

- [ ] Update the biometric device page to show vendor family, connectivity mode, last successful sync, current failure state, and live event previews.
- [ ] Add health diagnostics and a manual replay/sync action for admins.
- [ ] Make webhook/pull credentials, secrets, and bridge URLs explicit without exposing raw secrets after creation.

## Task 6: Cleanup and Verification

- [ ] Remove stale device assumptions that each protocol implies a single vendor family.
- [ ] Cover new adapters, registry logic, and live-stream behavior with automated tests.
- [ ] Verify that live streaming degrades safely when Redis/event transport is unavailable.
