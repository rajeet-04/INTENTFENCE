.PHONY: setup-backend test-backend lint-backend format-backend setup-frontend test-frontend dev-api dev-dashboard verify

setup-backend:
	python -m pip install -e ./packages/contracts -e ./packages/classification -e ./packages/policy -e ./packages/state -e ./packages/dataflow -e "./apps/api[dev]"

test-backend:
	python -m pytest packages/contracts/tests packages/classification/tests packages/policy/tests packages/state/tests packages/dataflow/tests apps/api/tests -q

lint-backend:
	python -m ruff check packages/contracts packages/classification packages/policy packages/state packages/dataflow apps/api

format-backend:
	python -m ruff format packages/contracts packages/classification packages/policy packages/state packages/dataflow apps/api

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
