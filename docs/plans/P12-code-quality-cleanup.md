# P12 — Code Quality & Cleanup

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure JWT authentication alongside session auth, fix the skipped E2E test, add pre-commit security hooks, configure mypy and ruff, add coverage enforcement, and create a Makefile for developer convenience.

**Architecture:** All changes are configuration and tooling — no new features. JWT uses `djangorestframework-simplejwt` (already installed). Pre-commit hooks prevent future regressions. Coverage config enforces ≥80% on all business logic apps.

**Tech Stack:** Django 4.2 · DRF · simplejwt · ruff · mypy · bandit · detect-secrets · pytest-cov · Playwright

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/clarisal/settings/base.py` | Modify | Add JWT to DRF auth classes, configure simplejwt |
| `backend/apps/accounts/urls.py` | Modify | Add JWT token + refresh endpoints |
| `backend/pytest.ini` | Modify/Create | Configure coverage targets ≥80% |
| `backend/.coveragerc` | Create | Coverage exclusion rules |
| `frontend/e2e/employee/leave.spec.ts` | Modify | Remove test.skip(), implement date picker interaction |
| `.pre-commit-config.yaml` | Create | bandit, detect-secrets, ruff, end-of-file-fixer |
| `Makefile` | Create | make test, coverage, lint, typecheck targets |
| `CONTRIBUTING.md` | Create | Document service/repository/view pattern |
| `backend/requirements-dev.txt` | Create | Dev-only dependencies |

---

## Task 1 — Configure JWT Authentication

**Files:**
- Modify: `backend/clarisal/settings/base.py`
- Modify: `backend/apps/accounts/urls.py`

### Background

`djangorestframework-simplejwt` is already in `requirements.txt` but not configured. Adding it alongside `SessionAuthentication` allows API clients (mobile apps, external integrations) to authenticate via JWT tokens without breaking the existing session-based frontend.

- [x] **Step 1: Write a failing test**

Create `backend/apps/accounts/tests/test_jwt.py`:

```python
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.tests.factories import UserFactory


class TestJWTEndpoints(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()

    def test_obtain_token_returns_access_and_refresh(self):
        response = self.client.post('/api/auth/token/', {
            'email': self.user.email,
            'password': 'testpass123',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_refresh_token_returns_new_access(self):
        obtain = self.client.post('/api/auth/token/', {
            'email': self.user.email,
            'password': 'testpass123',
        }, format='json')
        refresh_token = obtain.data['refresh']
        response = self.client.post('/api/auth/token/refresh/', {
            'refresh': refresh_token,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_protected_endpoint_accepts_jwt(self):
        obtain = self.client.post('/api/auth/token/', {
            'email': self.user.email,
            'password': 'testpass123',
        }, format='json')
        access_token = obtain.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        # Use a protected endpoint that requires auth
        response = self.client.get('/api/me/employees/profile/')
        # Should not be 401/403 due to auth failure (may be other errors)
        self.assertNotEqual(response.status_code, 401)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest apps/accounts/tests/test_jwt.py -v
```

Expected: FAIL — URL not found.

- [x] **Step 3: Update DRF settings in `backend/clarisal/settings/base.py`**

Find the `REST_FRAMEWORK` dict. Update `DEFAULT_AUTHENTICATION_CLASSES`:

```python
REST_FRAMEWORK = {
    # ... existing settings ...
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    # ... rest unchanged ...
}
```

Add `SIMPLE_JWT` configuration below `REST_FRAMEWORK`:

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    # Use email as username for token generation
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}
```

Add `'rest_framework_simplejwt.token_blacklist'` to `INSTALLED_APPS` (under `THIRD_PARTY_APPS`).

- [x] **Step 4: Create a custom token serializer that accepts email**

Create `backend/apps/accounts/jwt_serializers.py`:

```python
# backend/apps/accounts/jwt_serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Override default simplejwt serializer to use email + password."""
    username_field = 'email'

    def validate(self, attrs):
        credentials = {
            'email': attrs.get('email'),
            'password': attrs.get('password'),
        }
        user = authenticate(**credentials)
        if user is None or not user.is_active:
            raise serializers.ValidationError('Invalid email or password.')
        attrs[self.username_field] = getattr(user, User.USERNAME_FIELD)
        return super().validate(attrs)
```

- [x] **Step 5: Add JWT URL endpoints to `accounts/urls.py`**

Open `backend/apps/accounts/urls.py`. Add:

```python
from rest_framework_simplejwt.views import TokenRefreshView
from .jwt_views import EmailTokenObtainPairView  # created below

# Add to urlpatterns:
path('token/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
```

Create `backend/apps/accounts/jwt_views.py`:

```python
from rest_framework_simplejwt.views import TokenObtainPairView
from .jwt_serializers import EmailTokenObtainPairSerializer


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
```

- [x] **Step 6: Generate and apply token blacklist migration**

```bash
cd backend && python manage.py makemigrations token_blacklist --check || python manage.py migrate
```

- [x] **Step 7: Run tests**

```bash
cd backend && python -m pytest apps/accounts/tests/test_jwt.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/clarisal/settings/base.py \
        backend/apps/accounts/urls.py \
        backend/apps/accounts/jwt_serializers.py \
        backend/apps/accounts/jwt_views.py \
        backend/apps/accounts/tests/test_jwt.py
git commit -m "feat(auth): add JWT authentication alongside session auth, email-based token endpoint"
```

---

## Task 2 — Fix Skipped E2E Test (`leave.spec.ts`)

**Files:**
- Modify: `frontend/e2e/employee/leave.spec.ts`

### Background

The `leave.spec.ts` test file contains `test.skip()` calls due to date picker interaction being unimplemented. The date picker is likely an `<input type="date">` or a custom `AppDatePicker` using Radix.

- [x] **Step 1: Read the current test file**

```bash
cat frontend/e2e/employee/leave.spec.ts
```

Note all `test.skip` occurrences and what they were trying to test.

- [x] **Step 2: Identify the date picker component in LeavePage**

```bash
grep -n "DatePicker\|type=\"date\"\|date-input" frontend/src/pages/employee/LeavePage.tsx | head -10
```

Note the component name and how dates are set (native input vs. custom picker).

- [x] **Step 3: Implement the date picker interaction**

Replace each `test.skip(...)` with a working `test(...)`. For a native `<input type="date">`:

```typescript
// Replace:
test.skip('employee can apply for leave with date range', async ({ page }) => { ... });

// With:
test('employee can apply for leave with date range', async ({ page }) => {
  await loginAsEmployee(page);
  await page.goto('/employee/leave');
  await page.getByRole('button', { name: /apply for leave/i }).click();

  // For native date inputs:
  await page.getByLabel(/start date/i).fill('2024-05-01');
  await page.getByLabel(/end date/i).fill('2024-05-03');

  // For AppDatePicker (Radix-based custom picker):
  // await page.getByTestId('start-date-picker').click();
  // await page.getByText('1').first().click(); // day 1 of displayed month

  await page.getByLabel(/leave type/i).selectOption({ index: 1 });
  await page.getByRole('button', { name: /submit/i }).click();
  await expect(page.getByText(/request submitted/i)).toBeVisible({ timeout: 5000 });
});
```

For a custom date picker (if `AppDatePicker` is used), identify its test ID via:
```bash
grep -n "data-testid\|testId" frontend/src/components/ui/AppDatePicker.tsx
```

Use the appropriate Playwright selector.

- [x] **Step 4: Run the previously-skipped tests**

```bash
cd frontend && npx playwright test e2e/employee/leave.spec.ts --headed
```

Expected: All tests RUN (no skips) and PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/e2e/employee/leave.spec.ts
git commit -m "fix(e2e): implement date picker interaction, remove test.skip from leave.spec.ts"
```

---

## Task 3 — Pre-commit Security Hooks

**Files:**
- Create: `.pre-commit-config.yaml`
- Create/Modify: `.gitignore` (add detect-secrets baseline)

- [x] **Step 1: Install pre-commit**

```bash
pip install pre-commit
# or
cd backend && pip install pre-commit
```

- [x] **Step 2: Create `.pre-commit-config.yaml`**

Create at the repository root:

```yaml
# .pre-commit-config.yaml
repos:
  # General
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=2048']
      - id: no-commit-to-branch
        args: ['--branch', 'master', '--branch', 'main']

  # Python linting with ruff
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: ['--fix', '--exit-non-zero-on-fix']
        files: ^backend/

  # Python security scanning
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.7
    hooks:
      - id: bandit
        args: ['-c', 'backend/pyproject.toml']
        files: ^backend/apps/

  # Secret detection
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: '^(backend/apps/.*/migrations/|.*\.lock$|\.env\.example$)'
```

- [x] **Step 3: Create `ruff` configuration**

Create `backend/pyproject.toml` if it does not exist (or add to existing):

```toml
[tool.ruff]
line-length = 120
target-version = "py311"
exclude = [
    "*/migrations/*",
    "*/tests/*",
]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B904",  # raise from within except
]

[tool.bandit]
exclude_dirs = ["tests", "migrations"]
skips = ["B101"]  # assert statements in tests
```

- [x] **Step 4: Generate detect-secrets baseline**

```bash
cd /home/jeet-padhya/PycharmProjects/clarisal
pip install detect-secrets
detect-secrets scan \
  --exclude-files '.*\.lock$' \
  --exclude-files '.*/migrations/.*' \
  --exclude-files '\.env\.example$' \
  > .secrets.baseline
```

- [x] **Step 5: Install hooks**

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

- [x] **Step 6: Run hooks on all files to check baseline**

```bash
pre-commit run --all-files
```

Fix any issues flagged by ruff or bandit. Common fixes:
- `bare except:` → `except Exception:`
- Remove unused imports
- Fix `B006` mutable default args

- [ ] **Step 7: Commit**

```bash
git add .pre-commit-config.yaml .secrets.baseline backend/pyproject.toml
git commit -m "chore: add pre-commit hooks for ruff linting, bandit security scan, detect-secrets"
```

---

## Task 4 — Configure Coverage Enforcement

**Files:**
- Modify/Create: `backend/pytest.ini`
- Modify/Create: `backend/.coveragerc`

- [x] **Step 1: Update `backend/pytest.ini`**

If `pytest.ini` exists, open and update. If not, create:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = clarisal.settings.test
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --tb=short
    --cov=apps
    --cov-report=term-missing
    --cov-fail-under=80
```

- [x] **Step 2: Create `.coveragerc`**

```ini
# backend/.coveragerc
[run]
source = apps
omit =
    */migrations/*
    */tests/*
    */test_*.py
    */__init__.py
    */apps.py
    */admin.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:
    pass

[html]
directory = htmlcov
```

- [x] **Step 3: Add `pytest-cov` to dev requirements**

Create `backend/requirements-dev.txt` if it does not exist:

```
pytest>=7.0
pytest-django
pytest-cov
factory-boy
faker
Faker
```

Install:
```bash
cd backend && pip install -r requirements-dev.txt
```

- [x] **Step 4: Run coverage and verify it passes 80%**

```bash
cd backend && python -m pytest --cov=apps --cov-report=term-missing --cov-fail-under=80
```

If it fails below 80%, identify the lowest-covered modules and add tests for them (inline with this task or note them for follow-up).

- [ ] **Step 5: Commit**

```bash
git add backend/pytest.ini backend/.coveragerc backend/requirements-dev.txt
git commit -m "chore(test): configure coverage enforcement ≥80% via pytest-cov"
```

---

## Task 5 — Mypy Type Checking

**Files:**
- Create: `backend/mypy.ini`
- Modify: `backend/requirements-dev.txt`

- [x] **Step 1: Add mypy to dev requirements**

Add to `backend/requirements-dev.txt`:
```
mypy
django-stubs[compatible-mypy]
djangorestframework-stubs
```

Install:
```bash
cd backend && pip install mypy django-stubs djangorestframework-stubs
```

- [x] **Step 2: Create `backend/mypy.ini`**

```ini
[mypy]
plugins = mypy_django_plugin.main

[mypy.plugins.django-stubs]
django_settings_module = clarisal.settings.base

[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
ignore_missing_imports = True
exclude = migrations

[mypy-apps.*.migrations.*]
ignore_errors = True
```

- [x] **Step 3: Run mypy and note errors**

```bash
cd backend && python -m mypy apps/ --ignore-missing-imports 2>&1 | head -50
```

- [x] **Step 4: Fix critical mypy errors**

Fix `error:` level issues in new code (services, models). Ignore existing legacy type errors by adding `# type: ignore` where fixing would be too invasive. Do not add type annotations to functions you didn't write.

- [ ] **Step 5: Commit**

```bash
git add backend/mypy.ini backend/requirements-dev.txt
git commit -m "chore: add mypy configuration for Django type checking"
```

---

## Task 6 — Makefile for Developer Convenience

**Files:**
- Create: `Makefile`

- [x] **Step 1: Create `Makefile` at repo root**

```makefile
# Makefile — Clarisal HRMS developer targets
.PHONY: test coverage lint typecheck frontend-test e2e install migrate shell

# Python paths
BACKEND = backend
MANAGE = python manage.py

## Backend

install:
	cd $(BACKEND) && pip install -r requirements.txt -r requirements-dev.txt

migrate:
	cd $(BACKEND) && $(MANAGE) migrate

shell:
	cd $(BACKEND) && $(MANAGE) shell_plus

test:
	cd $(BACKEND) && python -m pytest -v

coverage:
	cd $(BACKEND) && python -m pytest --cov=apps --cov-report=term-missing --cov-report=html --cov-fail-under=80
	@echo "Coverage report: backend/htmlcov/index.html"

lint:
	cd $(BACKEND) && ruff check apps/ --fix
	cd $(BACKEND) && bandit -r apps/ -c pyproject.toml

typecheck:
	cd $(BACKEND) && python -m mypy apps/ --ignore-missing-imports

## Frontend

frontend-install:
	cd frontend && npm install

frontend-test:
	cd frontend && npx vitest run

frontend-test-coverage:
	cd frontend && npx vitest run --coverage

e2e:
	cd frontend && npx playwright test

e2e-headed:
	cd frontend && npx playwright test --headed

## Combined

check: lint typecheck test
	@echo "All checks passed"
```

- [x] **Step 2: Verify Makefile targets work**

```bash
make lint
# Expected: ruff and bandit run without crashing

make test
# Expected: tests run (may fail if DB not set up — that's OK)
```

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: add Makefile with test, coverage, lint, typecheck, e2e targets"
```

---

## Task 7 — CONTRIBUTING.md

**Files:**
- Create: `CONTRIBUTING.md`

- [x] **Step 1: Create `CONTRIBUTING.md`**

```markdown
# Contributing to Clarisal HRMS

## Architecture Pattern

All backend logic follows a strict **Service → Repository → View** pattern:

### Views (`views.py`)
- Thin — only HTTP concerns: request parsing, permission checks, serialization, response
- Never contain business logic or direct ORM calls
- Call service functions only

### Services (`services.py`)
- All business logic lives here
- Functions are pure-ish Python (no HTTP concepts)
- Call repository functions for data access
- Raise `ValueError` for business rule violations (views catch and return 400)

### Repositories (`repositories.py`)
- All ORM queries live here
- Return model instances or Python primitives
- No business logic — just data retrieval

### Example Flow

```
POST /api/org/payroll/runs/{id}/calculate/
  → OrgPayrollRunCalculateView.post()
    → validate permissions
    → call calculate_pay_run_task.delay(pay_run_id, user_id)  # service layer
      → calculate_pay_run(pay_run, actor)  # service
        → PayrollRunItem.objects.filter(...)  # repository layer (or repositories.py)
    → return 202
```

## TDD Workflow

Every change follows TDD:
1. Write a failing test
2. Run it and confirm it fails
3. Write the minimal implementation
4. Run it and confirm it passes
5. Commit

## Running Tests

```bash
make test          # run all backend tests
make coverage      # run with coverage report (≥80% required)
make frontend-test # run Vitest unit tests
make e2e           # run Playwright E2E tests
```

## Linting & Type Checking

```bash
make lint       # ruff + bandit
make typecheck  # mypy
```

## Commit Message Format

`type(scope): description`

Types: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`, `perf`

Examples:
- `feat(payroll): add 87A rebate calculation`
- `fix(leave): enforce carry-forward cap on cycle end`
- `test(attendance): add daily calculation unit tests`
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING.md documenting service/repository/view architecture"
```

---

## Task 8 — Final Cleanup Pass

- [x] **Step 1: Remove any remaining dead code**

Search for unused imports:
```bash
cd backend && ruff check apps/ --select F401 --fix
```

Search for `TODO` comments that can be resolved:
```bash
grep -rn "TODO\|FIXME\|HACK\|XXX" backend/apps/ --include="*.py" | grep -v "migrations" | head -20
```

Address any low-hanging TODO items (remove, implement, or convert to GitHub issues).

- [-] **Step 2: Ensure all new apps have migrations**

```bash
cd backend && python manage.py makemigrations --check
```

Expected: `No changes detected` (all migrations already generated).

- [x] **Step 3: Run full test suite one final time**

```bash
cd backend && python -m pytest -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass. Coverage ≥ 80%.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup — remove dead code, fix TODOs, verify all migrations present"
```

---

## Verification Checklist

```bash
# 1. JWT works
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass"}' | python -m json.tool
# Expected: {"access": "...", "refresh": "..."}

# 2. No test.skip remaining
grep -rn "test.skip" frontend/e2e/
# Expected: zero results

# 3. Pre-commit hooks installed
cat .git/hooks/pre-commit | head -3
# Expected: pre-commit hook content

# 4. Coverage ≥ 80%
cd backend && python -m pytest --cov=apps --cov-fail-under=80 -q
# Expected: PASSED

# 5. Lint passes
make lint
# Expected: no exit-non-zero errors

# 6. All 12 plan files exist
ls docs/plans/P*.md | wc -l
# Expected: 12
```
