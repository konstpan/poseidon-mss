-- Poseidon MSS Database Initialization
-- Enable required extensions

-- PostGIS for geospatial data
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- TimescaleDB for time-series data
-- CREATE EXTENSION IF NOT EXISTS timescaledb;  -- Will add in Phase 2

-- Additional useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify extensions are installed
SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis', 'timescaledb', 'uuid-ossp', 'pg_trgm');

-- Create schemas
CREATE SCHEMA IF NOT EXISTS ais;
CREATE SCHEMA IF NOT EXISTS security;

-- Grant permissions
GRANT ALL ON SCHEMA ais TO poseidon;
GRANT ALL ON SCHEMA security TO poseidon;

-- Create initial tables
-- Vessels table
CREATE TABLE IF NOT EXISTS ais.vessels (
    mmsi VARCHAR(9) PRIMARY KEY,
    imo VARCHAR(10),
    name VARCHAR(255),
    call_sign VARCHAR(50),
    ship_type INTEGER,
    dimension_a INTEGER,
    dimension_b INTEGER,
    dimension_c INTEGER,
    dimension_d INTEGER,
    draught DECIMAL(4,1),
    destination VARCHAR(255),
    eta TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vessel positions table (time-series)
CREATE TABLE IF NOT EXISTS ais.vessel_positions (
    id BIGSERIAL,
    mmsi VARCHAR(9) NOT NULL,
    position GEOMETRY(Point, 4326) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(10,6) NOT NULL,
    course DECIMAL(5,2),
    speed DECIMAL(5,2),
    heading INTEGER,
    navigation_status INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable for time-series optimization
--SELECT create_hypertable('ais.vessel_positions', 'timestamp',
--    chunk_time_interval => INTERVAL '1 day',
--    if_not_exists => TRUE
--);

-- Create index on vessel positions
CREATE INDEX IF NOT EXISTS idx_vessel_positions_mmsi ON ais.vessel_positions (mmsi, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vessel_positions_geom ON ais.vessel_positions USING GIST (position);

-- Security zones table
CREATE TABLE IF NOT EXISTS security.zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    zone_type VARCHAR(50) NOT NULL,
    geometry GEOMETRY(Polygon, 4326) NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zones_geom ON security.zones USING GIST (geometry);

-- Alerts table
CREATE TABLE IF NOT EXISTS security.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    vessel_mmsi VARCHAR(9),
    zone_id UUID REFERENCES security.zones(id),
    message TEXT NOT NULL,
    metadata JSONB,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_vessel ON security.alerts (vessel_mmsi);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON security.alerts (created_at DESC);

-- Log initialization completion
DO $$
BEGIN
    RAISE NOTICE 'Poseidon MSS database initialized successfully';
END $$;
