# Poseidon Maritime Security System

A comprehensive maritime security system for vessel tracking, AIS data processing, and security zone monitoring.

## Dashboard

![Poseidon Dashboard](dashboard.png)

## Core Capabilities

- **Real-time vessel tracking** with AIS data ingestion
- **Security zone monitoring** with geofenced areas
- **Risk assessment** and automated alerting
- **Collision detection** using CPA/TCPA calculations
- **Traffic simulation** for development and training

## Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.109.0 | Web framework |
| SQLAlchemy | 2.0.25 | ORM (async) |
| GeoAlchemy2 | 0.14.3 | PostGIS integration |
| Celery | 5.3.6 | Task queue |
| python-socketio | 5.11.0 | WebSocket support |
| pyais | 2.6.0 | AIS message parsing |
| Alembic | 1.13.1 | Database migrations |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2.0 | UI framework |
| TypeScript | 5.3.3 | Type safety |
| Vite | 5.0.12 | Build tool |
| React Query | 5.17.19 | Data fetching |
| Zustand | 4.5.0 | State management |
| Mapbox GL | 3.1.2 | Map rendering |
| Tailwind CSS | 3.4.1 | Styling |

### Infrastructure
| Technology | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 16 | Relational database |
| PostGIS | 3.4 | Geospatial extension |
| Redis | 7 | Cache & message broker |
| Docker Compose | 3.8 | Service orchestration |

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

### Health & Status
- `GET /health` - Health check with database/redis status
- `GET /status` - Detailed system status with AIS statistics

### Vessels
- `GET /api/v1/vessels` - List vessels (supports `bbox`, `vessel_type`, `limit`, `offset`)
- `GET /api/v1/vessels/{mmsi}` - Get vessel by MMSI
- `GET /api/v1/vessels/{mmsi}/track` - Get vessel track history as GeoJSON

### Security Zones
- `GET /api/v1/zones` - List zones as GeoJSON (supports `zone_type`, `security_level`)
- `GET /api/v1/zones/{zone_id}` - Get zone by ID

### Alerts
- `GET /api/v1/alerts` - List alerts (supports `status`, `severity`, `alert_type`, `hours`)

### AIS Sources
- `GET /api/v1/ais-sources/status` - Get AIS data source status
- `POST /api/v1/ais-sources/switch` - Switch active data source
- `GET /api/v1/ais-sources/emulator/scenarios` - List available scenarios
- `POST /api/v1/ais-sources/emulator/load-scenario/{name}` - Load a scenario

Full API documentation available at http://localhost:8000/docs when running.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | development/staging/production | development |
| `DEBUG` | Enable debug mode | true |
| `SECRET_KEY` | Secret key for signing | - |
| `DATABASE_URL` | PostgreSQL connection string | postgresql://poseidon:poseidon@postgres:5432/poseidon |
| `REDIS_URL` | Redis connection string | redis://redis:6379/0 |
| `CELERY_BROKER_URL` | Celery broker URL | redis://redis:6379/1 |
| `CELERY_RESULT_BACKEND` | Celery result backend | redis://redis:6379/2 |
| `MAPBOX_TOKEN` | Mapbox access token (required) | - |
| `API_HOST` | Backend host | 0.0.0.0 |
| `API_PORT` | Backend port | 8000 |
| `CORS_ORIGINS` | Allowed CORS origins | http://localhost:3000 |
| `LOG_LEVEL` | Logging level | INFO |

## Traffic Scenarios

The system includes a traffic emulator with predefined scenarios for development and testing:

| Scenario | Description |
|----------|-------------|
| `thessaloniki_normal_traffic` | Normal port operations with typical vessel traffic |
| `collision_threat` | Vessels on collision course for CPA/TCPA testing |
| `ais_gap_dark_vessel` | AIS signal gaps and dark vessel detection |
| `loitering_suspicious` | Suspicious loitering behavior patterns |
| `zone_violation` | Security zone entry/exit violations |

Load scenarios via API:
```bash
curl -X POST http://localhost:8000/api/v1/ais-sources/emulator/load-scenario/thessaloniki_normal_traffic
```

## Documentation

Detailed documentation is available in the `docs/` folder:

- [Architecture](docs/architecture.md) - System architecture and data flow
- [Database](docs/database.md) - Database schema and PostGIS configuration
- [Backend API](docs/backend-api.md) - Complete API reference
- [Frontend](docs/frontend.md) - React components and state management
- [AIS Architecture](docs/ais-architecture.md) - AIS adapter pattern and emulator design

## License

Proprietary - All rights reserved
