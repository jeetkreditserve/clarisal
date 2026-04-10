.PHONY: install migrate shell test coverage lint typecheck frontend-install frontend-test frontend-test-coverage seed e2e e2e-headed check

DC = docker compose
BACKEND = backend
FRONTEND = frontend
BACKEND_DIR = /app
FRONTEND_DIR = /app
BACKEND_ENV = export HOME=/tmp PYTHONPATH=/tmp/.local/lib/python3.11/site-packages PATH=/tmp/.local/bin:$$PATH RUFF_CACHE_DIR=/tmp/.ruff_cache MYPY_CACHE_DIR=/tmp/.mypy_cache
MANAGE = python manage.py

install:
	$(DC) exec backend /bin/sh -lc "$(BACKEND_ENV) && cd $(BACKEND_DIR) && python -m pip install -r requirements.txt -r requirements-dev.txt"

migrate:
	$(DC) exec backend /bin/sh -lc "cd $(BACKEND_DIR) && $(MANAGE) migrate"

shell:
	$(DC) exec backend /bin/sh -lc "cd $(BACKEND_DIR) && $(MANAGE) shell"

test:
	$(DC) exec backend /bin/sh -lc "cd $(BACKEND_DIR) && python -m pytest -v"

coverage:
	$(DC) exec backend /bin/sh -lc "$(BACKEND_ENV) COVERAGE_FILE=/tmp/.coverage && cd $(BACKEND_DIR) && python -m pytest --cov=apps --cov-report=term-missing --cov-report=html --cov-fail-under=80"
	@echo "Coverage report: backend/htmlcov/index.html"

lint:
	$(DC) exec backend /bin/sh -lc "$(BACKEND_ENV) && cd $(BACKEND_DIR) && ruff check apps/"
	$(DC) exec backend /bin/sh -lc "$(BACKEND_ENV) && cd $(BACKEND_DIR) && bandit -r apps/ -c pyproject.toml"

typecheck:
	$(DC) exec backend /bin/sh -lc "$(BACKEND_ENV) && cd $(BACKEND_DIR) && python -m mypy apps/ --ignore-missing-imports"

frontend-install:
	$(DC) exec frontend sh -lc "cd $(FRONTEND_DIR) && npm install"

frontend-test:
	$(DC) exec frontend sh -lc "cd $(FRONTEND_DIR) && npx vitest run"

frontend-test-coverage:
	$(DC) exec frontend sh -lc "cd $(FRONTEND_DIR) && npx vitest run --coverage"

seed:
	$(DC) exec backend /bin/sh -lc "cd $(BACKEND_DIR) && $(MANAGE) seed_control_tower"

e2e: seed
	$(DC) exec frontend sh -lc "cd $(FRONTEND_DIR) && npx playwright test"

e2e-headed:
	$(DC) exec frontend sh -lc "cd $(FRONTEND_DIR) && npx playwright test --headed"

check: lint typecheck test
	@echo "All checks passed"
