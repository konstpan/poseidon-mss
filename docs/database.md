# Poseidon Maritime Security System - Database Documentation

**Version:** 0.1.0
**Generated:** January 2026
**Status:** As-Built Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Schema Organization](#schema-organization)
4. [Table Definitions](#table-definitions)
5. [Relationships](#relationships)
6. [Indexes](#indexes)
7. [PostGIS Configuration](#postgis-configuration)
8. [Sample Queries](#sample-queries)
9. [Migrations](#migrations)

---

## Overview

The Poseidon MSS database is built on PostgreSQL 16 with the PostGIS 3.4 extension for geospatial operations. The database is organized into two logical schemas:

- **`ais`**: Contains AIS (Automatic Identification System) vessel and position data
- **`security`**: Contains security zones, alerts, and system configuration

### Database Connection

```
postgresql://poseidon:poseidon@postgres:5432/poseidon
```

---

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| PostgreSQL | 16 | Relational database |
| PostGIS | 3.4 | Geospatial extension |
| PostGIS Topology | - | Topological data support |
| uuid-ossp | - | UUID generation |
| pg_trgm | - | Trigram text search |

### Future Extensions (Planned)

| Extension | Purpose |
|-----------|---------|
| TimescaleDB | Time-series hypertables for position data |

---

## Schema Organization

```mermaid
erDiagram
    ais_vessels ||--o{ ais_vessel_positions : "has many"
    ais_vessels ||--o{ security_alerts : "triggers"
    security_zones ||--o{ security_alerts : "triggers"
    security_alerts ||--o{ security_alert_acknowledgments : "has many"
```

### Schema: `ais`

| Table | Description |
|-------|-------------|
| `vessels` | Vessel static data and metadata |
| `vessel_positions` | Time-series position data |

### Schema: `security`

| Table | Description |
|-------|-------------|
| `zones` | Geofenced security areas |
| `alerts` | Risk alerts and events |
| `alert_acknowledgments` | Audit trail for alert actions |
| `system_config` | System configuration storage |

---

## Table Definitions

### `ais.vessels`

Stores AIS vessel static data including identification, dimensions, and denormalized last position.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `mmsi` | VARCHAR(9) | **PRIMARY KEY** | Maritime Mobile Service Identity |
| `imo` | VARCHAR(10) | NULLABLE | IMO number (7 digits) |
| `name` | VARCHAR(255) | NULLABLE | Vessel name |
| `call_sign` | VARCHAR(50) | NULLABLE | Radio call sign |
| `ship_type` | INTEGER | NULLABLE | AIS ship type code (0-99) |
| `ship_type_text` | VARCHAR(100) | NULLABLE | Human-readable ship type |
| `dimension_a` | INTEGER | NULLABLE | Distance from GPS to bow (meters) |
| `dimension_b` | INTEGER | NULLABLE | Distance from GPS to stern (meters) |
| `dimension_c` | INTEGER | NULLABLE | Distance from GPS to port (meters) |
| `dimension_d` | INTEGER | NULLABLE | Distance from GPS to starboard (meters) |
| `length` | INTEGER | NULLABLE | Calculated vessel length (a+b) |
| `width` | INTEGER | NULLABLE | Calculated vessel width (c+d) |
| `draught` | NUMERIC(4,1) | NULLABLE | Draft in meters (0.1-25.5) |
| `destination` | VARCHAR(255) | NULLABLE | Reported destination |
| `eta` | TIMESTAMP | NULLABLE | Estimated time of arrival |
| `flag_state` | VARCHAR(2) | NULLABLE | ISO 3166-1 alpha-2 country code |
| `risk_score` | NUMERIC(5,2) | DEFAULT 0.0 | Current risk score (0-100) |
| `risk_category` | VARCHAR(20) | NULLABLE | Risk category label |
| `last_latitude` | NUMERIC(9,6) | NULLABLE | Denormalized last latitude |
| `last_longitude` | NUMERIC(10,6) | NULLABLE | Denormalized last longitude |
| `last_speed` | NUMERIC(5,2) | NULLABLE | Denormalized last speed (knots) |
| `last_course` | NUMERIC(5,2) | NULLABLE | Denormalized last course (degrees) |
| `last_position_time` | TIMESTAMP | NULLABLE | Timestamp of last position |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

**Indexes:**
- `ix_vessels_name` - BTREE on `name`
- `ix_vessels_ship_type` - BTREE on `ship_type`
- `ix_vessels_flag_state` - BTREE on `flag_state`
- `ix_vessels_risk_score` - BTREE on `risk_score`

---

### `ais.vessel_positions`

Time-series storage for vessel position reports with PostGIS geography support.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | **PRIMARY KEY** | Auto-incrementing ID |
| `mmsi` | VARCHAR(9) | **FK** → vessels.mmsi, NOT NULL | Vessel identifier |
| `timestamp` | TIMESTAMP | NOT NULL | Position timestamp from AIS |
| `position` | GEOGRAPHY(Point,4326) | NOT NULL | PostGIS geography point (WGS84) |
| `latitude` | NUMERIC(9,6) | NOT NULL | Latitude coordinate |
| `longitude` | NUMERIC(10,6) | NOT NULL | Longitude coordinate |
| `speed` | NUMERIC(5,2) | NULLABLE | Speed over ground (knots, 0-102.2) |
| `course` | NUMERIC(5,2) | NULLABLE | Course over ground (degrees, 0-359.9) |
| `heading` | INTEGER | NULLABLE | True heading (degrees, 0-359) |
| `navigation_status` | INTEGER | NULLABLE | AIS navigation status code (0-15) |
| `rate_of_turn` | INTEGER | NULLABLE | Rate of turn (deg/min, -127 to 127) |
| `position_accuracy` | INTEGER | NULLABLE | Position accuracy (0=low, 1=high) |
| `received_at` | TIMESTAMPTZ | DEFAULT NOW() | Server receive timestamp |

**Foreign Key:**
- `mmsi` → `ais.vessels.mmsi` ON DELETE CASCADE

**Indexes:**
- `ix_vessel_positions_mmsi_timestamp` - BTREE on (`mmsi`, `timestamp`)
- `ix_vessel_positions_timestamp` - BTREE on `timestamp`
- `ix_vessel_positions_position` - **GIST** on `position`

**Navigation Status Codes:**

| Code | Status |
|------|--------|
| 0 | Under way using engine |
| 1 | At anchor |
| 2 | Not under command |
| 3 | Restricted manoeuvrability |
| 4 | Constrained by draught |
| 5 | Moored |
| 6 | Aground |
| 7 | Engaged in fishing |
| 8 | Under way sailing |
| 9 | Reserved for HSC |
| 10 | Reserved for WIG |
| 11-13 | Reserved |
| 14 | AIS-SART active |
| 15 | Not defined |

---

### `security.zones`

Geofenced security areas with PostGIS polygon geometry.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | **PRIMARY KEY**, DEFAULT uuid_generate_v4() | Zone identifier |
| `name` | VARCHAR(255) | NOT NULL | Zone name |
| `code` | VARCHAR(50) | UNIQUE, NULLABLE | Zone code identifier |
| `description` | TEXT | NULLABLE | Zone description |
| `zone_type` | VARCHAR(50) | NOT NULL, DEFAULT 'general' | Zone classification |
| `security_level` | INTEGER | DEFAULT 1 | Security level (1-5) |
| `geometry` | GEOGRAPHY(Polygon,4326) | NOT NULL | PostGIS polygon (WGS84) |
| `active` | BOOLEAN | DEFAULT true | Zone active status |
| `alert_config` | JSONB | NULLABLE | Alert configuration |
| `monitor_entries` | BOOLEAN | DEFAULT true | Monitor zone entries |
| `monitor_exits` | BOOLEAN | DEFAULT false | Monitor zone exits |
| `speed_limit_knots` | FLOAT | NULLABLE | Speed limit in zone |
| `time_restrictions` | JSONB | NULLABLE | Time-based restrictions |
| `display_color` | VARCHAR(7) | NULLABLE | Hex color for display |
| `fill_opacity` | FLOAT | DEFAULT 0.3 | Fill opacity for display |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

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

**Security Levels:**
| Level | Label |
|-------|-------|
| 1 | Low |
| 2 | Moderate |
| 3 | Elevated |
| 4 | High |
| 5 | Critical |

**alert_config JSONB Example:**
```json
{
    "entry_alert": true,
    "exit_alert": false,
    "speed_limit": 10.0,
    "restricted_vessel_types": [30, 31, 32],
    "alert_severity": "warning",
    "notification_channels": ["websocket", "email"]
}
```

**time_restrictions JSONB Example:**
```json
{
    "active_hours": {"start": "06:00", "end": "22:00"},
    "active_days": [0, 1, 2, 3, 4],
    "timezone": "Europe/Athens"
}
```

**Indexes:**
- `ix_zones_geometry` - **GIST** on `geometry`
- `ix_zones_zone_type` - BTREE on `zone_type`
- `ix_zones_security_level` - BTREE on `security_level`
- `ix_zones_active` - BTREE on `active`

---

### `security.alerts`

Risk alerts and security events.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | **PRIMARY KEY**, DEFAULT uuid_generate_v4() | Alert identifier |
| `alert_type` | VARCHAR(50) | NOT NULL | Alert classification |
| `severity` | VARCHAR(20) | NOT NULL, DEFAULT 'info' | Severity level |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'active' | Alert status |
| `title` | VARCHAR(255) | NOT NULL | Alert title |
| `message` | TEXT | NOT NULL | Alert message |
| `vessel_mmsi` | VARCHAR(9) | **FK** → vessels.mmsi, NULLABLE | Primary vessel |
| `secondary_vessel_mmsi` | VARCHAR(9) | **FK** → vessels.mmsi, NULLABLE | Secondary vessel (collisions) |
| `zone_id` | UUID | **FK** → zones.id, NULLABLE | Related zone |
| `position` | GEOGRAPHY(Point,4326) | NULLABLE | Alert location |
| `latitude` | NUMERIC(9,6) | NULLABLE | Alert latitude |
| `longitude` | NUMERIC(10,6) | NULLABLE | Alert longitude |
| `details` | JSONB | NULLABLE | Additional details |
| `risk_score` | NUMERIC(5,2) | NULLABLE | Associated risk score |
| `acknowledged` | BOOLEAN | DEFAULT false | Acknowledgment flag |
| `acknowledged_at` | TIMESTAMP | NULLABLE | Acknowledgment time |
| `acknowledged_by` | VARCHAR(255) | NULLABLE | Acknowledging user |
| `acknowledgment_notes` | TEXT | NULLABLE | Acknowledgment notes |
| `resolved` | BOOLEAN | DEFAULT false | Resolution flag |
| `resolved_at` | TIMESTAMP | NULLABLE | Resolution time |
| `resolved_by` | VARCHAR(255) | NULLABLE | Resolving user |
| `resolution_notes` | TEXT | NULLABLE | Resolution notes |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Update timestamp |
| `expires_at` | TIMESTAMP | NULLABLE | Auto-dismiss time |

**Alert Types:**
| Type | Description |
|------|-------------|
| `zone_entry` | Vessel entered monitored zone |
| `zone_exit` | Vessel exited monitored zone |
| `speed_violation` | Speed limit exceeded |
| `ais_gap` | AIS signal gap detected |
| `dark_vessel` | Vessel operating without AIS |
| `collision_risk` | Potential collision detected |
| `suspicious_behavior` | Suspicious movement pattern |
| `anchor_dragging` | Anchor drag detected |
| `route_deviation` | Vessel deviated from route |
| `port_approach` | Vessel approaching port |

**Severity Levels:**
| Level | Numeric | Description |
|-------|---------|-------------|
| `info` | 1 | Informational |
| `warning` | 2 | Warning |
| `alert` | 3 | Alert |
| `critical` | 4 | Critical |

**Status Values:**
- `active` - Alert is active
- `acknowledged` - Alert has been acknowledged
- `resolved` - Alert has been resolved
- `dismissed` - Alert was dismissed
- `escalated` - Alert was escalated

**Foreign Keys:**
- `vessel_mmsi` → `ais.vessels.mmsi` ON DELETE SET NULL
- `secondary_vessel_mmsi` → `ais.vessels.mmsi` ON DELETE SET NULL
- `zone_id` → `security.zones.id` ON DELETE SET NULL

**Indexes:**
- `ix_alerts_alert_type` - BTREE on `alert_type`
- `ix_alerts_severity` - BTREE on `severity`
- `ix_alerts_status` - BTREE on `status`
- `ix_alerts_vessel_mmsi` - BTREE on `vessel_mmsi`
- `ix_alerts_created_at` - BTREE on `created_at`
- `ix_alerts_position` - **GIST** on `position`

---

### `security.alert_acknowledgments`

Audit trail for alert acknowledgment actions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | **PRIMARY KEY**, DEFAULT uuid_generate_v4() | Record identifier |
| `alert_id` | UUID | **FK** → alerts.id, NOT NULL | Related alert |
| `user_id` | VARCHAR(255) | NOT NULL | User identifier |
| `user_name` | VARCHAR(255) | NULLABLE | User display name |
| `user_role` | VARCHAR(100) | NULLABLE | User role |
| `action` | VARCHAR(50) | NOT NULL | Action performed |
| `previous_status` | VARCHAR(20) | NULLABLE | Status before action |
| `new_status` | VARCHAR(20) | NULLABLE | Status after action |
| `notes` | TEXT | NULLABLE | Action notes |
| `action_metadata` | JSONB | NULLABLE | Additional metadata |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Action timestamp |

**Action Types:**
- `acknowledged` - Alert was acknowledged
- `resolved` - Alert was resolved
- `dismissed` - Alert was dismissed
- `escalated` - Alert was escalated
- `comment` - Comment was added
- `reassigned` - Alert was reassigned

**action_metadata JSONB Example:**
```json
{
    "ip_address": "192.168.1.100",
    "client_type": "web",
    "session_id": "abc123",
    "reason_code": "false_positive"
}
```

**Foreign Key:**
- `alert_id` → `security.alerts.id` ON DELETE CASCADE

**Indexes:**
- `ix_alert_acks_alert_id` - BTREE on `alert_id`
- `ix_alert_acks_user_id` - BTREE on `user_id`
- `ix_alert_acks_action` - BTREE on `action`
- `ix_alert_acks_created_at` - BTREE on `created_at`

---

### `security.system_config`

Key-value configuration storage with validation support.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | **PRIMARY KEY**, DEFAULT uuid_generate_v4() | Config identifier |
| `key` | VARCHAR(255) | NOT NULL, UNIQUE | Configuration key |
| `category` | VARCHAR(100) | NOT NULL, DEFAULT 'general' | Config category |
| `name` | VARCHAR(255) | NOT NULL | Human-readable name |
| `description` | TEXT | NULLABLE | Configuration description |
| `value` | JSONB | NOT NULL | Configuration value |
| `default_value` | JSONB | NULLABLE | Default value reference |
| `value_type` | VARCHAR(50) | NOT NULL, DEFAULT 'string' | Value type |
| `constraints` | JSONB | NULLABLE | Validation constraints |
| `active` | BOOLEAN | DEFAULT true | Config active status |
| `editable` | BOOLEAN | DEFAULT true | UI editability |
| `requires_restart` | BOOLEAN | DEFAULT false | Requires restart |
| `modified_by` | VARCHAR(255) | NULLABLE | Last modifier |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Update timestamp |

**Categories:**
- `alert_thresholds` - Alert threshold settings
- `risk_scoring` - Risk calculation settings
- `ais_processing` - AIS processing settings
- `notification` - Notification settings
- `system` - System settings
- `display` - Display/UI settings

**Value Types:**
- `string`, `integer`, `float`, `boolean`, `json`, `array`

**Indexes:**
- `ix_system_config_key` - UNIQUE on `key`
- `ix_system_config_category` - BTREE on `category`
- `ix_system_config_active` - BTREE on `active`

**Default Configurations:**

| Key | Category | Default | Description |
|-----|----------|---------|-------------|
| `alert.speed_violation_threshold` | alert_thresholds | 10.0 | Speed threshold (knots) |
| `alert.ais_gap_threshold_minutes` | alert_thresholds | 30 | AIS gap threshold (minutes) |
| `alert.collision_risk_distance_nm` | alert_thresholds | 0.5 | Collision distance (nm) |
| `alert.anchor_drag_threshold_meters` | alert_thresholds | 50 | Anchor drag distance (m) |
| `risk.dark_vessel_score` | risk_scoring | 30 | Dark vessel risk score |
| `risk.restricted_zone_entry_score` | risk_scoring | 25 | Zone entry risk score |
| `risk.suspicious_pattern_score` | risk_scoring | 20 | Suspicious pattern score |
| `risk.decay_rate_per_hour` | risk_scoring | 2.0 | Risk decay rate |
| `ais.position_update_interval_seconds` | ais_processing | 60 | Position update interval |
| `ais.track_history_hours` | ais_processing | 24 | Track history duration |
| `notification.websocket_enabled` | notification | true | WebSocket notifications |
| `notification.email_enabled` | notification | false | Email notifications |
| `notification.alert_cooldown_minutes` | notification | 15 | Alert cooldown period |
| `display.map_center_lat` | display | 40.6401 | Default map center lat |
| `display.map_center_lon` | display | 22.9444 | Default map center lon |
| `display.default_zoom` | display | 12 | Default map zoom |

---

## Relationships

```mermaid
erDiagram
    VESSEL ||--o{ VESSEL_POSITION : "has many"
    VESSEL ||--o{ ALERT : "triggers (primary)"
    VESSEL ||--o{ ALERT : "triggers (secondary)"
    ZONE ||--o{ ALERT : "triggers"
    ALERT ||--o{ ALERT_ACKNOWLEDGMENT : "has many"

    VESSEL {
        string mmsi PK
        string name
        integer ship_type
        decimal risk_score
    }

    VESSEL_POSITION {
        bigint id PK
        string mmsi FK
        geography position
        timestamp timestamp
    }

    ZONE {
        uuid id PK
        string name
        geography geometry
        integer security_level
    }

    ALERT {
        uuid id PK
        string vessel_mmsi FK
        uuid zone_id FK
        string alert_type
        string severity
    }

    ALERT_ACKNOWLEDGMENT {
        uuid id PK
        uuid alert_id FK
        string action
        string user_id
    }
```

---

## Indexes

### Spatial Indexes (GIST)

| Table | Column | Index Name |
|-------|--------|------------|
| `ais.vessel_positions` | `position` | `ix_vessel_positions_position` |
| `security.zones` | `geometry` | `ix_zones_geometry` |
| `security.alerts` | `position` | `ix_alerts_position` |

### Composite Indexes

| Table | Columns | Index Name |
|-------|---------|------------|
| `ais.vessel_positions` | `mmsi`, `timestamp` | `ix_vessel_positions_mmsi_timestamp` |

### Performance Notes

1. **Position queries**: Use GIST indexes for spatial queries (ST_DWithin, ST_Contains)
2. **Time-range queries**: Use the composite index on `(mmsi, timestamp)` for vessel track queries
3. **Alert filtering**: Multiple single-column indexes support varied filtering patterns

---

## PostGIS Configuration

### SRID

All geographic data uses **SRID 4326** (WGS84), the standard for GPS coordinates.

### Geometry Types

| Table | Column | Geometry Type |
|-------|--------|---------------|
| `vessel_positions` | `position` | GEOGRAPHY(Point, 4326) |
| `zones` | `geometry` | GEOGRAPHY(Polygon, 4326) |
| `alerts` | `position` | GEOGRAPHY(Point, 4326) |

### Creating Geographic Data

**Point (Position):**
```sql
-- Using WKT
INSERT INTO ais.vessel_positions (mmsi, position, latitude, longitude, timestamp)
VALUES ('123456789', ST_GeogFromText('SRID=4326;POINT(22.9444 40.6401)'), 40.6401, 22.9444, NOW());

-- Using ST_MakePoint
INSERT INTO ais.vessel_positions (mmsi, position, latitude, longitude, timestamp)
VALUES ('123456789', ST_SetSRID(ST_MakePoint(22.9444, 40.6401), 4326)::geography, 40.6401, 22.9444, NOW());
```

**Polygon (Zone):**
```sql
INSERT INTO security.zones (name, zone_type, geometry)
VALUES (
    'Port Boundary',
    'port_boundary',
    ST_GeogFromText('SRID=4326;POLYGON((22.90 40.60, 22.98 40.60, 22.98 40.68, 22.90 40.68, 22.90 40.60))')
);
```

---

## Sample Queries

### Find vessels within a bounding box

```sql
SELECT v.mmsi, v.name, v.last_latitude, v.last_longitude, v.last_speed
FROM ais.vessels v
WHERE v.last_latitude BETWEEN 40.5 AND 40.7
  AND v.last_longitude BETWEEN 22.8 AND 23.0
ORDER BY v.last_position_time DESC;
```

### Find vessels within distance of a point

```sql
SELECT v.mmsi, v.name,
       ST_Distance(
           ST_SetSRID(ST_MakePoint(v.last_longitude, v.last_latitude), 4326)::geography,
           ST_SetSRID(ST_MakePoint(22.9444, 40.6401), 4326)::geography
       ) / 1852 AS distance_nm
FROM ais.vessels v
WHERE ST_DWithin(
    ST_SetSRID(ST_MakePoint(v.last_longitude, v.last_latitude), 4326)::geography,
    ST_SetSRID(ST_MakePoint(22.9444, 40.6401), 4326)::geography,
    10000  -- 10km in meters
)
ORDER BY distance_nm;
```

### Get vessel track history

```sql
SELECT vp.timestamp, vp.latitude, vp.longitude, vp.speed, vp.course, vp.heading
FROM ais.vessel_positions vp
WHERE vp.mmsi = '123456789'
  AND vp.timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY vp.timestamp ASC;
```

### Find vessels in a zone

```sql
SELECT DISTINCT v.mmsi, v.name, v.ship_type
FROM ais.vessels v
INNER JOIN security.zones z ON z.name = 'Port of Thessaloniki'
WHERE ST_Contains(
    z.geometry::geometry,
    ST_SetSRID(ST_MakePoint(v.last_longitude, v.last_latitude), 4326)
);
```

### Get active alerts with vessel details

```sql
SELECT a.id, a.alert_type, a.severity, a.title, a.created_at,
       v.mmsi, v.name AS vessel_name, v.ship_type,
       z.name AS zone_name
FROM security.alerts a
LEFT JOIN ais.vessels v ON v.mmsi = a.vessel_mmsi
LEFT JOIN security.zones z ON z.id = a.zone_id
WHERE a.status = 'active'
ORDER BY
    CASE a.severity
        WHEN 'critical' THEN 1
        WHEN 'alert' THEN 2
        WHEN 'warning' THEN 3
        ELSE 4
    END,
    a.created_at DESC;
```

### Calculate CPA (Closest Point of Approach)

```sql
-- Get recent positions for two vessels to calculate CPA
WITH vessel1 AS (
    SELECT mmsi, latitude, longitude, speed, course, timestamp
    FROM ais.vessel_positions
    WHERE mmsi = '123456789'
    ORDER BY timestamp DESC
    LIMIT 1
),
vessel2 AS (
    SELECT mmsi, latitude, longitude, speed, course, timestamp
    FROM ais.vessel_positions
    WHERE mmsi = '987654321'
    ORDER BY timestamp DESC
    LIMIT 1
)
SELECT
    v1.mmsi AS vessel1_mmsi,
    v2.mmsi AS vessel2_mmsi,
    ST_Distance(
        ST_SetSRID(ST_MakePoint(v1.longitude, v1.latitude), 4326)::geography,
        ST_SetSRID(ST_MakePoint(v2.longitude, v2.latitude), 4326)::geography
    ) / 1852 AS current_distance_nm
FROM vessel1 v1, vessel2 v2;
```

### Alert summary by type and severity

```sql
SELECT
    alert_type,
    severity,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE status = 'active') AS active,
    COUNT(*) FILTER (WHERE status = 'acknowledged') AS acknowledged,
    COUNT(*) FILTER (WHERE status = 'resolved') AS resolved
FROM security.alerts
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY alert_type, severity
ORDER BY alert_type, severity;
```

### Get configuration by category

```sql
SELECT key, name, value, value_type, description
FROM security.system_config
WHERE category = 'alert_thresholds'
  AND active = true
ORDER BY key;
```

---

## Migrations

The database schema is managed using **Alembic** migrations.

### Migration Location

```
backend/alembic/versions/
```

### Initial Migration

File: `20260112_000000_001_initial_schema.py`

Creates all tables, indexes, and constraints for:
- `ais.vessels`
- `ais.vessel_positions`
- `security.zones`
- `security.alerts`
- `security.alert_acknowledgments`
- `security.system_config`

### Running Migrations

```bash
# Apply all migrations
cd backend
alembic upgrade head

# Check current revision
alembic current

# Create new migration
alembic revision --autogenerate -m "description"
```

### Database Initialization

The initial database setup is performed via `docker/postgres/init.sql` which:
1. Enables PostGIS and other extensions
2. Creates `ais` and `security` schemas
3. Creates base tables (minimal schema)
4. Grants permissions to the `poseidon` user

Full schema is then applied via Alembic migrations.

---

*This document reflects the actual implemented database schema as of the documentation date.*
