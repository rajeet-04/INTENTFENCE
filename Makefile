UV ?= uv
PYTHON ?= .venv/bin/python
BUN ?= bun

.PHONY: setup setup-backend test-backend test-benchmark lint-backend format-backend setup-frontend test-frontend dev dev-api dev-dashboard phase9-mac-smoke phase10-smoke phase10-live-smoke phase10-cloud-fallback-smoke quick-tunnel verify

setup: setup-backend setup-frontend

setup-backend:
	$(UV) venv --python 3.12 .venv
	$(UV) pip install --python $(PYTHON) -e ./packages/contracts -e ./packages/classification -e ./packages/policy -e ./packages/state -e "./packages/dataflow[dev]" -e "./packages/analytics[dev]" -e "./apps/api[dev]"

test-backend:
	$(PYTHON) -m pytest packages/contracts/tests packages/classification/tests packages/policy/tests packages/state/tests packages/dataflow/tests packages/analytics/tests apps/api/tests -q

test-benchmark:
	$(PYTHON) -m pytest packages/analytics/tests -q

lint-backend:
	$(PYTHON) -m ruff check packages/contracts packages/classification packages/policy packages/state packages/dataflow packages/analytics apps/api

format-backend:
	$(PYTHON) -m ruff format packages/contracts packages/classification packages/policy packages/state packages/dataflow packages/analytics apps/api

setup-frontend:
	cd apps/dashboard && $(BUN) install --frozen-lockfile

test-frontend:
	cd apps/dashboard && $(BUN) test
	cd apps/dashboard && $(BUN) run lint
	cd apps/dashboard && $(BUN) run typecheck
	cd apps/dashboard && $(BUN) run build

dev-api:
	$(PYTHON) -m uvicorn intentfence_api.app:app --app-dir apps/api/src --reload --host 0.0.0.0 --port 8000

dev-dashboard:
	cd apps/dashboard && $(BUN) run dev

dev:
	$(PYTHON) scripts/phase10_dev.py

phase9-mac-smoke:
	$(PYTHON) scripts/phase9_mac_smoke.py

phase10-smoke:
	$(PYTHON) scripts/phase10_release_smoke.py

phase10-live-smoke:
	$(PYTHON) scripts/phase10_release_smoke.py --live

phase10-cloud-fallback-smoke:
	$(PYTHON) scripts/phase10_release_smoke.py --cloud-fallback

quick-tunnel:
	./scripts/phase10_quick_tunnel.sh

verify: lint-backend test-backend test-frontend
