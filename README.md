# Poseidon Maritime Security System

A comprehensive maritime security system for vessel tracking, AIS data processing, and security zone monitoring.

## Dashboard

![Poseidon Dashboard](dashboard.png)

## Tech Stack

### Backend
- Python 3.11+ with FastAPI
- SQLAlchemy 2.0 + GeoAlchemy2
- Celery + Redis for task processing
- Socket.IO for real-time updates
- pyais for AIS data decoding

### Frontend
- React 18 with TypeScript
- Vite 5 for fast development
- Mapbox GL JS for mapping
- TanStack Query for data fetching
- Zustand for state management
- Tailwind CSS for styling

### Infrastructure
- PostgreSQL 16 + PostGIS 3.4 + TimescaleDB
- Redis 7
- Docker Compose for orchestration

## Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Mapbox account and access token

## Quick Start

1. **Clone and configure**
   ```bash
   cd poseidon-mss
   cp .env.example .env
   # Edit .env and add your MAPBOX_TOKEN
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Services

| Service | Port | Description |
|---------|------|-------------|
| frontend | 3000 | React application |
| backend | 8000 | FastAPI REST API |
| postgres | 5432 | PostgreSQL + PostGIS + TimescaleDB |
| redis | 6379 | Redis cache and message broker |
| celery-worker | - | Background task processor |
| celery-beat | - | Scheduled task scheduler |

## Project Structure

```
poseidon-mss/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # SQLAlchemy models
│   │   ├── database/     # Database configuration
│   │   ├── ais/          # AIS data processing
│   │   ├── emulator/     # AIS scenario emulation
│   │   └── tasks/        # Celery tasks
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── hooks/        # Custom hooks
│   │   ├── stores/       # Zustand stores
│   │   ├── lib/          # Utilities
│   │   └── types/        # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── scenarios/            # YAML scenario files
├── docker/
│   └── postgres/
│       └── init.sql      # Database initialization
├── docker-compose.yml
└── .env.example
```

## Development

### Backend Development

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
poetry run pytest

# Frontend type checking
cd frontend
npm run type-check
```

## API Endpoints

- `GET /health` - Health check
- `GET /api/v1/vessels` - List all vessels
- `GET /api/v1/vessels/{mmsi}` - Get vessel by MMSI
- `GET /api/v1/zones` - List security zones
- `GET /api/v1/alerts` - List alerts

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://poseidon:poseidon@postgres:5432/poseidon |
| REDIS_URL | Redis connection string | redis://redis:6379/0 |
| MAPBOX_TOKEN | Mapbox access token | - |
| ENVIRONMENT | development/staging/production | development |
| DEBUG | Enable debug mode | true |

## License

Proprietary - All rights reserved
