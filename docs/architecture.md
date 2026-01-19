# Poseidon Maritime Security System - Architecture Documentation

**Version:** 0.1.0
**Generated:** January 2026
**Status:** As-Built Documentation

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Technology Stack](#technology-stack)
4. [Docker Services](#docker-services)
5. [Network Architecture](#network-architecture)
6. [Data Flow](#data-flow)
7. [Directory Structure](#directory-structure)

---

## System Overview

The Poseidon Maritime Security System (MSS) is a real-time vessel tracking and maritime domain awareness platform designed for port security operations. The system ingests AIS (Automatic Identification System) data, processes vessel movements, detects security events, and provides an interactive map-based interface for operators.

### Core Capabilities

- **Real-time vessel tracking** with AIS data ingestion
- **Security zone monitoring** with geofenced areas
- **Risk assessment** and automated alerting
- **Collision detection** using CPA/TCPA calculations
- **Traffic simulation** for development and training

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "External Data Sources"
        AIS[AIS Data Feeds]
        EMU[Traffic Emulator]
    end

    subgraph "Frontend Layer"
        UI[React SPA<br/>Port 3000]
    end

    subgraph "Backend Layer"
        API[FastAPI<br/>Port 8000]
        CW[Celery Worker]
        CB[Celery Beat]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL<br/>+ PostGIS<br/>Port 5432)]
        RD[(Redis<br/>Port 6379)]
    end

    AIS --> API
    EMU --> API
    UI --> API
    UI -.-> |WebSocket| API
    API --> PG
    API --> RD
    CW --> PG
    CW --> RD
    CB --> CW
    RD --> CW
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Frontend (React)** | Interactive map UI, vessel visualization, alert management |
| **Backend (FastAPI)** | REST API, AIS processing, WebSocket connections |
| **Celery Worker** | Background tasks: AIS ingestion, risk scoring, collision detection |
| **Celery Beat** | Task scheduling for periodic operations |
| **PostgreSQL/PostGIS** | Persistent storage with geospatial queries |
| **Redis** | Message broker, task queue, position caching, Socket.IO pub/sub (DB 3) |

---

## Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.109.0 | Web framework |
| SQLAlchemy | 2.0.25 | ORM (async) |
| AsyncPG | 0.29.0 | PostgreSQL async driver |
| GeoAlchemy2 | 0.14.3 | PostGIS integration |
| Celery | 5.3.6 | Task queue |
| Redis | 5.0.1 | Cache & broker |
| python-socketio | 5.11.0 | WebSocket support |
| pyais | 2.6.0 | AIS message parsing |
| Pydantic | 2.1.0+ | Configuration & validation |
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
| Axios | 1.6.7 | HTTP client |
| Socket.IO Client | 4.7.4 | Real-time updates |

### Database

| Technology | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 16 | Relational database |
| PostGIS | 3.4 | Geospatial extension |
| uuid-ossp | - | UUID generation |
| pg_trgm | - | Text similarity |

### Infrastructure

| Technology | Version | Purpose |
|------------|---------|---------|
| Docker | - | Containerization |
| Docker Compose | 3.8 | Service orchestration |
| Poetry | 1.7.1 | Python dependency management |
| npm | - | Node.js package management |

---

## Docker Services

### Service Configuration

```mermaid
graph LR
    subgraph "Docker Network: poseidon-network"
        FE[frontend:3000]
        BE[backend:8000]
        CW[celery-worker]
        CB[celery-beat]
        PG[postgres:5432]
        RD[redis:6379]
    end

    FE --> BE
    BE --> PG
    BE --> RD
    CW --> PG
    CW --> RD
    CB --> RD
```

### Service Details

| Service | Image | Port | Resources | Health Check |
|---------|-------|------|-----------|--------------|
| **postgres** | postgis/postgis:16-3.4 | 5432 | - | `pg_isready` |
| **redis** | redis:7-alpine | 6379 | - | `redis-cli ping` |
| **backend** | Custom (Python 3.11-slim) | 8000 | - | HTTP /health |
| **frontend** | Custom (Node 20-alpine) | 3000 | - | wget localhost:3000 |
| **celery-worker** | Custom (backend image) | - | Concurrency: 4 | - |
| **celery-beat** | Custom (backend image) | - | - | - |

### Docker Compose Structure

```yaml
# Key service configurations from docker-compose.yml

services:
  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: poseidon
      POSTGRES_USER: poseidon
      POSTGRES_PASSWORD: poseidon
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker -l INFO -Q default,ais,alerts

  celery-beat:
    build: ./backend
    command: celery -A app.celery_app beat -l INFO
```

### Volume Configuration

| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `postgres_data` | /var/lib/postgresql/data | Persistent database storage |
| `redis_data` | /data | Redis persistence (AOF) |

---

## Network Architecture

### Port Mappings

| Service | Internal Port | External Port | Protocol |
|---------|---------------|---------------|----------|
| Frontend | 3000 | 3000 | HTTP |
| Backend | 8000 | 8000 | HTTP/WS |
| PostgreSQL | 5432 | 5432 | TCP |
| Redis | 6379 | 6379 | TCP |

### Internal Service Communication

All services communicate over the Docker bridge network `poseidon-network`:

```
frontend → backend:8000       (HTTP/REST API)
frontend → backend:8000       (WebSocket/Socket.IO)
backend → postgres:5432       (PostgreSQL)
backend → redis:6379          (Cache)
celery-worker → postgres:5432 (PostgreSQL)
celery-worker → redis:6379    (Broker/Result)
celery-beat → redis:6379      (Scheduler)
```

### CORS Configuration

The backend is configured to accept requests from:
- `http://localhost:3000` (development)
- `http://127.0.0.1:3000` (development)
- Additional origins via `CORS_ORIGINS` environment variable

---

## Data Flow

### AIS Data Ingestion Flow

```mermaid
sequenceDiagram
    participant Source as AIS Source/Emulator
    participant Worker as Celery Worker
    participant Proc as AIS Processor
    participant DB as PostgreSQL
    participant Cache as Redis
    participant API as FastAPI
    participant UI as Frontend

    Note over Worker: Every 60 seconds (scheduled)
    Worker->>Source: fetch_data(bbox)
    Source-->>Worker: AISMessage[]
    Worker->>Proc: process_batch(messages)
    Proc->>DB: upsert_vessel()
    Proc->>DB: store_position()
    Proc->>Cache: cache_position()
    UI->>API: GET /vessels
    API->>DB: Query vessels
    DB-->>API: Vessel data
    API-->>UI: JSON response
    UI->>UI: Update map
```

### Alert Generation Flow

```mermaid
sequenceDiagram
    participant Worker as Celery Worker
    participant CD as Collision Detector
    participant DB as PostgreSQL
    participant API as FastAPI
    participant UI as Frontend

    Note over Worker: Every 30 seconds
    Worker->>CD: detect_collisions()
    CD->>DB: Query recent positions
    DB-->>CD: VesselPosition[]
    CD->>CD: Calculate CPA/TCPA
    alt Collision Risk Detected
        CD->>DB: Create RiskAlert
        DB-->>CD: Alert created
    end
    UI->>API: GET /alerts
    API->>DB: Query alerts
    DB-->>API: Alert[]
    API-->>UI: JSON response
```

### Real-Time Update Flow (WebSocket)

```mermaid
sequenceDiagram
    participant Worker as Celery Worker
    participant Redis as Redis (DB 3)
    participant API as FastAPI + Socket.IO
    participant UI as Frontend

    Note over Worker,UI: Vessel Position Update
    Worker->>Worker: Process AIS message
    Worker->>Redis: emit_vessel_update() via Redis pub/sub
    Redis-->>API: Socket.IO receives event
    API->>UI: WebSocket emit "vessel:update"
    UI->>UI: Update vessel marker in real-time

    Note over Worker,UI: Collision Alert
    Worker->>Worker: Detect collision risk
    Worker->>Redis: emit_alert() via Redis pub/sub
    Redis-->>API: Socket.IO receives event
    API->>UI: WebSocket emit "alert:new"
    UI->>UI: Display alert notification
```

**Key Points:**
- Socket.IO uses Redis DB 3 for cross-process pub/sub
- Celery workers emit events that reach browser clients via Redis
- Frontend receives updates without polling (real-time)

---

## Directory Structure

```
poseidon-mss/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── routes.py      # Main API router
│   │   │   │   ├── vessels.py     # Vessel endpoints
│   │   │   │   ├── zones.py       # Zone endpoints
│   │   │   │   └── schemas.py     # Pydantic models
│   │   │   └── ais_routes.py      # AIS source management
│   │   ├── ais/
│   │   │   ├── adapters/
│   │   │   │   ├── base.py        # Adapter interface
│   │   │   │   └── emulator.py    # Emulator adapter
│   │   │   ├── models.py          # AIS data models
│   │   │   ├── manager.py         # Adapter manager
│   │   │   ├── processor.py       # Message processor
│   │   │   └── collision_detection.py
│   │   ├── socketio/
│   │   │   ├── __init__.py        # Module exports
│   │   │   ├── server.py          # Socket.IO server & emit functions
│   │   │   └── serializers.py     # Event data serializers
│   │   ├── emulator/
│   │   │   ├── engine.py          # Emulator core
│   │   │   ├── vessel.py          # Vessel simulation
│   │   │   ├── behaviors.py       # Movement behaviors
│   │   │   └── scenarios.py       # Scenario loader
│   │   ├── models/
│   │   │   ├── vessel.py          # Vessel model
│   │   │   ├── position.py        # Position model
│   │   │   ├── zone.py            # Zone model
│   │   │   ├── alert.py           # Alert model
│   │   │   └── config.py          # System config
│   │   ├── database/
│   │   │   ├── connection.py      # DB connection
│   │   │   └── session.py         # Session management
│   │   ├── cache/
│   │   │   └── redis_client.py    # Redis client
│   │   ├── tasks/
│   │   │   └── ais_ingestion.py   # Celery tasks
│   │   ├── main.py                # FastAPI entry
│   │   ├── config.py              # Settings
│   │   └── celery_app.py          # Celery config
│   ├── alembic/
│   │   └── versions/              # Migrations
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/
│   │   │   │   ├── VesselLayer.tsx
│   │   │   │   └── ZoneLayer.tsx
│   │   │   ├── Layout.tsx
│   │   │   └── VesselDetails.tsx
│   │   ├── pages/
│   │   │   └── Dashboard.tsx
│   │   ├── hooks/
│   │   │   ├── useVessels.ts
│   │   │   ├── useZones.ts
│   │   │   ├── useSocket.ts
│   │   │   └── useAlerts.ts
│   │   ├── stores/
│   │   │   ├── useVesselStore.ts
│   │   │   └── useMapStore.ts
│   │   ├── lib/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── docker/
│   └── postgres/
│       └── init.sql               # DB initialization
│
├── scenarios/
│   ├── thessaloniki_normal_traffic.yaml
│   ├── collision_threat.yaml
│   ├── ais_gap_dark_vessel.yaml
│   ├── loitering_suspicious.yaml
│   └── zone_violation.yaml
│
├── docs/                          # Documentation
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Environment Configuration

### Required Environment Variables

```bash
# Application
ENVIRONMENT=development|staging|production
DEBUG=true|false
SECRET_KEY=<secret-key>

# Database
DATABASE_URL=postgresql://poseidon:poseidon@postgres:5432/poseidon

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend
MAPBOX_TOKEN=<mapbox-access-token>

# Logging
LOG_LEVEL=INFO
```

---

## Deployment Architecture

### Development

```mermaid
graph TB
    subgraph "Developer Machine"
        DC[Docker Compose]
        subgraph "Containers"
            All[All Services]
        end
    end
    DC --> All
```

All services run locally via Docker Compose with hot-reload enabled for development.

### Production Considerations

For production deployment, consider:

1. **Container Orchestration**: Kubernetes or ECS for scaling
2. **Database**: Managed PostgreSQL with PostGIS (e.g., AWS RDS, Cloud SQL)
3. **Caching**: Managed Redis (e.g., ElastiCache, Memorystore)
4. **Load Balancing**: Application load balancer for the frontend and backend
5. **CDN**: Static asset delivery for frontend
6. **Secrets Management**: Vault, AWS Secrets Manager, or similar
7. **Monitoring**: Prometheus/Grafana, DataDog, or CloudWatch

---

*This document reflects the actual implemented architecture as of the documentation date.*
