# Poseidon Maritime Security System - Functional Requirements

## 1. Core Functional Requirements (Phase 1-2)

### 1.1 Vessel Tracking
- **FR-001**: System SHALL display all vessels in the monitored area on an interactive map
- **FR-002**: System SHALL update vessel positions automatically every 60 seconds
- **FR-003**: System SHALL display vessel information including: MMSI, name, type, speed, course, heading, and last seen timestamp
- **FR-004**: System SHALL color-code vessel markers by type:
  - Cargo: Blue
  - Tanker: Red
  - Passenger: Green
  - Fishing: Yellow
  - Other/Unknown: Gray
- **FR-005**: System SHALL display directional indicator showing vessel heading
- **FR-006**: System SHALL allow users to click vessel markers to view detailed information
- **FR-007**: System SHALL display vessel name on hover (tooltip)
- **FR-008**: System SHALL provide historical track view for any vessel showing past 24 hours of movement

### 1.2 Security Zones (Geofencing)
- **FR-009**: System SHALL display security zones on the map as colored polygons
- **FR-010**: System SHALL support multiple zone types:
  - Restricted areas
  - Anchorage zones
  - Port boundaries
  - Approach channels
  - Pilot boarding areas
- **FR-011**: System SHALL color-code zones by security level:
  - Critical: Red
  - High: Orange
  - Medium: Yellow
  - Low: Blue
- **FR-012**: System SHALL detect when vessels enter restricted zones
- **FR-013**: System SHALL generate alerts for unauthorized zone entries
- **FR-014**: System SHALL track vessel dwell time in zones

### 1.3 Collision Risk Detection
- **FR-015**: System SHALL calculate Time to Closest Point of Approach (TCPA) for all vessel pairs within 10 nautical miles
- **FR-016**: System SHALL calculate Closest Point of Approach (CPA) distance
- **FR-017**: System SHALL generate collision risk alerts with severity levels:
  - CRITICAL: TCPA < 10 min AND CPA < 0.5 nm
  - HIGH: TCPA < 20 min AND CPA < 1 nm
  - MEDIUM: TCPA < 30 min AND CPA < 2 nm
- **FR-018**: System SHALL identify both vessels involved in potential collision
- **FR-019**: System SHALL display collision risk information including current separation distance and relative bearing

### 1.4 Suspicious Behavior Detection
- **FR-020**: System SHALL detect loitering vessels (speed < 1 knot for > 30 minutes outside anchorage)
- **FR-021**: System SHALL detect sudden speed changes (> 5 knots in < 2 minutes)
- **FR-022**: System SHALL detect course deviations (> 45° change without navigational reason)
- **FR-023**: System SHALL detect AIS transmission gaps (no signal for > 10 minutes while vessel was underway)
- **FR-024**: System SHALL flag vessels exhibiting suspicious behavior patterns

### 1.5 Alert Management
- **FR-025**: System SHALL display all active alerts in a prioritized list
- **FR-026**: System SHALL organize alerts by severity (Critical, High, Medium, Low, Info)
- **FR-027**: System SHALL allow filtering alerts by type, severity, and status
- **FR-028**: System SHALL allow users to acknowledge alerts
- **FR-029**: System SHALL allow users to resolve alerts with notes
- **FR-030**: System SHALL maintain audit trail of all alert actions (who, when, what)
- **FR-031**: System SHALL display alert count by severity level
- **FR-032**: System SHALL provide real-time notifications for new critical alerts

### 1.6 Vessel Intelligence
- **FR-033**: System SHALL maintain vessel profile with static information (name, type, dimensions, flag)
- **FR-034**: System SHALL calculate and display vessel risk score based on alert history
- **FR-035**: System SHALL track alert count by vessel (total, critical, high)
- **FR-036**: System SHALL record first seen and last seen timestamps for each vessel
- **FR-037**: System SHALL support "watch list" for vessels of interest
- **FR-038**: System SHALL provide vessel search functionality by name or MMSI

### 1.7 Data Sources (AIS Integration)
- **FR-039**: System SHALL support multiple AIS data sources with automatic failover
- **FR-040**: System SHALL support the following adapter types:
  - Traffic emulator (development/testing)
  - AISHub API
  - Port's own AIS receiver
  - Other AIS data providers
- **FR-041**: System SHALL allow switching between data sources via API
- **FR-042**: System SHALL display current active data source and health status
- **FR-043**: System SHALL provide data source quality metrics

### 1.8 Traffic Emulator (Development/Testing)
- **FR-044**: System SHALL include built-in traffic emulator for offline development
- **FR-045**: System SHALL support scenario-based simulation from YAML files
- **FR-046**: System SHALL provide pre-built scenarios:
  - Normal port traffic
  - Collision threat
  - Zone violation
  - Suspicious loitering
- **FR-047**: System SHALL generate realistic vessel movements including:
  - Straight-line navigation
  - Loitering behavior
  - Waypoint following
  - Evasive maneuvers
- **FR-048**: System SHALL allow loading different scenarios via API
- **FR-049**: System SHALL support configurable number of vessels and update intervals

### 1.9 Historical Data & Reporting
- **FR-050**: System SHALL store vessel position history for minimum 30 days
- **FR-051**: System SHALL store all alerts indefinitely
- **FR-052**: System SHALL provide vessel track playback for any time period
- **FR-053**: System SHALL support querying historical data by:
  - Time range
  - Vessel MMSI
  - Geographic area
  - Event type

### 1.10 System Configuration
- **FR-054**: System SHALL allow configuration of alert thresholds
- **FR-055**: System SHALL support environment-specific configuration (development, testing, production)
- **FR-056**: System SHALL store configuration in database for runtime modification
- **FR-057**: System SHALL support configurable parameters:
  - Collision alert thresholds (TCPA/CPA)
  - Loitering duration and speed thresholds
  - AIS gap detection time
  - Speed/course change thresholds
  - Data update intervals

---

## 2. Non-Functional Requirements

### 2.1 Performance
- **NFR-001**: System SHALL support monitoring of 200+ vessels simultaneously
- **NFR-002**: System SHALL update vessel positions with < 60 second latency
- **NFR-003**: System SHALL generate collision alerts within 60 seconds of detection
- **NFR-004**: API responses SHALL complete in < 200ms (95th percentile)
- **NFR-005**: Map rendering SHALL maintain > 30 FPS with 100+ vessels displayed
- **NFR-006**: System SHALL handle 10+ concurrent users without degradation

### 2.2 Reliability
- **NFR-007**: System SHALL implement automatic failover between AIS data sources
- **NFR-008**: System SHALL gracefully handle temporary data source outages
- **NFR-009**: System SHALL maintain data integrity during system restarts
- **NFR-010**: System SHALL log all errors with sufficient detail for troubleshooting

### 2.3 Scalability
- **NFR-011**: System SHALL support horizontal scaling of backend services
- **NFR-012**: Database SHALL efficiently handle 1M+ position records
- **NFR-013**: System SHALL use time-series optimization for position data (TimescaleDB - Phase 2)

### 2.4 Usability
- **NFR-014**: System SHALL provide intuitive map-based interface requiring minimal training
- **NFR-015**: System SHALL be responsive and work on desktop browsers (1920x1080 minimum)
- **NFR-016**: System SHALL provide clear visual indicators for all alert severities
- **NFR-017**: System SHALL use consistent color coding throughout the interface

### 2.5 Security
- **NFR-018**: System SHALL validate all API inputs
- **NFR-019**: System SHALL implement CORS restrictions for frontend origin
- **NFR-020**: System SHALL rate-limit API requests (100 req/min per IP)
- **NFR-021**: System SHALL not expose sensitive configuration in client code

### 2.6 Maintainability
- **NFR-022**: System SHALL use consistent coding standards throughout
- **NFR-023**: System SHALL include type hints in all Python code
- **NFR-024**: System SHALL use TypeScript strict mode for frontend
- **NFR-025**: System SHALL include comprehensive error handling
- **NFR-026**: System SHALL maintain separation of concerns (adapter pattern for data sources)

### 2.7 Testability
- **NFR-027**: System SHALL support automated testing via traffic emulator
- **NFR-028**: System SHALL provide reproducible test scenarios
- **NFR-029**: System SHALL allow manual triggering of background tasks
- **NFR-030**: System SHALL expose health check endpoints for monitoring

---

## 3. Data Requirements

### 3.1 Vessel Data
- **DR-001**: System SHALL store vessel static information (MMSI, name, type, dimensions, flag)
- **DR-002**: System SHALL store vessel positions with timestamp, lat/lon, speed, course, heading
- **DR-003**: System SHALL use PostGIS geography type for spatial data (SRID 4326)
- **DR-004**: System SHALL maintain position history with time-series optimization

### 3.2 Security Zone Data
- **DR-005**: System SHALL store zone geometry as PostGIS polygons
- **DR-006**: System SHALL store zone metadata (name, type, security level, alert configuration)
- **DR-007**: System SHALL support JSONB for flexible zone configuration

### 3.3 Alert Data
- **DR-008**: System SHALL store all alert types with severity, status, timestamp
- **DR-009**: System SHALL store alert details in JSONB for flexibility
- **DR-010**: System SHALL maintain complete audit trail for alert acknowledgments

### 3.4 Configuration Data
- **DR-011**: System SHALL store system configuration as key-value pairs
- **DR-012**: System SHALL support runtime configuration updates
- **DR-013**: System SHALL maintain default configuration values

---

## 4. Integration Requirements

### 4.1 AIS Data Sources
- **IR-001**: System SHALL integrate with AISHub API
- **IR-002**: System SHALL support NMEA AIS message format
- **IR-003**: System SHALL support port's proprietary AIS receiver protocols (future)
- **IR-004**: System SHALL parse AIVDM AIS messages using pyais library

### 4.2 Mapping
- **IR-005**: System SHALL integrate with Mapbox GL JS for map rendering
- **IR-006**: System SHALL support GeoJSON format for spatial data exchange
- **IR-007**: System SHALL render vessel markers and zones as Mapbox layers

### 4.3 Real-Time Updates
- **IR-008**: System SHALL support WebSocket connections for live updates (Phase 2)
- **IR-009**: System SHALL broadcast position updates to connected clients (Phase 2)
- **IR-010**: System SHALL broadcast alert notifications in real-time (Phase 2)

---

## 5. Operational Requirements

### 5.1 Deployment
- **OR-001**: System SHALL run in Docker containers
- **OR-002**: System SHALL support Docker Compose for local development
- **OR-003**: System SHALL support single-command startup (`docker compose up`)
- **OR-004**: System SHALL include database initialization scripts

### 5.2 Monitoring
- **OR-005**: System SHALL expose health check endpoints
- **OR-006**: System SHALL log all system operations
- **OR-007**: System SHALL track data source health and quality metrics

### 5.3 Data Retention
- **OR-008**: System SHALL retain position data for 30 days (configurable to 90 days)
- **OR-009**: System SHALL retain alert data indefinitely
- **OR-010**: System SHALL support data compression for historical positions

---

## 6. Future Enhancements (Out of Scope for Phase 1-2)

### 6.1 Satellite Integration (Phase 3)
- Copernicus Sentinel-1 SAR imagery
- Dark vessel detection (satellite without AIS)
- Satellite-AIS fusion and correlation

### 6.2 Advanced Analytics (Phase 4)
- Machine learning for trajectory prediction
- Anomaly detection using Isolation Forest
- Pattern-of-life analysis
- Vessel behavior classification

### 6.3 Additional Features (Phase 4+)
- User authentication and role-based access control
- Email/SMS alert notifications
- Multi-port support
- Mobile application
- Report generation (PDF/Excel)
- Integration with port authority systems

---

**This document defines the functional requirements for Poseidon Maritime Security System Phase 1-2 implementation.**