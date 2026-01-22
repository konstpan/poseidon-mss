# Poseidon Maritime Security System - Functional Requirements

This document describes the functional requirements based on the current implementation.

---

## 1. Vessel Tracking

### 1.1 Real-Time Position Display
- **FR-001**: System displays all vessels in the monitored area on an interactive Mapbox map
- **FR-002**: System updates vessel positions automatically every 60 seconds via Celery background task
- **FR-003**: System receives real-time position updates via WebSocket (Socket.IO)
- **FR-004**: System displays vessel information including: MMSI, name, type, speed, course, heading, and last seen timestamp

### 1.2 Vessel Visualization
- **FR-005**: System color-codes vessel markers by type:
  - Cargo: Blue (#3B82F6)
  - Tanker: Red (#EF4444)
  - Passenger: Green (#22C55E)
  - Fishing: Yellow (#EAB308)
  - Tug: Purple (#A855F7)
  - Pleasure Craft: Cyan (#06B6D4)
  - High Speed Craft: Pink (#EC4899)
  - Other/Unknown: Gray (#6B7280)
- **FR-006**: System allows users to click vessel markers to view detailed information in a slide-out panel
- **FR-007**: Vessel details panel displays: position (formatted coordinates), speed, course, heading, dimensions, flag state, destination, ETA, risk score, and last seen timestamp

### 1.3 Vessel Data Management
- **FR-008**: System stores vessel static information (MMSI, IMO, name, call sign, ship type, dimensions, draught, flag state)
- **FR-009**: System stores vessel dynamic information (position, speed, course, heading, navigation status, rate of turn)
- **FR-010**: System maintains denormalized last position data on vessel records for fast queries
- **FR-011**: System provides vessel search/filter by bounding box and ship type via API

### 1.4 Track History
- **FR-012**: System stores vessel position history in a time-series table
- **FR-013**: System provides API endpoint to retrieve vessel track as GeoJSON LineString
- **FR-014**: Track queries support time range filtering (start_time, end_time parameters)
- **FR-015**: Default track history is 24 hours; maximum 10,000 positions per request

---

## 2. Security Zones (Geofencing)

### 2.1 Zone Display
- **FR-016**: System displays security zones on the map as colored polygon overlays
- **FR-017**: System supports multiple zone types:
  - Port boundary
  - Restricted area
  - Anchorage
  - Approach channel
  - Military zone
  - Environmental zone
  - Traffic separation scheme
  - Pilot boarding area
  - General
- **FR-018**: System color-codes zones by security level (1-5):
  - Level 1 (Low): Green
  - Level 2: Blue
  - Level 3 (Medium): Yellow
  - Level 4: Orange
  - Level 5 (Critical): Red
- **FR-019**: Zone opacity is configurable per zone (default 0.3)

### 2.2 Zone Configuration
- **FR-020**: Each zone stores geometry as PostGIS POLYGON (SRID 4326)
- **FR-021**: Zones have configurable alert settings (JSONB):
  - Entry monitoring (enabled/disabled)
  - Exit monitoring (enabled/disabled)
  - Speed limit enforcement
  - Restricted vessel types
  - Alert severity
  - Notification channels
- **FR-022**: Zones support time-based restrictions (active hours/days, timezone)
- **FR-023**: Zones can be activated/deactivated without deletion

### 2.3 Zone Filtering
- **FR-024**: API supports filtering zones by type, security level, and active status
- **FR-025**: Zone list returns as GeoJSON FeatureCollection

---

## 3. Collision Risk Detection

### 3.1 CPA/TCPA Calculations
- **FR-026**: System calculates Closest Point of Approach (CPA) for vessel pairs
- **FR-027**: System calculates Time to Closest Point of Approach (TCPA)
- **FR-028**: Collision detection runs as scheduled Celery task
- **FR-029**: Manual collision detection can be triggered via API endpoint

### 3.2 Risk Level Assessment
- **FR-030**: System generates collision risk alerts with severity levels:
  - Critical: CPA < 0.25 nm AND TCPA < 10 minutes
  - High (Alert): CPA < 0.5 nm AND TCPA < 15 minutes
  - Medium (Warning): CPA < 0.75 nm AND TCPA < 20 minutes
  - Low (Info): CPA < 1.0 nm
- **FR-031**: System identifies both vessels involved in potential collision
- **FR-032**: Collision alerts include: CPA distance, TCPA, current separation, vessel names

### 3.3 Collision Alert Management
- **FR-033**: System checks for existing collision alerts to prevent duplicates
- **FR-034**: Existing alerts are updated with new CPA/TCPA values
- **FR-035**: Only moving vessels (speed >= 0.5 knots) are considered
- **FR-036**: Only future collision risks (TCPA > 0) generate alerts

---

## 4. Risk Assessment

### 4.1 Risk Scoring
- **FR-037**: System calculates dynamic risk score (0-100) for each vessel
- **FR-038**: Risk scoring factors include:
  - AIS gap duration (base 30 points for dark vessel)
  - Restricted zone entries (25 points)
  - Suspicious behavior patterns (20 points)
- **FR-039**: Risk scores are stored on vessel records
- **FR-040**: Risk scores decay over time when no incidents (configurable decay rate)

### 4.2 Risk Categories
- **FR-041**: Vessels are categorized by risk level (low, medium, high, critical)
- **FR-042**: Risk category is derived from numerical risk score
- **FR-043**: Risk score update runs as scheduled Celery task

---

## 5. Alert Management

### 5.1 Alert Types
- **FR-044**: System supports the following alert types:
  - zone_entry: Vessel entered security zone
  - zone_exit: Vessel exited security zone
  - speed_violation: Vessel exceeded zone speed limit
  - ais_gap: Vessel AIS transmission gap detected
  - dark_vessel: Vessel operating without AIS
  - collision_risk: Potential collision detected
  - suspicious_behavior: Unusual vessel behavior
  - anchor_dragging: Anchor position changed unexpectedly
  - route_deviation: Vessel deviated from expected route
  - port_approach: Vessel approaching port

### 5.2 Alert Severity
- **FR-045**: Alerts are classified by severity: info, warning, alert, critical

### 5.3 Alert Status
- **FR-046**: Alerts have lifecycle status: active, acknowledged, resolved, dismissed, escalated
- **FR-047**: System tracks who acknowledged/resolved alerts and when
- **FR-048**: System stores acknowledgment and resolution notes

### 5.4 Alert Querying
- **FR-049**: Alerts can be filtered by: status, severity, type, time window (hours)
- **FR-050**: Alert list is paginated (limit 1-500, default 100)
- **FR-051**: Each alert includes: type, severity, status, title, message, vessel references, location, risk score, timestamps

### 5.5 Alert Audit Trail
- **FR-052**: System maintains complete audit trail for all alert actions
- **FR-053**: Audit records include: user ID, user name, user role, action, previous/new status, notes, metadata, timestamp
- **FR-054**: Actions tracked: acknowledged, resolved, dismissed, escalated, comment, reassigned

### 5.6 Real-Time Alerts
- **FR-055**: New alerts are broadcast via WebSocket (alert:new event)
- **FR-056**: Frontend displays alerts in a panel sorted by severity
- **FR-057**: Critical alerts are highlighted in red, high in orange

---

## 6. AIS Data Sources

### 6.1 Source Management
- **FR-058**: System supports multiple AIS data source adapters
- **FR-059**: Active source can be switched via API endpoint
- **FR-060**: System provides health check for all configured sources
- **FR-061**: Source status includes: active source, all sources, manager statistics

### 6.2 Traffic Emulator
- **FR-062**: System includes built-in traffic emulator for development/testing
- **FR-063**: Emulator supports scenario-based simulation from YAML files
- **FR-064**: Available scenarios include pre-configured test scenarios (e.g., thessaloniki_normal_traffic)
- **FR-065**: Scenarios define: vessel configurations, movement patterns, area bounds
- **FR-066**: Emulator supports dynamic vessel addition/removal via API
- **FR-067**: Emulator provides statistics (vessels emulated, messages generated)

### 6.3 Data Processing
- **FR-068**: AIS messages are fetched and processed every 60 seconds (configurable)
- **FR-069**: Processing includes: message parsing, vessel upsert, position storage, cache update, WebSocket emission
- **FR-070**: Batch processing handles multiple messages in a single transaction
- **FR-071**: Processing returns statistics: messages_fetched, vessels_processed, positions_stored, errors

---

## 7. Real-Time Updates (WebSocket)

### 7.1 Connection
- **FR-072**: System provides Socket.IO WebSocket server
- **FR-073**: WebSocket supports horizontal scaling via Redis adapter
- **FR-074**: Client falls back to polling if WebSocket unavailable

### 7.2 Events
- **FR-075**: Server emits `vessel:update` event for position changes
- **FR-076**: Server emits `alert:new` event for new security alerts
- **FR-077**: Events contain serialized vessel/alert data

### 7.3 Frontend Integration
- **FR-078**: Frontend maintains WebSocket connection state
- **FR-079**: Frontend updates vessel positions in real-time without page refresh
- **FR-080**: Frontend displays new alerts immediately when received

---

## 8. Data Caching

### 8.1 Redis Cache
- **FR-081**: System caches hot vessel positions in Redis
- **FR-082**: Batch caching operations for efficiency
- **FR-083**: Automatic TTL expiry for old cached data
- **FR-084**: Cache reduces database load for frequently accessed data

---

## 9. System Configuration

### 9.1 Configurable Parameters
- **FR-085**: System stores configuration as key-value pairs in database
- **FR-086**: Configuration categories: alert_thresholds, risk_scoring, ais_processing, notification, system, display
- **FR-087**: Each parameter has: key, name, description, value (JSONB), default value, type, constraints

### 9.2 Default Configurations
- **FR-088**: Speed violation threshold: 10 knots
- **FR-089**: AIS gap threshold: 30 minutes
- **FR-090**: Collision risk distance: 0.5 nm
- **FR-091**: Anchor drag threshold: 50 meters
- **FR-092**: Dark vessel risk score: 30 points
- **FR-093**: Risk decay rate: 2 points/hour
- **FR-094**: Position update interval: 60 seconds
- **FR-095**: Track history default: 24 hours

### 9.3 Configuration Management
- **FR-096**: Configuration can be modified at runtime
- **FR-097**: Some settings are flagged as requiring restart
- **FR-098**: Audit trail tracks who modified settings

---

## 10. System Health & Monitoring

### 10.1 Health Endpoints
- **FR-099**: System provides `/health` endpoint for overall health status
- **FR-100**: Health check verifies: database connectivity, AIS system, Redis cache
- **FR-101**: Returns status: "healthy" or "degraded"

### 10.2 Status Information
- **FR-102**: System provides `/status` endpoint for detailed status
- **FR-103**: Status includes: AIS manager statistics, Redis stats, environment info

---

## 11. Data Maintenance

### 11.1 Position Cleanup
- **FR-104**: System runs daily cleanup task for old position records
- **FR-105**: Default retention period: 30 days
- **FR-106**: Batch deletion (10,000 records per batch) to avoid locks
- **FR-107**: Cleanup is configurable via days_to_keep parameter

---

## 12. API Structure

### 12.1 REST Endpoints
- **FR-108**: Vessels API: `/api/v1/vessels` (list, get, track)
- **FR-109**: Zones API: `/api/v1/zones` (list, get)
- **FR-110**: Alerts API: `/api/v1/alerts` (list with filters)
- **FR-111**: AIS Sources API: `/api/v1/ais-sources` (status, switch, health, emulator management)
- **FR-112**: System API: `/health`, `/status`, `/`

### 12.2 Response Formats
- **FR-113**: Vessel responses include pagination metadata (total, limit, offset, has_more)
- **FR-114**: Zone responses return GeoJSON FeatureCollection
- **FR-115**: Track responses return GeoJSON with LineString geometry

---

## 13. Frontend Features

### 13.1 Dashboard Layout
- **FR-116**: Three-column layout: sidebar, map, details panel
- **FR-117**: Collapsible sidebar sections: Vessels, Zones, Alerts

### 13.2 Map Interface
- **FR-118**: Interactive Mapbox map with dark theme
- **FR-119**: Default viewport centered on Thermaikos Gulf (Thessaloniki)
- **FR-120**: Navigation controls (zoom, rotation) and scale indicator
- **FR-121**: Vessel markers rendered as colored symbols
- **FR-122**: Zone polygons rendered as semi-transparent fills

### 13.3 Vessel List Panel
- **FR-123**: Shows paginated list of vessels (up to 50)
- **FR-124**: Displays vessel name/MMSI, speed, type-colored icon
- **FR-125**: Click to select vessel and fly map to location

### 13.4 Zone List Panel
- **FR-126**: Shows active security zones (up to 10)
- **FR-127**: Displays zone name, type, security level
- **FR-128**: Color-coded by security level

### 13.5 Alert List Panel
- **FR-129**: Shows active alerts (up to 10)
- **FR-130**: Color-coded by severity
- **FR-131**: Displays alert type and message

### 13.6 Vessel Details Panel
- **FR-132**: Slide-in panel showing selected vessel details
- **FR-133**: Displays all vessel metadata and current position data
- **FR-134**: Shows risk score and category
- **FR-135**: Close button to return to map view

### 13.7 Legend
- **FR-136**: Permanent legend showing vessel type color key

---

## Non-Functional Requirements

### Performance
- **NFR-001**: System supports monitoring of 200+ vessels simultaneously
- **NFR-002**: Vessel positions update with < 60 second latency
- **NFR-003**: API responses complete in < 200ms (95th percentile)
- **NFR-004**: Map maintains smooth rendering with 100+ vessels

### Reliability
- **NFR-005**: Background tasks include retry logic (3 retries, 30s exponential backoff)
- **NFR-006**: Task time limits: soft 120s, hard 180s
- **NFR-007**: System logs all errors with detail for troubleshooting

### Scalability
- **NFR-008**: Redis-based Socket.IO adapter enables horizontal scaling
- **NFR-009**: Multiple Celery workers can process tasks in parallel
- **NFR-010**: PostgreSQL connection pooling via asyncpg

### Database
- **NFR-011**: PostGIS GiST indexes on geometry columns
- **NFR-012**: Composite indexes (mmsi, timestamp) for efficient track queries
- **NFR-013**: JSONB fields for flexible configuration and alert details

### Security
- **NFR-014**: Input validation on all API endpoints via Pydantic
- **NFR-015**: CORS configuration for frontend origin
- **NFR-016**: No authentication implemented (development mode)

### Code Quality
- **NFR-017**: TypeScript strict mode for frontend
- **NFR-018**: Python type hints throughout backend
- **NFR-019**: Separation of concerns via adapter pattern for AIS sources

---

## Not Yet Implemented

The following features are planned but not currently implemented:

1. **Authentication & Authorization**: No user login, roles, or permissions
2. **Watch List**: Marking vessels of interest for monitoring
3. **Email/SMS Notifications**: Alert notifications only via WebSocket
4. **Suspicious Behavior Detection**: Loitering, sudden speed changes, course deviations (framework exists, detection logic partial)
5. **Historical Track Playback**: API ready, no UI implementation
6. **AIS Gap Detection**: Threshold configurable, detection task not fully implemented
7. **Report Generation**: No PDF/Excel export
8. **Multi-port Support**: Single deployment area (Thessaloniki)
9. **Live AIS Feed Integration**: Only emulator adapter fully implemented

---

**This document reflects the Poseidon Maritime Security System as currently implemented.**
