import { useEffect, useRef } from 'react';
import type mapboxgl from 'mapbox-gl';
import type { ZoneListResponse, SecurityLevel } from '@/types';
import { ZONE_COLORS } from '@/types';

const ZONE_SOURCE_ID = 'zones';
const ZONE_FILL_LAYER_ID = 'zone-fills';
const ZONE_OUTLINE_LAYER_ID = 'zone-outlines';
const ZONE_LABELS_LAYER_ID = 'zone-labels';

interface ZoneLayerProps {
  map: mapboxgl.Map | null;
  zones: ZoneListResponse | null;
}

/**
 * Convert zones to GeoJSON with styling properties
 */
function zonesToGeoJSON(zones: ZoneListResponse | null): GeoJSON.FeatureCollection {
  if (!zones) {
    return { type: 'FeatureCollection', features: [] };
  }

  return {
    type: 'FeatureCollection',
    features: zones.features.map((zone) => {
      const securityLevel = zone.properties.security_level as SecurityLevel;
      const color = zone.properties.display_color || ZONE_COLORS[securityLevel] || ZONE_COLORS[1];
      const opacity = zone.properties.fill_opacity ?? 0.2;

      // Calculate centroid for label placement
      const coords = zone.geometry.coordinates[0];
      let cx = 0, cy = 0;
      for (const [x, y] of coords) {
        cx += x;
        cy += y;
      }
      cx /= coords.length;
      cy /= coords.length;

      return {
        type: 'Feature' as const,
        geometry: zone.geometry,
        properties: {
          id: zone.properties.id,
          name: zone.properties.name,
          zoneType: zone.properties.zone_type,
          securityLevel,
          color,
          opacity,
          centroidLng: cx,
          centroidLat: cy,
        },
      };
    }),
  };
}

/**
 * Create label points for zones (centroids)
 */
function createLabelPoints(zones: ZoneListResponse | null): GeoJSON.FeatureCollection {
  if (!zones) {
    return { type: 'FeatureCollection', features: [] };
  }

  return {
    type: 'FeatureCollection',
    features: zones.features.map((zone) => {
      // Calculate centroid
      const coords = zone.geometry.coordinates[0];
      let cx = 0, cy = 0;
      for (const [x, y] of coords) {
        cx += x;
        cy += y;
      }
      cx /= coords.length;
      cy /= coords.length;

      return {
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [cx, cy],
        },
        properties: {
          name: zone.properties.name,
          securityLevel: zone.properties.security_level,
        },
      };
    }),
  };
}

export default function ZoneLayer({ map, zones }: ZoneLayerProps) {
  const initialized = useRef(false);

  // Initialize source and layers
  useEffect(() => {
    if (!map || initialized.current) return;

    const initLayers = () => {
      // Add zone source
      if (!map.getSource(ZONE_SOURCE_ID)) {
        map.addSource(ZONE_SOURCE_ID, {
          type: 'geojson',
          data: zonesToGeoJSON(null),
        });
      }

      // Add zone labels source
      if (!map.getSource('zone-labels-source')) {
        map.addSource('zone-labels-source', {
          type: 'geojson',
          data: createLabelPoints(null),
        });
      }

      // Add fill layer (semi-transparent)
      if (!map.getLayer(ZONE_FILL_LAYER_ID)) {
        map.addLayer({
          id: ZONE_FILL_LAYER_ID,
          type: 'fill',
          source: ZONE_SOURCE_ID,
          paint: {
            'fill-color': ['get', 'color'],
            'fill-opacity': ['get', 'opacity'],
          },
        });
      }

      // Add outline layer
      if (!map.getLayer(ZONE_OUTLINE_LAYER_ID)) {
        map.addLayer({
          id: ZONE_OUTLINE_LAYER_ID,
          type: 'line',
          source: ZONE_SOURCE_ID,
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 2,
            'line-opacity': 0.8,
          },
        });
      }

      // Add labels layer
      if (!map.getLayer(ZONE_LABELS_LAYER_ID)) {
        map.addLayer({
          id: ZONE_LABELS_LAYER_ID,
          type: 'symbol',
          source: 'zone-labels-source',
          layout: {
            'text-field': ['get', 'name'],
            'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
            'text-size': 12,
            'text-anchor': 'center',
            'text-allow-overlap': false,
          },
          paint: {
            'text-color': '#ffffff',
            'text-halo-color': '#000000',
            'text-halo-width': 1.5,
          },
          minzoom: 10, // Only show labels when zoomed in
        });
      }

      initialized.current = true;
    };

    if (map.isStyleLoaded()) {
      initLayers();
    } else {
      map.once('style.load', initLayers);
    }
  }, [map]);

  // Update zone data
  useEffect(() => {
    if (!map || !initialized.current) return;

    const source = map.getSource(ZONE_SOURCE_ID) as mapboxgl.GeoJSONSource;
    if (source) {
      source.setData(zonesToGeoJSON(zones));
    }

    const labelSource = map.getSource('zone-labels-source') as mapboxgl.GeoJSONSource;
    if (labelSource) {
      labelSource.setData(createLabelPoints(zones));
    }
  }, [map, zones]);

  return null;
}
