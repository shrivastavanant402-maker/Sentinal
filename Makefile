# AegisMesh Foundation Makefile

.PHONY: test backend frontend install dev

install:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm install

test:
	python -m pytest backend/tests

backend:
	python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting AegisMesh/Sentinel Backend (:8000) and Frontend (:5173)..."
	@python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 & \
	BACKEND_PID=$$!; \
	trap 'kill $$BACKEND_PID 2>/dev/null' EXIT INT TERM; \
	cd frontend && npm run dev

build:
	cd frontend && npm run build

