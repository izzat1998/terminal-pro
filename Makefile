.PHONY: help dev dev-docker prod backend frontend telegram-miniapp migrate makemigrations test lint clean install logs shell

# Default target
help:
	@echo "MTT Combined Project - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install           - Install all dependencies (backend + frontend + telegram-miniapp)"
	@echo "  make dev               - Start all services locally (backend, frontend, telegram-miniapp)"
	@echo "  make backend           - Start only Django backend (port 8000)"
	@echo "  make frontend          - Start only Vue frontend (port 5174)"
	@echo "  make telegram-miniapp  - Start only Telegram Mini App (port 5175)"
	@echo ""
	@echo "Docker:"
	@echo "  make dev-docker   - Start all services with Docker (dev mode)"
	@echo "  make prod         - Start all services with Docker (production)"
	@echo "  make logs         - View Docker logs"
	@echo "  make down         - Stop all Docker services"
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
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm ci
	@echo "Installing telegram-miniapp dependencies..."
	cd telegram-miniapp && npm ci
	@echo "Done!"

# Local development (no Docker)
dev:
	@echo "Starting all services..."
	@make -j3 backend frontend telegram-miniapp

backend:
	cd backend && source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000

frontend:
	cd frontend && npm run dev

telegram-miniapp:
	cd telegram-miniapp && npm run dev

# Docker development
dev-docker:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Docker production
prod:
	docker-compose up --build -d

# Docker utilities
logs:
	docker-compose logs -f

down:
	docker-compose down

# Database management
migrate:
	cd backend && source .venv/bin/activate && python manage.py migrate

makemigrations:
	cd backend && source .venv/bin/activate && python manage.py makemigrations

shell:
	cd backend && source .venv/bin/activate && python manage.py shell

# Testing
test: test-backend

test-backend:
	cd backend && source .venv/bin/activate && pytest -v

# Linting
lint:
	cd backend && source .venv/bin/activate && python -m flake8 apps/ --max-line-length=120 || true
	cd frontend && npm run lint 2>/dev/null || true
	cd telegram-miniapp && npm run lint 2>/dev/null || true

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done!"
