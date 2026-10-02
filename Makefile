# AegisMesh Foundation Makefile

.PHONY: test backend frontend install dev

install:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm install

test:
	python -m pytest backend/tests

backend:
	python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build
