# P01 — Critical Security Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all critical and high-severity security findings from the audit: rotate exposed credentials, enforce strong secret key and encryption key configuration, and add missing input validation to payroll and leave serializers.

**Architecture:** Pure configuration and validation changes — no new models or migrations. Security improvements applied at settings layer (startup-time validation) and serializer layer (request-time validation). TDD throughout: validation tests written before implementation.

**Tech Stack:** Django 4.2 · DRF 3.15 · pytest · factory-boy · git-secrets · BFG Repo-Cleaner

---

## Audit Findings Addressed

| ID | Finding | Severity |
|----|---------|----------|
| S5-01 | AWS + Zeptomail credentials committed in `.env` | 🔴 Critical |
| S5-02 | `SECRET_KEY` insecure placeholder in `settings/base.py` | 🔴 Critical |
| S5-03 | `FIELD_ENCRYPTION_KEY` defaults to empty string | 🟠 High |
| S5-04 | No negative salary validation in payroll serializer | 🟡 Medium |
| S5-05 | No `end_date >= start_date` validation in leave serializer | 🟡 Medium |

---

## File Structure

```
backend/
  clarisal/settings/
    base.py                         MODIFY — remove insecure FIELD_ENCRYPTION_KEY default
    production.py                   MODIFY — add SECRET_KEY + FIELD_ENCRYPTION_KEY startup validation
  apps/
    payroll/
      serializers.py                MODIFY — add validate_monthly_amount
      tests/
        test_serializers.py         CREATE — payroll serializer validation tests
    timeoff/
      serializers.py                MODIFY — add cross-field end_date >= start_date validation
      tests/
        __init__.py                 CREATE
        test_serializers.py         CREATE — leave serializer validation tests
.gitignore                          VERIFY — confirm .env is excluded
.env.example                        MODIFY — scrub real values, document required vars
.pre-commit-config.yaml             CREATE — detect-secrets hook
```

---

## Task 1: Rotate Exposed Credentials (Manual + Automated)

**Files:** `.env`, `.env.example`, `.pre-commit-config.yaml` (new)

This task is procedural and cannot be automated — it requires human action in AWS and Zeptomail consoles.

- [ ] **Step 1: Immediately revoke the exposed AWS Access Key**

  Go to AWS IAM Console → Users → find the user owning `AKIA47KWW5J3E6Z37SAS` → Security credentials → Make inactive → Delete key.

  Create a new access key pair and store ONLY in the deployment environment secrets manager (not in `.env` file in the repo).

  ```bash
  # Verify the key is no longer active (run from any machine with AWS CLI)
  aws iam list-access-keys --user-name <iam-username>
  # Status should be "Inactive" or key should not appear
  ```

- [ ] **Step 2: Revoke the Zeptomail API key**

  Log into Zeptomail console → API keys → revoke the key beginning with `PHtE6r0LF7y6j...`. Generate a new key and store securely.

- [ ] **Step 3: Purge the credentials from git history using BFG Repo-Cleaner**

  ```bash
  # Install BFG (requires Java)
  brew install bfg  # macOS
  # or download from https://rtyley.github.io/bfg-repo-cleaner/

  # Create a file listing secrets to remove
  cat > secrets-to-remove.txt << 'EOF'
  AKIA47KWW5J3E6Z37SAS
  VPwjCEmznSuMSbmvuO9krzx79cKEy2XtwTBvRmWC
  PHtE6r0LF7y6jDN7phhSsfC+EcasYNt7q+plKwFGtdkRAv4HFk1dqd95lja/+RoiVPYXEPGbmtpgt7ib4OuMdDroY29EVGqyqK3sx/VYSPOZsbq6x00fsFwZf0feV4Ppc95i1iDfvtffNA==
  EOF

  # Run BFG to replace secrets in all commits
  bfg --replace-text secrets-to-remove.txt clarisal.git

  # Force-push the cleaned history
  cd clarisal
  git reflog expire --expire=now --all && git gc --prune=now --aggressive
  git push --force --all
  git push --force --tags
  ```

- [ ] **Step 4: Verify `.env` is in `.gitignore`**

  ```bash
  grep -n "^\.env$" .gitignore
  # Expected: shows line number with ".env"
  ```

  If not present, add it:
  ```bash
  echo ".env" >> .gitignore
  git add .gitignore
  git commit -m "fix: ensure .env is gitignored"
  ```

- [ ] **Step 5: Scrub `.env.example` — replace all real values with placeholders**

  Open `.env.example` and ensure every value is a placeholder:
  ```bash
  # .env.example after scrub:
  AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID_HERE
  AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY_HERE
  ZEPTOMAIL_API_KEY=YOUR_ZEPTOMAIL_API_KEY_HERE
  POSTGRES_PASSWORD=choose-a-strong-password
  DATABASE_URL=postgresql://clarisal:<password>@db:5432/clarisal
  REDIS_URL=redis://redis:6379/0
  SECRET_KEY=generate-with-python-c-"from-django.core.utils.crypto-import-get_random_string;-print(get_random_string(50))"
  FIELD_ENCRYPTION_KEY=generate-with-python-c-"from-cryptography.fernet-import-Fernet;-print(Fernet.generate_key().decode())"
  ```

  Commit the change:
  ```bash
  git add .env.example
  git commit -m "fix: scrub real credentials from .env.example"
  ```

- [ ] **Step 6: Install detect-secrets pre-commit hook**

  Create `.pre-commit-config.yaml`:
  ```yaml
  repos:
    - repo: https://github.com/Yelp/detect-secrets
      rev: v1.5.0
      hooks:
        - id: detect-secrets
          args: ['--baseline', '.secrets.baseline']
          exclude: .env.example

    - repo: https://github.com/pre-commit/pre-commit-hooks
      rev: v4.6.0
      hooks:
        - id: no-commit-to-branch
          args: ['--branch', 'main', '--branch', 'master']
        - id: check-merge-conflict
        - id: trailing-whitespace
  ```

  Initialize the baseline (scan current codebase, mark known false positives):
  ```bash
  pip install detect-secrets pre-commit
  detect-secrets scan --exclude-files '\.env$' > .secrets.baseline
  pre-commit install
  git add .pre-commit-config.yaml .secrets.baseline
  git commit -m "chore: add detect-secrets pre-commit hook to prevent credential commits"
  ```

---

## Task 2: Enforce Strong `SECRET_KEY` at Startup

**Files:** `backend/clarisal/settings/production.py`

- [ ] **Step 1: Write the failing test**

  Create `backend/clarisal/tests/test_production_settings.py`:
  ```python
  import pytest
  from django.core.exceptions import ImproperlyConfigured
  from unittest.mock import patch
  import importlib


  def _reload_production_settings(env_overrides):
      """Helper to reload production settings with specific env vars."""
      import os
      with patch.dict(os.environ, env_overrides, clear=False):
          import clarisal.settings.production as prod
          importlib.reload(prod)
      return prod


  def test_insecure_secret_key_raises_improperly_configured():
      with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
          _reload_production_settings({
              'SECRET_KEY': 'django-insecure-dev-key-change-in-production',
              'FIELD_ENCRYPTION_KEY': 'dmFsaWRrZXloZXJlMTIzNDU2Nzg5MDEyMzQ1Njc4OTA=',
              'ALLOWED_HOSTS': 'example.com',
          })


  def test_placeholder_secret_key_raises_improperly_configured():
      with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
          _reload_production_settings({
              'SECRET_KEY': 'your-secret-key-here-change-in-production',
              'FIELD_ENCRYPTION_KEY': 'dmFsaWRrZXloZXJlMTIzNDU2Nzg5MDEyMzQ1Njc4OTA=',
              'ALLOWED_HOSTS': 'example.com',
          })
  ```

  Run:
  ```bash
  cd backend
  pytest clarisal/tests/test_production_settings.py -v
  # Expected: FAIL — ImproperlyConfigured not raised
  ```

- [ ] **Step 2: Implement the validation in `production.py`**

  Open `backend/clarisal/settings/production.py` and add after the existing `SECRET_KEY` line:
  ```python
  from django.core.exceptions import ImproperlyConfigured

  # Validate SECRET_KEY is not a known insecure placeholder
  _INSECURE_KEY_SUBSTRINGS = [
      'insecure',
      'change-in-production',
      'your-secret-key-here',
      'django-insecure',
  ]
  if any(fragment in SECRET_KEY for fragment in _INSECURE_KEY_SUBSTRINGS):
      raise ImproperlyConfigured(
          "SECRET_KEY contains an insecure placeholder value. "
          "Generate a strong key with: python -c \"from django.core.utils.crypto import get_random_string; print(get_random_string(50))\""
      )
  ```

- [ ] **Step 3: Run test to verify it passes**

  ```bash
  cd backend
  pytest clarisal/tests/test_production_settings.py -v
  # Expected: PASS
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/clarisal/settings/production.py backend/clarisal/tests/test_production_settings.py
  git commit -m "fix(security): raise ImproperlyConfigured when SECRET_KEY is insecure placeholder in production"
  ```

---

## Task 3: Enforce `FIELD_ENCRYPTION_KEY` in All Environments

**Files:** `backend/clarisal/settings/base.py`, `backend/apps/common/security.py`

- [ ] **Step 1: Write the failing test**

  Add to `backend/clarisal/tests/test_production_settings.py`:
  ```python
  def test_missing_field_encryption_key_raises_improperly_configured():
      with pytest.raises(ImproperlyConfigured, match="FIELD_ENCRYPTION_KEY"):
          _reload_production_settings({
              'SECRET_KEY': 'a-sufficiently-long-random-secret-key-for-testing-123456',
              'FIELD_ENCRYPTION_KEY': '',  # empty = not configured
              'ALLOWED_HOSTS': 'example.com',
          })
  ```

  Run:
  ```bash
  pytest backend/clarisal/tests/test_production_settings.py::test_missing_field_encryption_key_raises_improperly_configured -v
  # Expected: FAIL
  ```

- [ ] **Step 2: Implement validation in `production.py`**

  Below the SECRET_KEY validation in `production.py`, add:
  ```python
  FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY')  # No default — required in production

  if not FIELD_ENCRYPTION_KEY:
      raise ImproperlyConfigured(
          "FIELD_ENCRYPTION_KEY must be set to a Fernet-compatible base64 key in production. "
          "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
      )
  ```

  In `backend/clarisal/settings/base.py`, change the `FIELD_ENCRYPTION_KEY` line from:
  ```python
  FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', default='')
  ```
  to:
  ```python
  FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', default='')  # Empty only allowed in development
  ```

  In `backend/clarisal/settings/development.py`, add an explicit note:
  ```python
  # SECURITY WARNING: Generate a real key for any non-development environment
  # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  if not FIELD_ENCRYPTION_KEY:
      import warnings
      warnings.warn(
          "FIELD_ENCRYPTION_KEY is not set. Falling back to SECRET_KEY-derived key. "
          "Sensitive fields (PAN, Aadhaar, bank accounts) are NOT strongly encrypted.",
          stacklevel=1,
      )
  ```

- [ ] **Step 3: Run test to verify it passes**

  ```bash
  pytest backend/clarisal/tests/test_production_settings.py -v
  # Expected: all PASS
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/clarisal/settings/production.py backend/clarisal/settings/base.py backend/clarisal/settings/development.py
  git commit -m "fix(security): enforce FIELD_ENCRYPTION_KEY is set in production; warn in development when absent"
  ```

---

## Task 4: Add Negative Amount Validation to Payroll Serializer

**Files:** `backend/apps/payroll/serializers.py`, `backend/apps/payroll/tests/test_serializers.py` (new)

- [ ] **Step 1: Write the failing tests**

  Create `backend/apps/payroll/tests/test_serializers.py`:
  ```python
  import pytest
  from decimal import Decimal
  from apps.payroll.serializers import (
      CompensationTemplateLineSerializer,
      PayrollTaxSlabSerializer,
  )


  @pytest.mark.django_db
  class TestCompensationTemplateLineSerializer:

      def _make_valid_data(self, monthly_amount='50000.00'):
          return {
              'component': None,  # will be mocked in integration tests
              'monthly_amount': monthly_amount,
              'sequence': 1,
          }

      def test_positive_monthly_amount_is_valid(self):
          data = {'monthly_amount': '50000.00', 'sequence': 1}
          serializer = CompensationTemplateLineSerializer(data=data)
          # Only check the monthly_amount field validation
          serializer.is_valid()
          assert 'monthly_amount' not in serializer.errors

      def test_zero_monthly_amount_is_valid(self):
          """Zero is valid for optional components."""
          data = {'monthly_amount': '0.00', 'sequence': 1}
          serializer = CompensationTemplateLineSerializer(data=data)
          serializer.is_valid()
          assert 'monthly_amount' not in serializer.errors

      def test_negative_monthly_amount_is_rejected(self):
          data = {'monthly_amount': '-1000.00', 'sequence': 1}
          serializer = CompensationTemplateLineSerializer(data=data)
          serializer.is_valid()
          assert 'monthly_amount' in serializer.errors
          assert 'negative' in str(serializer.errors['monthly_amount']).lower() or \
                 'greater' in str(serializer.errors['monthly_amount']).lower()

      def test_large_negative_monthly_amount_is_rejected(self):
          data = {'monthly_amount': '-999999.99', 'sequence': 1}
          serializer = CompensationTemplateLineSerializer(data=data)
          serializer.is_valid()
          assert 'monthly_amount' in serializer.errors


  @pytest.mark.django_db
  class TestPayrollTaxSlabSerializer:

      def test_negative_min_income_is_rejected(self):
          data = {'min_income': '-1.00', 'max_income': '300000.00', 'rate_percent': '5.00'}
          serializer = PayrollTaxSlabSerializer(data=data)
          serializer.is_valid()
          assert 'min_income' in serializer.errors

      def test_rate_above_100_is_rejected(self):
          data = {'min_income': '0.00', 'max_income': '300000.00', 'rate_percent': '101.00'}
          serializer = PayrollTaxSlabSerializer(data=data)
          serializer.is_valid()
          assert 'rate_percent' in serializer.errors

      def test_negative_rate_is_rejected(self):
          data = {'min_income': '0.00', 'max_income': '300000.00', 'rate_percent': '-5.00'}
          serializer = PayrollTaxSlabSerializer(data=data)
          serializer.is_valid()
          assert 'rate_percent' in serializer.errors
  ```

  Run:
  ```bash
  cd backend
  pytest apps/payroll/tests/test_serializers.py -v
  # Expected: FAIL — validation not implemented
  ```

- [ ] **Step 2: Add validation to `payroll/serializers.py`**

  Open `backend/apps/payroll/serializers.py`. Find `CompensationTemplateLineSerializer` and add:
  ```python
  def validate_monthly_amount(self, value):
      if value < 0:
          raise serializers.ValidationError(
              "Monthly amount cannot be negative. Use a deduction component type for amounts that reduce pay."
          )
      return value
  ```

  Find `PayrollTaxSlabSerializer` and add:
  ```python
  def validate_min_income(self, value):
      if value < 0:
          raise serializers.ValidationError("Minimum income cannot be negative.")
      return value

  def validate_rate_percent(self, value):
      if value < 0:
          raise serializers.ValidationError("Tax rate cannot be negative.")
      if value > 100:
          raise serializers.ValidationError("Tax rate cannot exceed 100%.")
      return value
  ```

- [ ] **Step 3: Run tests to verify they pass**

  ```bash
  cd backend
  pytest apps/payroll/tests/test_serializers.py -v
  # Expected: all PASS
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/apps/payroll/serializers.py backend/apps/payroll/tests/test_serializers.py
  git commit -m "fix(security): reject negative salary amounts and invalid tax rates in payroll serializers"
  ```

---

## Task 5: Add Date Range Validation to Leave Request Serializer

**Files:** `backend/apps/timeoff/serializers.py`, `backend/apps/timeoff/tests/test_serializers.py` (new)

- [ ] **Step 1: Create tests directory and write failing tests**

  ```bash
  mkdir -p backend/apps/timeoff/tests
  touch backend/apps/timeoff/tests/__init__.py
  ```

  Create `backend/apps/timeoff/tests/test_serializers.py`:
  ```python
  import pytest
  from datetime import date, timedelta
  from apps.timeoff.serializers import LeaveRequestCreateSerializer


  @pytest.mark.django_db
  class TestLeaveRequestCreateSerializer:

      def _base_data(self, start_date=None, end_date=None):
          today = date.today()
          return {
              'leave_type': None,  # FK — tested in integration tests
              'start_date': (start_date or today).isoformat(),
              'end_date': (end_date or today).isoformat(),
              'start_session': 'FULL_DAY',
              'end_session': 'FULL_DAY',
              'reason': 'Medical leave',
          }

      def test_same_day_leave_is_valid(self):
          today = date.today()
          data = self._base_data(start_date=today, end_date=today)
          serializer = LeaveRequestCreateSerializer(data=data)
          serializer.is_valid()
          assert 'end_date' not in serializer.errors
          assert 'non_field_errors' not in serializer.errors

      def test_multi_day_leave_is_valid(self):
          today = date.today()
          data = self._base_data(start_date=today, end_date=today + timedelta(days=3))
          serializer = LeaveRequestCreateSerializer(data=data)
          serializer.is_valid()
          assert 'end_date' not in serializer.errors

      def test_end_date_before_start_date_is_rejected(self):
          today = date.today()
          data = self._base_data(
              start_date=today + timedelta(days=2),
              end_date=today,  # end before start
          )
          serializer = LeaveRequestCreateSerializer(data=data)
          serializer.is_valid()
          assert 'end_date' in serializer.errors or 'non_field_errors' in serializer.errors

      def test_end_date_one_day_before_start_date_is_rejected(self):
          today = date.today()
          data = self._base_data(
              start_date=today,
              end_date=today - timedelta(days=1),
          )
          serializer = LeaveRequestCreateSerializer(data=data)
          serializer.is_valid()
          assert 'end_date' in serializer.errors or 'non_field_errors' in serializer.errors
  ```

  Run:
  ```bash
  cd backend
  pytest apps/timeoff/tests/test_serializers.py -v
  # Expected: FAIL — validation not implemented
  ```

- [ ] **Step 2: Add cross-field validation to `timeoff/serializers.py`**

  Open `backend/apps/timeoff/serializers.py`. Find `LeaveRequestCreateSerializer` and add the `validate` method:
  ```python
  def validate(self, data):
      start_date = data.get('start_date')
      end_date = data.get('end_date')
      if start_date and end_date and end_date < start_date:
          raise serializers.ValidationError({
              'end_date': 'End date must be on or after the start date.'
          })
      return data
  ```

- [ ] **Step 3: Run tests to verify they pass**

  ```bash
  cd backend
  pytest apps/timeoff/tests/test_serializers.py -v
  # Expected: all PASS
  ```

- [ ] **Step 4: Run the full backend test suite to confirm no regressions**

  ```bash
  cd backend
  pytest --tb=short -q
  # Expected: all existing tests pass, new tests pass
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add backend/apps/timeoff/serializers.py backend/apps/timeoff/tests/
  git commit -m "fix(security): validate leave end_date >= start_date in serializer; add serializer test suite"
  ```

---

## Task 6: Final Security Checklist

- [ ] **Step 1: Confirm all exposed credentials are rotated**

  ```bash
  # Check AWS key is inactive
  aws iam list-access-keys --user-name <username> | grep Status
  # Expected: "Inactive" or key not found
  ```

- [ ] **Step 2: Confirm `.env` is not tracked by git**

  ```bash
  git ls-files .env
  # Expected: no output (empty)
  ```

- [ ] **Step 3: Run detect-secrets on entire repo**

  ```bash
  detect-secrets scan --exclude-files '\.env$|\.secrets\.baseline$'
  # Expected: no new secrets found outside .secrets.baseline
  ```

- [ ] **Step 4: Run the full backend test suite**

  ```bash
  cd backend
  pytest --tb=short -q
  # Expected: all tests pass
  ```

- [ ] **Step 5: Final commit**

  ```bash
  git add -A
  git commit -m "chore(security): P01 complete — credentials rotated, startup validation added, serializer guards in place"
  ```

---

## Verification

Run the full security check suite:

```bash
# 1. All new tests pass
cd backend && pytest apps/payroll/tests/test_serializers.py apps/timeoff/tests/test_serializers.py clarisal/tests/ -v

# 2. detect-secrets finds no new credentials
detect-secrets scan --exclude-files '\.env$' | python -c "import sys,json; d=json.load(sys.stdin); print('Clean' if not any(d['results'].values()) else 'SECRETS FOUND')"

# 3. pre-commit passes on all files
pre-commit run --all-files
```

Expected output: all green, no secrets detected.
