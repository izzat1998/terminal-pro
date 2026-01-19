# CLAUDE.md - MTT Container Terminal Management System

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Navigation

This is a monorepo with backend and two frontend codebases. Each has its own detailed CLAUDE.md:

| Area | Path | Technology |
|------|------|------------|
| Backend API | `backend/CLAUDE.md` | Django 5.2 + DRF |
| Frontend SPA | `frontend/CLAUDE.md` | Vue 3 + TypeScript |
| Telegram Mini App | `telegram-miniapp/CLAUDE.md` | React 18 + TypeScript |

**Always check the relevant CLAUDE.md file before making changes to that area.**

## Project Overview

Full-stack container terminal management system for:
- Container entry/exit tracking with status management (laden/empty)
- Vehicle gate operations with pre-order matching
- Multi-role access: admin (API), manager (Telegram bot), customer (web portal)
- Telegram bot integration for on-site operations

## Monorepo Commands

```bash
# Start all services (recommended for development)
make dev

# Start with Docker (production-like)
make prod

# Individual services
make backend           # Django on port 8008
make frontend          # Vue on port 5174
make telegram-miniapp  # React Telegram Mini App on port 5175

# Testing
make test        # Run all tests
pytest backend/  # Backend only

# Database
make migrate         # Apply migrations
make makemigrations  # Create migrations
```

## Critical Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Production orchestration (PostgreSQL, Redis, backend, frontends) |
| `docker-compose.dev.yml` | Development overrides |
| `Makefile` | Development automation commands |
| `backend/terminal_app/settings.py` | Django configuration (DB, auth, CORS) |
| `frontend/vite.config.ts` | Vue frontend build configuration |
| `telegram-miniapp/vite.config.ts` | Telegram Mini App build configuration |
| `.env.example` | Environment variable template |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontends                            │
├─────────────────────────────┬───────────────────────────────┤
│   Vue 3 SPA (Admin/Customer)│  React Telegram Mini App       │
│   localhost:5174 (dev)      │  localhost:5175 (dev)          │
│   localhost:1001 (prod)     │  localhost:1002 (prod)         │
└─────────────────────────────┴───────────────────────────────┘
                          │ HTTP/REST
┌─────────────────────────▼───────────────────────────────────┐
│                    Backend (Django DRF)                      │
│                     localhost:8008/api                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Service Layer (apps/*/services/)                     │   │
│  │  - All business logic here                            │   │
│  │  - Views are thin orchestration                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│  PostgreSQL (prod) / SQLite (dev)  │  Redis (Telegram FSM)  │
└─────────────────────────────────────────────────────────────┘
```

## Commit Conventions

Use conventional commits for clear history:

| Prefix | Use For |
|--------|---------|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes |
| `refactor:` | Code restructuring without behavior change |
| `test:` | Adding or updating tests |
| `chore:` | Build, config, dependency updates |

Examples:
- `feat: add container export to Excel`
- `fix: correct JWT refresh token rotation`
- `docs: update API endpoint documentation`

## User Types

| Type | Access Method | Capabilities |
|------|--------------|--------------|
| Admin | API (username/password) | Full system access, user management |
| Manager | Telegram bot (phone) | Container/vehicle operations at terminal |
| Customer | Web portal + Telegram (username/password) | View containers, manage pre-orders |

## Environment Setup

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```

2. Required variables:
   ```env
   SECRET_KEY=your-secure-secret-key
   DEBUG=True
   VITE_API_BASE_URL=http://localhost:8008/api
   ```

3. Optional (for full features):
   ```env
   DATABASE_URL=postgresql://user:pass@localhost:5432/mtt
   TELEGRAM_BOT_TOKEN=your-bot-token
   PLATE_RECOGNIZER_API_KEY=your-api-key
   ```

## AI Assistant Guidelines

### Cross-Cutting Concerns

**DO:**
- Check both CLAUDE.md files when changes span frontend and backend
- Use `make` commands for common operations
- Follow existing patterns in each codebase
- Keep API contracts consistent between frontend and backend

**NEVER:**
- Modify docker-compose.yml without understanding all services
- Change environment variable names without updating both frontend and backend
- Skip testing after cross-cutting changes
- Commit secrets or credentials

### When Working on Backend
Read `backend/CLAUDE.md` for:
- Service layer pattern (business logic in services, not views)
- Custom exception handling
- API response format
- Testing patterns

### When Working on Frontend
Read `frontend/CLAUDE.md` for:
- Vue 3 Composition API patterns
- TypeScript strict mode requirements
- Ant Design Vue component usage
- API service integration

### When Working on Telegram Mini App
Read `telegram-miniapp/CLAUDE.md` for:
- React 18 + TypeScript patterns
- Telegram Mini Apps SDK usage
- antd-mobile component library
- Camera/plate recognition features

## Quick Debug

| Issue | Check |
|-------|-------|
| Backend won't start | `python manage.py check` in backend/ |
| Frontend build fails | `npm run build` shows TypeScript errors |
| API connection refused | Backend running? Check `localhost:8008/api/docs` |
| Docker issues | `docker-compose logs -f` for details |
| Migration errors | `python manage.py showmigrations` |
