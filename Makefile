.PHONY: setup-backend test-backend lint-backend format-backend setup-frontend test-frontend dev-api dev-dashboard verify

setup-backend:
	python -m pip install -e ./packages/contracts -e ./packages/dataflow -e "./apps/api[dev]" -e "./packages/analytics[dev]"

test-backend:
	python -m pytest packages/contracts/tests packages/dataflow/tests apps/api/tests packages/analytics/tests -q

lint-backend:
	python -m ruff check packages/contracts packages/dataflow apps/api packages/analytics

format-backend:
	python -m ruff format packages/contracts packages/dataflow apps/api packages/analytics

setup-frontend:
	npm --prefix apps/dashboard install

test-frontend:
	npm --prefix apps/dashboard run lint
	npm --prefix apps/dashboard run typecheck
	npm --prefix apps/dashboard run build

dev-api:
	uvicorn intentfence_api.app:app --app-dir apps/api/src --reload --host 0.0.0.0 --port 8000

dev-dashboard:
	npm --prefix apps/dashboard run dev

verify: lint-backend test-backend test-frontend
