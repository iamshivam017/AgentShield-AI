SHELL := /bin/bash
PYTHON := services/api/.venv/bin/python
PIP := services/api/.venv/bin/pip

.PHONY: setup dev lint typecheck test e2e build benchmark migrate docs security api web verify

setup:
	python3 -m venv services/api/.venv
	$(PIP) install -e 'services/api[dev]'
	cd apps/web && npm install

dev:
	@echo "Run 'make api' and 'make web' in separate terminals"

api:
	cd services/api && .venv/bin/uvicorn app.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

lint:
	cd services/api && .venv/bin/ruff check app tests
	cd apps/web && npm run lint

typecheck:
	cd services/api && .venv/bin/mypy app
	cd apps/web && npm run typecheck

test:
	cd services/api && .venv/bin/pytest --cov=app --cov-fail-under=70 -q
	cd apps/web && npm test -- --run

e2e:
	cd apps/web && npm run e2e

build:
	cd apps/web && npm run build
	cd services/api && .venv/bin/python -m compileall -q app

benchmark:
	cd services/api && .venv/bin/python -m app.ml.benchmark --output ../../docs/benchmark-results.json

migrate:
	cd services/api && .venv/bin/alembic upgrade head

docs:
	python3 scripts/check_docs.py

security:
	bash scripts/secret_scan.sh
	cd apps/web && npm audit --omit=dev --audit-level=high

verify: docs security lint typecheck test build benchmark
