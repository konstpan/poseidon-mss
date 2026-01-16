// Bounding box for spatial queries
export interface BoundingBox {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

// Vessel types (AIS ship type categories)
export enum VesselTypeCategory {
  CARGO = 'cargo',
  TANKER = 'tanker',
  PASSENGER = 'passenger',
  FISHING = 'fishing',
  TUG = 'tug',
  PILOT = 'pilot',
  MILITARY = 'military',
  SAILING = 'sailing',
  PLEASURE = 'pleasure',
  HIGH_SPEED = 'high_speed',
  OTHER = 'other',
}

// Map AIS ship type codes to categories
export function getVesselCategory(shipType: number | undefined | null): VesselTypeCategory {
  if (shipType === undefined || shipType === null) return VesselTypeCategory.OTHER;

  // Cargo: 70-79
  if (shipType >= 70 && shipType <= 79) return VesselTypeCategory.CARGO;
  // Tanker: 80-89
  if (shipType >= 80 && shipType <= 89) return VesselTypeCategory.TANKER;
  // Passenger: 60-69
  if (shipType >= 60 && shipType <= 69) return VesselTypeCategory.PASSENGER;
  // Fishing: 30
  if (shipType === 30) return VesselTypeCategory.FISHING;
  // Tug: 31-32, 52
  if (shipType === 31 || shipType === 32 || shipType === 52) return VesselTypeCategory.TUG;
  // Pilot: 50
  if (shipType === 50) return VesselTypeCategory.PILOT;
  // Military: 35
  if (shipType === 35) return VesselTypeCategory.MILITARY;
  // Sailing: 36
  if (shipType === 36) return VesselTypeCategory.SAILING;
  // Pleasure: 37
  if (shipType === 37) return VesselTypeCategory.PLEASURE;
  // High speed: 40-49
  if (shipType >= 40 && shipType <= 49) return VesselTypeCategory.HIGH_SPEED;

  return VesselTypeCategory.OTHER;
}

// Vessel colors by category
export const VESSEL_COLORS: Record<VesselTypeCategory, string> = {
  [VesselTypeCategory.CARGO]: '#3B82F6',      // blue
  [VesselTypeCategory.TANKER]: '#EF4444',     // red
  [VesselTypeCategory.PASSENGER]: '#10B981',  // green
  [VesselTypeCategory.FISHING]: '#F59E0B',    // yellow/amber
  [VesselTypeCategory.TUG]: '#8B5CF6',        // purple
  [VesselTypeCategory.PILOT]: '#EC4899',      // pink
  [VesselTypeCategory.MILITARY]: '#6366F1',   // indigo
  [VesselTypeCategory.SAILING]: '#14B8A6',    // teal
  [VesselTypeCategory.PLEASURE]: '#06B6D4',   // cyan
  [VesselTypeCategory.HIGH_SPEED]: '#F97316', // orange
  [VesselTypeCategory.OTHER]: '#6B7280',      // gray
};

// Vessel from API (snake_case to match backend)
export interface Vessel {
  mmsi: string;
  imo?: string | null;
  name?: string | null;
  call_sign?: string | null;
  ship_type?: number | null;
  ship_type_text?: string | null;
  length?: number | null;
  width?: number | null;
  draught?: number | null;
  flag_state?: string | null;
  destination?: string | null;
  eta?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  speed?: number | null;
  course?: number | null;
  heading?: number | null;
  last_seen?: string | null;
  risk_score?: number | null;
  risk_category?: string | null;
}

// Detailed vessel info (same as Vessel for now, but can extend)
export interface VesselDetails extends Vessel {
  // Additional fields can be added here
}

// Vessel position in a track
export interface VesselPosition {
  mmsi: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  speed?: number | null;
  course?: number | null;
  heading?: number | null;
  navigation_status?: number | null;
  navigation_status_text?: string | null;
}

// GeoJSON types for track
export interface GeoJSONFeature {
  type: 'Feature';
  geometry: {
    type: 'LineString' | 'Point';
    coordinates: number[] | number[][];
  };
  properties: {
    mmsi: string;
    vessel_name?: string | null;
    start_time: string;
    end_time: string;
    point_count: number;
  };
}

// Vessel track response (GeoJSON FeatureCollection)
export interface VesselTrack {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
  positions: VesselPosition[];
}

// Zone types
export type ZoneType =
  | 'port_boundary'
  | 'restricted'
  | 'anchorage'
  | 'approach_channel'
  | 'military'
  | 'environmental'
  | 'traffic_separation'
  | 'pilot_boarding'
  | 'general';

// Security levels
export type SecurityLevel = 1 | 2 | 3 | 4 | 5;

// Zone colors by security level
export const ZONE_COLORS: Record<SecurityLevel, string> = {
  5: '#EF4444', // Critical - red
  4: '#F97316', // High - orange
  3: '#F59E0B', // Elevated - yellow/amber
  2: '#3B82F6', // Moderate - blue
  1: '#10B981', // Low - green
};

// Zone properties from API (snake_case to match backend)
export interface ZoneProperties {
  id: string;
  name: string;
  code?: string | null;
  description?: string | null;
  zone_type: string;
  zone_type_text: string;
  security_level: SecurityLevel;
  security_level_text: string;
  active: boolean;
  monitor_entries: boolean;
  monitor_exits: boolean;
  speed_limit_knots?: number | null;
  display_color?: string | null;
  fill_opacity?: number | null;
  alert_config?: Record<string, unknown> | null;
  time_restrictions?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// Zone as GeoJSON Feature
export interface Zone {
  type: 'Feature';
  geometry: {
    type: 'Polygon';
    coordinates: number[][][];
  };
  properties: ZoneProperties;
}

// Zone list response (GeoJSON FeatureCollection)
export interface ZoneListResponse {
  type: 'FeatureCollection';
  features: Zone[];
  total: number;
}

// Alert types
export type AlertType =
  | 'zone_entry'
  | 'zone_exit'
  | 'speed_violation'
  | 'ais_gap'
  | 'dark_vessel'
  | 'collision_risk'
  | 'suspicious_behavior'
  | 'anchor_dragging'
  | 'route_deviation'
  | 'port_approach'
  | 'zone_violation'
  | 'ais_spoofing'
  | 'unusual_behavior';

export type AlertSeverity = 'info' | 'warning' | 'alert' | 'critical' | 'low' | 'medium' | 'high';

export interface Alert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  vessel_mmsi: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
}

// AIS Source status
export interface AISSourceInfo {
  name: string;
  source_type: string;
  is_active: boolean;
  is_healthy: boolean;
  message_count: number;
  last_message_time?: string | null;
  error_count: number;
  last_error?: string | null;
}

export interface AISSourceStatus {
  active_source: string;
  sources: AISSourceInfo[];
  manager_stats: {
    total_messages?: number;
    uptime_seconds?: number;
    [key: string]: unknown;
  };
}

// Legacy types for backwards compatibility
export interface ApiResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
}
