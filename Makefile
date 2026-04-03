.PHONY: install migrate shell test coverage lint typecheck frontend-install frontend-test frontend-test-coverage e2e e2e-headed check

BACKEND = backend
FRONTEND = frontend
MANAGE = python manage.py

install:
	cd $(BACKEND) && python -m pip install -r requirements.txt -r requirements-dev.txt

migrate:
	cd $(BACKEND) && $(MANAGE) migrate

shell:
	cd $(BACKEND) && $(MANAGE) shell

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

frontend-install:
	cd $(FRONTEND) && npm install

frontend-test:
	cd $(FRONTEND) && npx vitest run

frontend-test-coverage:
	cd $(FRONTEND) && npx vitest run --coverage

e2e:
	cd $(FRONTEND) && npx playwright test

e2e-headed:
	cd $(FRONTEND) && npx playwright test --headed

check: lint typecheck test
	@echo "All checks passed"
