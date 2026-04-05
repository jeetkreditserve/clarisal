# Contributing to Clarisal HRMS

## Architecture Pattern

The backend is moving toward a strict Service -> Repository -> View split.

### Views (`views.py`)

- Keep them thin.
- Handle request parsing, permissions, serialization, and HTTP response shaping.
- Delegate business rules to services.

### Services (`services.py`)

- Keep business logic here.
- Avoid HTTP concepts in service functions.
- Raise `ValueError` for business rule violations so views can turn them into `400` responses.

### Repositories (`repositories.py`)

- Keep ORM-heavy access paths here when a module has enough query complexity to justify it.
- Return model instances or simple Python structures.
- Avoid embedding business rules in repository helpers.

## Expected Workflow

1. Write a failing test or otherwise create a reproducible failure.
2. Confirm it fails for the expected reason.
3. Implement the smallest coherent fix.
4. Re-run focused verification, then broader verification when the change is stable.

## Running Checks

```bash
make test
make coverage
make frontend-test
make e2e
make lint
make typecheck
```

## Commit Messages

Use `type(scope): description`.

Examples:

- `feat(payroll): add 87A rebate calculation`
- `fix(leave): enforce carry-forward caps`
- `chore(auth): add JWT endpoints`
