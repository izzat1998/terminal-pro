.PHONY: help dev backend frontend telegram-miniapp mediamtx anpr test-anpr \
        migrate makemigrations test test-backend lint clean install shell

# Use bash for better compatibility with complex commands
SHELL := /bin/bash
.DEFAULT_GOAL := help

# Backend venv binaries - avoids need for 'source activate'
BACKEND_PYTHON := backend/.venv/bin/python
BACKEND_PIP := backend/.venv/bin/pip
BACKEND_PYTEST := backend/.venv/bin/pytest

# macOS: WeasyPrint needs Homebrew C libraries (pango, glib, cairo)
export DYLD_FALLBACK_LIBRARY_PATH := /opt/homebrew/lib

# Default target
help:
	@echo "MTT Combined Project - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install           - Install all dependencies (backend + frontend + telegram-miniapp)"
	@echo "  make dev               - Start all services locally (backend, frontend, telegram-miniapp)"
	@echo "  make backend           - Start only Django backend (port 8008)"
	@echo "  make frontend          - Start only Vue frontend (port 5174)"
	@echo "  make telegram-miniapp  - Start only Telegram Mini App (port 5175)"
	@echo "  make mediamtx          - Start RTSP→WebRTC camera proxy"
	@echo "  make anpr              - Start ANPR event listener (Hikvision camera)"
	@echo "  make test-anpr         - Test ANPR pipeline with capture loop (every 10s)"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      - Run Django migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make shell        - Open Django shell"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test         - Run all tests"
	@echo "  make test-backend - Run backend tests only"
	@echo "  make lint         - Run linters"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove build artifacts and caches"

# Install dependencies
install:
	@echo "Setting up backend virtual environment..."
	@if [ ! -d "backend/.venv" ]; then \
		cd backend && python3 -m venv .venv; \
	fi
	@echo "Installing backend dependencies..."
	$(BACKEND_PIP) install -r backend/requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm ci
	@echo "Installing telegram-miniapp dependencies..."
	cd telegram-miniapp && npm ci
	@echo "Done!"

# Local development (no Docker)
dev:
	@echo "Starting all services..."
	@$(MAKE) -j3 backend frontend telegram-miniapp

backend:
	$(BACKEND_PYTHON) backend/manage.py runserver 0.0.0.0:8008

frontend:
	cd frontend && npm run dev

telegram-miniapp:
	cd telegram-miniapp && npm run dev

# Gate camera stream proxy (RTSP → WebRTC via mediamtx)
mediamtx:
	mediamtx ./mediamtx.yml

# Gate camera ANPR event listener (Hikvision plate detection)
anpr:
	$(BACKEND_PYTHON) backend/manage.py listen_anpr

# Test ANPR pipeline with capture loop (every 10s)
test-anpr:
	PYTHONUNBUFFERED=1 $(BACKEND_PYTHON) backend/manage.py test_capture_loop

# Database management
migrate:
	$(BACKEND_PYTHON) backend/manage.py migrate

makemigrations:
	$(BACKEND_PYTHON) backend/manage.py makemigrations

shell:
	$(BACKEND_PYTHON) backend/manage.py shell

# Testing
test: test-backend

test-backend:
	cd backend && .venv/bin/pytest -v

# Linting - now properly shows errors
lint:
	@echo "=== Linting backend ==="
	cd backend && .venv/bin/python -m ruff check apps/ || .venv/bin/python -m flake8 apps/ --max-line-length=120
	@echo ""
	@echo "=== Linting frontend ==="
	cd frontend && npm run lint --if-present
	@echo ""
	@echo "=== Linting telegram-miniapp ==="
	cd telegram-miniapp && npm run lint

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done!"
