# Poseidon Maritime Security System - Backend API Documentation

**Version:** 0.1.0
**Generated:** January 2026
**Status:** As-Built Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Base Configuration](#base-configuration)
3. [Authentication & CORS](#authentication--cors)
4. [API Endpoints](#api-endpoints)
5. [Request/Response Examples](#requestresponse-examples)
6. [Error Responses](#error-responses)
7. [Celery Tasks](#celery-tasks)
8. [WebSocket Events](#websocket-events)

---

## Overview

The Poseidon MSS backend is built with **FastAPI 0.109.0** and provides a RESTful API for vessel tracking, security zone management, and AIS data source control.

### API Base URL

```
http://localhost:8000/api/v1
```

### Documentation

- **OpenAPI/Swagger**: `http://localhost:8000/docs` (development only)
- **ReDoc**: `http://localhost:8000/redoc` (development only)
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## Base Configuration

### Application Settings

| Setting | Value | Description |
|---------|-------|-------------|
| App Name | Poseidon Maritime Security System | Application title |
| Version | 0.1.0 | API version |
| API Prefix | `/api/v1` | All endpoints prefixed |
| Default Port | 8000 | Backend HTTP port |

### Environment Variables

```bash
# Application
ENVIRONMENT=development          # development|staging|production
DEBUG=true                       # Enable debug mode
SECRET_KEY=your-secret-key       # Secret key for signing

# Database
DATABASE_URL=postgresql://poseidon:poseidon@postgres:5432/poseidon

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

---

## Authentication & CORS

### Authentication

**Current State**: No authentication required (development mode).

Future implementation will support:
- JWT tokens
- API keys
- OAuth 2.0

### CORS Configuration

```python
CORSMiddleware(
    allow_origins=["http://localhost:3000"],  # Configurable via CORS_ORIGINS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## API Endpoints

### Health & Status

#### GET `/health`

Health check endpoint for container orchestration.

**Response:**
```json
{
    "status": "healthy",
    "service": "poseidon-mss",
    "environment": "development",
    "database": true,
    "ais_system": true,
    "redis_cache": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "healthy" or "degraded" |
| `database` | boolean | Database connection status |
| `ais_system` | boolean | AIS manager status |
| `redis_cache` | boolean | Redis connection status |

---

#### GET `/`

Root endpoint with service information.

**Response:**
```json
{
    "service": "Poseidon Maritime Security System",
    "version": "0.1.0",
    "environment": "development",
    "docs": "/docs"
}
```

---

#### GET `/status`

Detailed system status with AIS and Redis statistics.

**Response:**
```json
{
    "service": "Poseidon Maritime Security System",
    "version": "0.1.0",
    "environment": "development",
    "ais": {
        "active_adapter": "emulator",
        "adapter_count": 1,
        "total_messages": 1523,
        "uptime_seconds": 3600
    },
    "redis": {
        "connected": true,
        "keys_count": 150
    }
}
```

---

### Vessels

#### GET `/api/v1/vessels`

List vessels with optional filtering and pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `bbox` | string | No | - | Bounding box: `min_lon,min_lat,max_lon,max_lat` |
| `vessel_type` | integer | No | - | AIS ship type code (0-99) |
| `limit` | integer | No | 100 | Maximum results (1-1000) |
| `offset` | integer | No | 0 | Pagination offset |

**Example Request:**
```
GET /api/v1/vessels?bbox=22.5,40.2,23.5,41.0&limit=50
```

**Response:**
```json
{
    "vessels": [
        {
            "mmsi": "237583000",
            "imo": "9234567",
            "name": "OLYMPIC CHAMPION",
            "call_sign": "SVDE",
            "ship_type": 70,
            "ship_type_text": "Cargo",
            "length": 189,
            "width": 28,
            "draught": 10.5,
            "flag_state": "GR",
            "destination": "THESSALONIKI",
            "eta": "2025-01-15T08:00:00Z",
            "latitude": 40.6234,
            "longitude": 22.9456,
            "speed": 12.5,
            "course": 45.2,
            "heading": 44,
            "last_seen": "2025-01-14T12:30:00Z",
            "risk_score": 15.0,
            "risk_category": "low"
        }
    ],
    "total": 150,
    "limit": 50,
    "offset": 0
}
```

---

#### GET `/api/v1/vessels/{mmsi}`

Get detailed information about a specific vessel.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mmsi` | string | Yes | 9-digit Maritime Mobile Service Identity |

**Example Request:**
```
GET /api/v1/vessels/237583000
```

**Response:** Same as single vessel object above.

**Error Response (404):**
```json
{
    "detail": "Vessel with MMSI 237583000 not found"
}
```

---

#### GET `/api/v1/vessels/{mmsi}/track`

Get historical positions for a vessel as GeoJSON.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mmsi` | string | Yes | 9-digit MMSI |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_time` | datetime | No | 24h ago | Start of time range (ISO 8601) |
| `end_time` | datetime | No | now | End of time range (ISO 8601) |
| `limit` | integer | No | 1000 | Maximum positions (1-10000) |

**Example Request:**
```
GET /api/v1/vessels/237583000/track?start_time=2025-01-14T00:00:00Z&limit=500
```

**Response:**
```json
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [22.9, 40.6],
                    [22.91, 40.61],
                    [22.92, 40.62]
                ]
            },
            "properties": {
                "mmsi": "237583000",
                "vessel_name": "OLYMPIC CHAMPION",
                "start_time": "2025-01-14T00:00:00Z",
                "end_time": "2025-01-14T12:00:00Z",
                "point_count": 150
            }
        }
    ],
    "positions": [
        {
            "mmsi": "237583000",
            "timestamp": "2025-01-14T00:00:00Z",
            "latitude": 40.6,
            "longitude": 22.9,
            "speed": 12.0,
            "course": 45.0,
            "heading": 44,
            "navigation_status": 0,
            "navigation_status_text": "Under way using engine"
        }
    ]
}
```

---

### Security Zones

#### GET `/api/v1/zones`

List security zones as GeoJSON FeatureCollection.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `zone_type` | string | No | - | Filter by zone type |
| `active_only` | boolean | No | true | Only return active zones |
| `security_level` | integer | No | - | Minimum security level (1-5) |

**Zone Types:**
- `port_boundary` - Port boundary
- `restricted` - Restricted area
- `anchorage` - Anchorage area
- `approach_channel` - Approach channel
- `military` - Military zone
- `environmental` - Environmental protection zone
- `traffic_separation` - Traffic separation scheme
- `pilot_boarding` - Pilot boarding area
- `general` - General zone

**Example Request:**
```
GET /api/v1/zones?zone_type=port_boundary&security_level=3
```

**Response:**
```json
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [22.9, 40.6],
                        [22.95, 40.6],
                        [22.95, 40.65],
                        [22.9, 40.65],
                        [22.9, 40.6]
                    ]
                ]
            },
            "properties": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Port of Thessaloniki",
                "code": "THESS-PORT",
                "description": "Main port boundary",
                "zone_type": "port_boundary",
                "zone_type_text": "Port Boundary",
                "security_level": 3,
                "security_level_text": "Elevated",
                "active": true,
                "monitor_entries": true,
                "monitor_exits": false,
                "speed_limit_knots": 10.0,
                "display_color": "#FF6B6B",
                "fill_opacity": 0.3,
                "alert_config": {
                    "entry_alert": true,
                    "exit_alert": false
                },
                "time_restrictions": null,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-14T12:00:00Z"
            }
        }
    ],
    "total": 5
}
```

---

#### GET `/api/v1/zones/{zone_id}`

Get details for a specific zone.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zone_id` | UUID | Yes | Zone UUID |

**Example Request:**
```
GET /api/v1/zones/123e4567-e89b-12d3-a456-426614174000
```

**Response:** Single GeoJSON Feature (same structure as in list).

---

### Alerts

#### GET `/api/v1/alerts`

Get alerts with optional filtering.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | - | Filter: active, acknowledged, resolved |
| `severity` | string | No | - | Filter: info, warning, alert, critical |
| `alert_type` | string | No | - | Filter by alert type |
| `hours` | integer | No | 24 | Time window (1-168 hours) |
| `limit` | integer | No | 100 | Maximum results (1-500) |

**Alert Types:**
- `zone_entry` - Vessel entered zone
- `zone_exit` - Vessel exited zone
- `speed_violation` - Speed limit exceeded
- `ais_gap` - AIS signal gap
- `dark_vessel` - Vessel operating without AIS
- `collision_risk` - Potential collision
- `suspicious_behavior` - Suspicious movement pattern
- `anchor_dragging` - Anchor drag detected
- `route_deviation` - Route deviation
- `port_approach` - Port approach

**Example Request:**
```
GET /api/v1/alerts?status=active&severity=critical&hours=12
```

**Response:**
```json
{
    "alerts": [
        {
            "id": "456e7890-e89b-12d3-a456-426614174000",
            "type": "collision_risk",
            "typeText": "Collision Risk",
            "severity": "critical",
            "status": "active",
            "title": "Collision Risk Detected",
            "message": "Vessels OLYMPIC CHAMPION and SEA EXPLORER on collision course",
            "vesselMmsi": "237583000",
            "secondaryVesselMmsi": "237584000",
            "latitude": 40.62,
            "longitude": 22.94,
            "details": {
                "cpa_nm": 0.2,
                "tcpa_min": 15,
                "vessel1_speed": 12.5,
                "vessel2_speed": 10.0
            },
            "riskScore": 85.0,
            "acknowledged": false,
            "acknowledgedAt": null,
            "resolved": false,
            "resolvedAt": null,
            "createdAt": "2025-01-14T12:30:00Z",
            "updatedAt": "2025-01-14T12:30:00Z"
        }
    ]
}
```

---

### AIS Sources

#### GET `/api/v1/ais-sources/status`

Get status of all AIS data sources.

**Response:**
```json
{
    "active_source": "emulator",
    "sources": [
        {
            "name": "emulator",
            "source_type": "emulator",
            "is_active": true,
            "is_healthy": true,
            "message_count": 1523,
            "last_message_time": "2025-01-14T12:30:00Z",
            "error_count": 0,
            "last_error": null,
            "data_quality": 1.0
        }
    ],
    "manager_stats": {
        "total_fetches": 150,
        "total_messages": 1523,
        "failover_count": 0,
        "uptime_seconds": 3600
    }
}
```

---

#### POST `/api/v1/ais-sources/switch`

Switch to a different data source.

**Request Body:**
```json
{
    "source_name": "emulator"
}
```

**Response:**
```json
{
    "message": "Switched to source: emulator"
}
```

---

#### GET `/api/v1/ais-sources/health`

Check health of all sources.

**Response:**
```json
{
    "emulator": true
}
```

---

#### GET `/api/v1/ais-sources/emulator/scenarios`

List available emulator scenarios.

**Response:**
```json
{
    "scenarios": [
        {
            "name": "Thessaloniki Normal Traffic",
            "filename": "thessaloniki_normal_traffic.yaml",
            "description": "Normal port operations with typical vessel traffic",
            "vessel_count": 15,
            "duration_minutes": 180
        },
        {
            "name": "Collision Threat",
            "filename": "collision_threat.yaml",
            "description": "Scenario with vessels on collision course",
            "vessel_count": 6,
            "duration_minutes": 60
        }
    ]
}
```

---

#### POST `/api/v1/ais-sources/emulator/load-scenario/{name}`

Load a scenario into the emulator.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Scenario name (without .yaml) |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `clear_existing` | boolean | No | true | Clear existing vessels from DB |

**Example Request:**
```
POST /api/v1/ais-sources/emulator/load-scenario/thessaloniki_normal_traffic
```

**Response:**
```json
{
    "message": "Loaded scenario: thessaloniki_normal_traffic"
}
```

---

#### GET `/api/v1/ais-sources/emulator/stats`

Get emulator statistics.

**Response:**
```json
{
    "stats": {
        "vessel_count": 15,
        "elapsed_seconds": 3600,
        "transmitting_vessels": 14,
        "scenario_name": "thessaloniki_normal_traffic"
    }
}
```

---

#### GET `/api/v1/ais-sources/emulator/vessels`

Get current emulated vessels.

**Response:**
```json
{
    "vessels": [
        {
            "mmsi": 237583000,
            "latitude": 40.62,
            "longitude": 22.94,
            "speed_over_ground": 12.5,
            "course_over_ground": 45.0,
            "heading": 44,
            "timestamp": "2025-01-14T12:30:00Z"
        }
    ],
    "count": 15
}
```

---

#### POST `/api/v1/ais-sources/emulator/add-vessel`

Add a vessel to the running emulation.

**Request Body:**
```json
{
    "mmsi": 237590000,
    "name": "NEW VESSEL",
    "type": "cargo",
    "start_position": [40.60, 22.90],
    "speed": 10.0,
    "course": 90.0,
    "behavior": "straight"
}
```

**Response:**
```json
{
    "message": "Added vessel: NEW VESSEL (237590000)"
}
```

---

#### DELETE `/api/v1/ais-sources/emulator/vessel/{mmsi}`

Remove a vessel from emulation.

**Response:**
```json
{
    "message": "Removed vessel: 237590000"
}
```

---

#### POST `/api/v1/ais-sources/detect-collisions`

Manually trigger collision detection.

**Response:**
```json
{
    "status": "success",
    "risks_detected": 2,
    "alerts_created": 1,
    "alerts_updated": 1
}
```

---

## Request/Response Examples

### Vessel Response Schema

```typescript
interface VesselResponse {
    mmsi: string;           // 9-digit MMSI
    imo?: string;           // IMO number
    name?: string;          // Vessel name
    call_sign?: string;     // Radio call sign
    ship_type?: number;     // AIS ship type code (0-99)
    ship_type_text?: string;// Human-readable type
    length?: number;        // Length in meters
    width?: number;         // Width in meters
    draught?: number;       // Draft in meters
    flag_state?: string;    // ISO country code
    destination?: string;   // Reported destination
    eta?: string;           // ISO 8601 datetime
    latitude?: number;      // Current latitude
    longitude?: number;     // Current longitude
    speed?: number;         // Speed in knots
    course?: number;        // Course in degrees
    heading?: number;       // Heading in degrees
    last_seen?: string;     // ISO 8601 datetime
    risk_score?: number;    // Risk score 0-100
    risk_category?: string; // Risk category
}
```

### Zone Properties Schema

```typescript
interface ZoneProperties {
    id: string;                     // UUID
    name: string;                   // Zone name
    code?: string;                  // Zone code
    description?: string;           // Description
    zone_type: string;              // Zone classification
    zone_type_text: string;         // Human-readable type
    security_level: number;         // 1-5
    security_level_text: string;    // Human-readable level
    active: boolean;                // Active status
    monitor_entries: boolean;       // Monitor entries
    monitor_exits: boolean;         // Monitor exits
    speed_limit_knots?: number;     // Speed limit
    display_color?: string;         // Hex color
    fill_opacity?: number;          // 0-1
    alert_config?: object;          // Alert configuration
    time_restrictions?: object;     // Time restrictions
    created_at: string;             // ISO 8601
    updated_at: string;             // ISO 8601
}
```

---

## Error Responses

### Standard Error Format

```json
{
    "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid parameters (bbox format, MMSI) |
| 404 | Not Found | Vessel/zone/scenario not found |
| 422 | Validation Error | Request body validation failed |
| 500 | Internal Error | Database or processing error |
| 503 | Service Unavailable | AIS manager not initialized |

### Validation Error Response

```json
{
    "detail": [
        {
            "loc": ["query", "bbox"],
            "msg": "Invalid bbox format: min_lon must be less than max_lon",
            "type": "value_error"
        }
    ]
}
```

---

## Celery Tasks

### Task Configuration

```python
# Celery broker and backend
CELERY_BROKER_URL = "redis://redis:6379/1"
CELERY_RESULT_BACKEND = "redis://redis:6379/2"

# Worker settings
worker_concurrency = 4
worker_prefetch_multiplier = 1
task_time_limit = 300  # 5 minute hard limit
task_soft_time_limit = 240  # 4 minute soft limit
```

### Task Queues

| Queue | Tasks | Description |
|-------|-------|-------------|
| `default` | General tasks | Default queue |
| `ais` | AIS processing tasks | AIS data ingestion |
| `alerts` | Alert tasks | Alert processing |

### Scheduled Tasks (Beat Schedule)

| Task | Schedule | Description |
|------|----------|-------------|
| `ais.fetch_and_process` | Every 60 seconds | Fetch and process AIS data |
| `ais.cleanup_old_positions` | Daily at 3 AM UTC | Delete old position records |
| `ais.update_risk_scores` | Every 5 minutes | Update vessel risk scores |
| `ais.detect_collisions` | Every 30 seconds | CPA/TCPA collision detection |

### Task Details

#### `ais.fetch_and_process`

Fetches AIS data from active source and processes into database.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_lat` | float | 40.48 | Minimum latitude |
| `max_lat` | float | 40.65 | Maximum latitude |
| `min_lon` | float | 22.78 | Minimum longitude |
| `max_lon` | float | 23.00 | Maximum longitude |

**Returns:**
```json
{
    "status": "success",
    "messages_fetched": 15,
    "vessels_processed": 15,
    "positions_stored": 15,
    "positions_cached": 15,
    "errors": 0,
    "source": "emulator",
    "elapsed_seconds": 0.45,
    "task_id": "abc123"
}
```

---

#### `ais.detect_collisions`

Calculates CPA/TCPA for vessel pairs and creates collision risk alerts.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cpa_threshold_nm` | float | 0.5 | CPA threshold in nautical miles |
| `tcpa_threshold_min` | float | 30.0 | TCPA threshold in minutes |

**Returns:**
```json
{
    "status": "success",
    "risks_detected": 2,
    "alerts_created": 1,
    "alerts_updated": 1,
    "elapsed_seconds": 0.12,
    "task_id": "def456"
}
```

---

#### `ais.update_risk_scores`

Updates risk scores for all vessels.

**Returns:**
```json
{
    "status": "success",
    "total_vessels": 150,
    "updated": 15,
    "errors": 0,
    "elapsed_seconds": 1.2,
    "task_id": "ghi789"
}
```

---

#### `ais.cleanup_old_positions`

Deletes position records older than specified retention period.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days_to_keep` | int | 30 | Days of data to retain |

**Returns:**
```json
{
    "status": "success",
    "deleted_count": 50000,
    "cutoff_date": "2024-12-15T03:00:00Z",
    "elapsed_seconds": 15.5,
    "task_id": "jkl012"
}
```

---

#### `ais.reload_scenario`

Reloads a scenario in the Celery worker's emulator.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scenario_name` | string | Yes | Scenario name |

**Returns:**
```json
{
    "status": "success",
    "message": "Loaded scenario: thessaloniki_normal_traffic",
    "task_id": "mno345"
}
```

---

### Running Celery

**Worker:**
```bash
celery -A app.celery_app worker -l INFO -Q default,ais,alerts
```

**Beat Scheduler:**
```bash
celery -A app.celery_app beat -l INFO
```

---

## WebSocket Events

The backend supports Socket.IO for real-time updates via WebSocket connections. Events are broadcast through Redis pub/sub, allowing both the web server and Celery workers to emit events to connected clients.

### Connection

```javascript
// Connect directly to backend
const socket = io('http://localhost:8000', {
    path: '/socket.io',
    transports: ['websocket', 'polling']
});

socket.on('connect', () => {
    console.log('Connected to WebSocket');
});

socket.on('disconnect', () => {
    console.log('Disconnected from WebSocket');
});
```

### Architecture

Socket.IO uses Redis (DB 3) as a message broker for cross-process communication:

```
┌─────────────────┐     ┌─────────────────┐
│  Celery Worker  │     │  FastAPI Server │
│  (AIS/Alerts)   │     │  (WebSocket)    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │    ┌───────────┐      │
         └───►│  Redis    │◄─────┘
              │  (DB 3)   │
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │  Browser  │
              │  Clients  │
              └───────────┘
```

### Events

| Event | Direction | Description | Payload |
|-------|-----------|-------------|---------|
| `vessel:update` | Server → Client | Vessel position update | `Vessel` object |
| `alert:new` | Server → Client | New alert created | `Alert` object |

### Event Payloads

#### `vessel:update`

Emitted when a vessel's AIS position is processed.

```json
{
    "mmsi": "237583000",
    "latitude": 40.6234,
    "longitude": 22.9456,
    "speed": 12.5,
    "course": 45.2,
    "heading": 44,
    "last_seen": "2025-01-14T12:30:00Z",
    "name": "OLYMPIC CHAMPION",
    "ship_type": 70
}
```

#### `alert:new`

Emitted when a collision risk or other alert is created.

```json
{
    "id": "456e7890-e89b-12d3-a456-426614174000",
    "type": "collision_risk",
    "severity": "critical",
    "vessel_mmsi": "237583000",
    "message": "Collision risk detected with vessel SEA EXPLORER",
    "timestamp": "2025-01-14T12:30:00Z",
    "acknowledged": false
}
```

### Backend Implementation

Socket.IO server is configured in `backend/app/socketio/server.py`:

```python
# Redis manager for cross-process communication
_mgr = socketio.AsyncRedisManager('redis://redis:6379/3')

# Socket.IO server with Redis manager
sio = socketio.AsyncServer(
    client_manager=_mgr,
    async_mode="asgi",
    cors_allowed_origins="*",
)

# Emit functions (work from web server or Celery workers)
async def emit_vessel_update(vessel_data: dict) -> None:
    await sio.emit("vessel:update", vessel_data)

async def emit_alert(alert_data: dict) -> None:
    await sio.emit("alert:new", alert_data)
```

### Emission Points

| Location | Event | Trigger |
|----------|-------|---------|
| `ais/processor.py` | `vessel:update` | After processing AIS message |
| `ais/collision_detection.py` | `alert:new` | When collision alert created |

---

*This document reflects the actual implemented API as of the documentation date.*
