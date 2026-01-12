# MTT - Container Terminal Management System

A full-stack application for managing container terminal operations, vehicle tracking, and customer pre-orders.

## Documentation

- **[Architecture Documentation](docs/ARCHITECTURE.md)** - System diagrams, business flows, and technical overview

## Project Structure

```
mtt-combined/
├── backend/          # Django REST API
│   ├── apps/         # Django applications
│   ├── terminal_app/ # Django settings
│   └── telegram_bot/ # Telegram bot integration
├── frontend/         # Vue 3 + TypeScript SPA
│   └── src/          # Vue source code
├── docker-compose.yml
└── Makefile
```

## Tech Stack

### Backend
- **Framework:** Django 5.2 + Django REST Framework
- **Database:** PostgreSQL (production) / SQLite (development)
- **Authentication:** JWT (SimpleJWT)
- **API Documentation:** OpenAPI (Swagger/ReDoc)

### Frontend
- **Framework:** Vue 3 + TypeScript
- **UI Library:** Ant Design Vue 4.x
- **Build Tool:** Vite
- **State Management:** Vue Composition API

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional, for containerized setup)
- PostgreSQL 15+ (optional, SQLite works for development)

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and navigate to project
cd mtt-combined

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Start all services
docker-compose up --build

# Or use Makefile
make prod
```

Services will be available at:
- Frontend: http://localhost:1001
- Backend API: http://localhost:8000/api
- API Docs: http://localhost:8000/api/docs

### Option 2: Local Development

```bash
# Install all dependencies
make install

# Start both services (in separate terminals or use make dev)
make dev

# Or start separately:
make backend   # Terminal 1: Django on port 8000
make frontend  # Terminal 2: Vue on port 5174
```

### Option 3: Manual Setup

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm ci

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

## Available Commands

Run `make help` to see all available commands:

| Command | Description |
|---------|-------------|
| `make dev` | Start both backend and frontend locally |
| `make dev-docker` | Start all services with Docker (development mode) |
| `make prod` | Start all services with Docker (production) |
| `make install` | Install all dependencies |
| `make migrate` | Run Django migrations |
| `make test` | Run backend tests |
| `make logs` | View Docker logs |
| `make down` | Stop Docker services |

## API Endpoints

Base URL: `http://localhost:8000/api`

### Authentication
- `POST /auth/login/` - Login
- `POST /auth/logout/` - Logout
- `POST /auth/token/refresh/` - Refresh JWT token
- `GET /auth/profile/` - Get current user profile

### Container Operations
- `GET /terminal/entries/` - List container entries
- `POST /terminal/entries/` - Create container entry
- `GET /terminal/owners/` - List container owners

### Vehicles
- `GET /vehicles/entries/` - List vehicle entries
- `POST /vehicles/entries/` - Create vehicle entry

### Documentation
- `GET /api/docs/` - Swagger UI
- `GET /api/redoc/` - ReDoc
- `GET /api/schema/` - OpenAPI Schema

## Environment Variables

### Backend (`backend/.env`)
```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost:5432/mtt
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Frontend (`frontend/.env`)
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## User Types

1. **Admin** - Full system access, manages users and settings
2. **Manager** - Terminal operations, vehicle/container tracking
3. **Customer** - Portal access for their company's containers and pre-orders

## Development

### Running Tests
```bash
# Backend tests
make test-backend
# or
cd backend && pytest -v
```

### Code Quality
```bash
make lint
```

### Database Migrations
```bash
# Create new migrations after model changes
make makemigrations

# Apply migrations
make migrate
```

## Deployment

### Docker Production
```bash
# Build and start in detached mode
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Production
1. Set `DEBUG=False` in backend `.env`
2. Generate a strong `SECRET_KEY`
3. Configure PostgreSQL database
4. Run `python manage.py collectstatic`
5. Use Gunicorn for backend: `gunicorn terminal_app.wsgi:application`
6. Build frontend: `npm run build`
7. Serve frontend with nginx or similar

## License

Private/Proprietary
