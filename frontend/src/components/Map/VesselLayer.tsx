import { useEffect, useRef } from 'react';
import type mapboxgl from 'mapbox-gl';
import type { Vessel } from '@/types';
import { getVesselCategory, VESSEL_COLORS } from '@/types';

const VESSEL_SOURCE_ID = 'vessels';
const VESSEL_LAYER_ID = 'vessel-markers';
const VESSEL_SELECTED_LAYER_ID = 'vessel-selected';

interface VesselLayerProps {
  map: mapboxgl.Map | null;
  vessels: Vessel[];
  selectedMmsi: string | null;
  onVesselClick: (mmsi: string) => void;
}

/**
 * Convert vessels array to GeoJSON FeatureCollection
 */
function vesselsToGeoJSON(vessels: Vessel[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: vessels
      .filter((v) => v.latitude != null && v.longitude != null)
      .map((vessel) => ({
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [vessel.longitude!, vessel.latitude!],
        },
        properties: {
          mmsi: vessel.mmsi,
          name: vessel.name || vessel.mmsi,
          shipType: vessel.ship_type,
          category: getVesselCategory(vessel.ship_type),
          color: VESSEL_COLORS[getVesselCategory(vessel.ship_type)],
          speed: vessel.speed ?? 0,
          course: vessel.course ?? 0,
          heading: vessel.heading ?? vessel.course ?? 0,
        },
      })),
  };
}

/**
 * Create vessel arrow icon as SVG data URL
 */
function createVesselIcon(color: string, size = 24): string {
  // Arrow/triangle pointing up (will be rotated by heading)
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">
      <path d="M12 2 L20 20 L12 16 L4 20 Z" fill="${color}" stroke="#000" stroke-width="1"/>
    </svg>
  `;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export default function VesselLayer({ map, vessels, selectedMmsi, onVesselClick }: VesselLayerProps) {
  const initialized = useRef(false);
  // Store callback in ref so we can access latest version without re-running effects
  const onVesselClickRef = useRef(onVesselClick);
  onVesselClickRef.current = onVesselClick;

  // Initialize source and layers - runs once when map is available
  useEffect(() => {
    if (!map) return;
    if (initialized.current) return;

    const initLayers = async () => {
      try {
        // Add vessel icons for each category
        const iconPromises = Object.entries(VESSEL_COLORS).map(([category, color]) => {
          const iconId = `vessel-icon-${category}`;

          return new Promise<void>((resolve) => {
            if (map.hasImage(iconId)) {
              resolve();
              return;
            }

            const img = new Image();
            img.onload = () => {
              if (!map.hasImage(iconId)) {
                map.addImage(iconId, img, { sdf: false });
              }
              resolve();
            };
            img.onerror = () => {
              console.warn(`Failed to load vessel icon: ${iconId}`);
              resolve();
            };
            img.src = createVesselIcon(color, 32);
          });
        });

        await Promise.all(iconPromises);

        // Add source with empty data - will be populated by the data update effect
        if (!map.getSource(VESSEL_SOURCE_ID)) {
          map.addSource(VESSEL_SOURCE_ID, {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
          });
        }

        // Add vessel layer
        if (!map.getLayer(VESSEL_LAYER_ID)) {
          map.addLayer({
            id: VESSEL_LAYER_ID,
            type: 'symbol',
            source: VESSEL_SOURCE_ID,
            layout: {
              'icon-image': ['concat', 'vessel-icon-', ['get', 'category']],
              'icon-size': 0.6,
              'icon-rotate': ['get', 'heading'],
              'icon-rotation-alignment': 'map',
              'icon-allow-overlap': true,
              'icon-ignore-placement': true,
              'text-field': ['get', 'name'],
              'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
              'text-size': 11,
              'text-offset': [0, 1.5],
              'text-anchor': 'top',
              'text-optional': true,
            },
            paint: {
              'text-color': '#ffffff',
              'text-halo-color': '#000000',
              'text-halo-width': 1,
              'text-opacity': 0,
            },
          });
        }

        // Add selected vessel highlight layer
        if (!map.getLayer(VESSEL_SELECTED_LAYER_ID)) {
          map.addLayer({
            id: VESSEL_SELECTED_LAYER_ID,
            type: 'circle',
            source: VESSEL_SOURCE_ID,
            filter: ['==', ['get', 'mmsi'], ''],
            paint: {
              'circle-radius': 20,
              'circle-color': 'transparent',
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': 3,
              'circle-stroke-opacity': 0.8,
            },
          });
        }

        // Click handler using ref to always get latest callback
        const clickHandler = (e: mapboxgl.MapMouseEvent) => {
          const features = map.queryRenderedFeatures(e.point, {
            layers: [VESSEL_LAYER_ID],
          });

          if (features.length > 0) {
            const mmsi = features[0].properties?.mmsi;
            if (mmsi) {
              e.preventDefault();
              onVesselClickRef.current(String(mmsi));
            }
          }
        };

        map.on('click', VESSEL_LAYER_ID, clickHandler);

        map.on('mouseenter', VESSEL_LAYER_ID, () => {
          map.getCanvas().style.cursor = 'pointer';
          if (map.getLayer(VESSEL_LAYER_ID)) {
            map.setPaintProperty(VESSEL_LAYER_ID, 'text-opacity', 1);
          }
        });

        map.on('mouseleave', VESSEL_LAYER_ID, () => {
          map.getCanvas().style.cursor = '';
          if (map.getLayer(VESSEL_LAYER_ID)) {
            map.setPaintProperty(VESSEL_LAYER_ID, 'text-opacity', 0);
          }
        });

        initialized.current = true;
        console.log('VesselLayer initialized');
      } catch (error) {
        console.error('Failed to initialize vessel layer:', error);
      }
    };

    // Try to initialize - handle race condition where style might already be loaded
    const tryInit = () => {
      if (map.isStyleLoaded()) {
        initLayers();
        return true;
      }
      return false;
    };

    if (!tryInit()) {
      // Style not loaded yet - try both approaches to be safe
      map.once('style.load', initLayers);

      // Also poll in case 'style.load' already fired before our listener
      const pollInterval = setInterval(() => {
        if (map.isStyleLoaded() && !initialized.current) {
          clearInterval(pollInterval);
          initLayers();
        } else if (initialized.current) {
          clearInterval(pollInterval);
        }
      }, 50);

      return () => {
        clearInterval(pollInterval);
        map.off('style.load', initLayers);
      };
    }
  }, [map]); // Only depend on map - runs once when map is available

  // Update vessel data whenever vessels change
  useEffect(() => {
    if (!map) return;

    // Wait for initialization to complete
    const updateData = () => {
      const source = map.getSource(VESSEL_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined;
      if (source) {
        const data = vesselsToGeoJSON(vessels);
        source.setData(data);
        console.log('Updated vessel data:', data.features.length, 'vessels');
      }
    };

    if (initialized.current) {
      updateData();
    } else {
      // If not initialized yet, wait a bit and try again
      const checkInterval = setInterval(() => {
        if (initialized.current) {
          clearInterval(checkInterval);
          updateData();
        }
      }, 100);

      // Clean up interval if component unmounts or vessels change before init completes
      return () => clearInterval(checkInterval);
    }
  }, [map, vessels]);

  // Update selected vessel filter
  useEffect(() => {
    if (!map || !initialized.current) return;

    if (map.getLayer(VESSEL_SELECTED_LAYER_ID)) {
      map.setFilter(VESSEL_SELECTED_LAYER_ID, [
        '==',
        ['get', 'mmsi'],
        selectedMmsi || '',
      ]);
    }
  }, [map, selectedMmsi]);

  return null;
}
