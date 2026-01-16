import { useEffect, useRef, useCallback, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import { useVessels } from '@/hooks/useVessels';
import { useZones } from '@/hooks/useZones';
import { useMapStore } from '@/stores/useMapStore';
import { useVesselStore } from '@/stores/useVesselStore';
import VesselLayer from '@/components/Map/VesselLayer';
import ZoneLayer from '@/components/Map/ZoneLayer';
import VesselDetails from '@/components/VesselDetails';
import { getVesselCategory, VESSEL_COLORS } from '@/types';

// Thermaikos Gulf coordinates (sea area south of Thessaloniki)
// Centered on the shipping area where emulated vessels spawn
const DEFAULT_CENTER: [number, number] = [22.88, 40.55];
const DEFAULT_ZOOM = 11;

export default function Dashboard() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Map store
  const { selectedVesselMmsi, selectVessel, isDetailsPanelOpen, setDetailsPanelOpen } = useMapStore();

  // Vessel store (for legacy WebSocket updates)
  const alerts = useVesselStore((state) => state.alerts);

  // Fetch vessels from API
  const { data: vesselsData, isLoading: vesselsLoading, error: vesselsError } = useVessels({ limit: 500 });

  // Fetch zones from API
  const { data: zonesData, isLoading: zonesLoading } = useZones({ activeOnly: true });

  // Get vessels from API response
  const vessels = vesselsData?.vessels ?? [];

  // Store vessels in a ref for stable callback access
  const vesselsRef = useRef(vessels);
  vesselsRef.current = vessels;

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const token = import.meta.env.VITE_MAPBOX_TOKEN;
    if (!token) {
      console.warn('Mapbox token not configured');
      return;
    }

    mapboxgl.accessToken = token;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.current.addControl(new mapboxgl.ScaleControl(), 'bottom-left');

    map.current.on('load', () => {
      setMapLoaded(true);
    });

    return () => {
      map.current?.remove();
      map.current = null;
      setMapLoaded(false);
    };
  }, []);

  // Handle vessel click - stable callback that uses refs
  const handleVesselClick = useCallback(
    (mmsi: string) => {
      selectVessel(mmsi);

      // Fly to vessel using ref to avoid dependency on vessels array
      const vessel = vesselsRef.current.find((v) => v.mmsi === mmsi);
      if (vessel && vessel.latitude && vessel.longitude && map.current) {
        map.current.flyTo({
          center: [vessel.longitude, vessel.latitude],
          zoom: 13,
          duration: 1000,
        });
      }
    },
    [selectVessel] // Only depends on selectVessel, not vessels
  );

  // Handle close details panel
  const handleCloseDetails = useCallback(() => {
    setDetailsPanelOpen(false);
    selectVessel(null);
  }, [setDetailsPanelOpen, selectVessel]);

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="w-80 flex-shrink-0 overflow-y-auto border-r border-slate-700 bg-slate-800">
        {/* Vessel list */}
        <div className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Vessels ({vessels.length})
            </h2>
            {vesselsLoading && (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-blue-500" />
            )}
          </div>

          {vesselsError && (
            <div className="mb-3 rounded bg-red-900/50 px-3 py-2 text-sm text-red-300">
              Failed to load vessels
            </div>
          )}

          {vessels.length === 0 && !vesselsLoading ? (
            <p className="text-sm text-slate-500">No vessels tracked</p>
          ) : (
            <ul className="space-y-2">
              {vessels.slice(0, 50).map((vessel) => {
                const category = getVesselCategory(vessel.ship_type);
                const color = VESSEL_COLORS[category];
                const isSelected = selectedVesselMmsi === vessel.mmsi;

                return (
                  <li
                    key={vessel.mmsi}
                    onClick={() => handleVesselClick(vessel.mmsi)}
                    className={`cursor-pointer rounded-lg p-3 transition-colors ${
                      isSelected
                        ? 'bg-blue-900/50 ring-1 ring-blue-500'
                        : 'bg-slate-700 hover:bg-slate-600'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span className="font-medium">
                        {vessel.name || vessel.mmsi}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-sm text-slate-400">
                      <span>MMSI: {vessel.mmsi}</span>
                      {vessel.speed !== undefined && vessel.speed !== null && (
                        <span>{vessel.speed.toFixed(1)} kn</span>
                      )}
                    </div>
                  </li>
                );
              })}
              {vessels.length > 50 && (
                <li className="px-3 py-2 text-center text-sm text-slate-500">
                  +{vessels.length - 50} more vessels
                </li>
              )}
            </ul>
          )}
        </div>

        {/* Zones */}
        <div className="border-t border-slate-700 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Zones ({zonesData?.total ?? 0})
            </h2>
            {zonesLoading && (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-blue-500" />
            )}
          </div>

          {zonesData && zonesData.features.length > 0 ? (
            <ul className="space-y-2">
              {zonesData.features.slice(0, 10).map((zone) => (
                <li
                  key={zone.properties.id}
                  className="rounded-lg bg-slate-700 p-3"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="h-3 w-3 rounded"
                      style={{
                        backgroundColor: zone.properties.display_color || '#6B7280',
                      }}
                    />
                    <span className="font-medium">{zone.properties.name}</span>
                  </div>
                  <div className="mt-1 text-sm text-slate-400">
                    {zone.properties.zone_type_text} - {zone.properties.security_level_text}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No zones configured</p>
          )}
        </div>

        {/* Alerts */}
        <div className="border-t border-slate-700 p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Alerts ({alerts.length})
          </h2>
          {alerts.length === 0 ? (
            <p className="text-sm text-slate-500">No active alerts</p>
          ) : (
            <ul className="space-y-2">
              {alerts.slice(0, 10).map((alert) => (
                <li
                  key={alert.id}
                  className={`rounded-lg p-3 ${
                    alert.severity === 'critical'
                      ? 'bg-red-900/50'
                      : alert.severity === 'high'
                      ? 'bg-orange-900/50'
                      : 'bg-slate-700'
                  }`}
                >
                  <div className="font-medium">{alert.type}</div>
                  <div className="text-sm text-slate-400">{alert.message}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* Map */}
      <div className="relative flex-1">
        <div ref={mapContainer} className="h-full w-full" />

        {/* Map layers - render when map is loaded */}
        {mapLoaded && (
          <>
            <ZoneLayer map={map.current} zones={zonesData ?? null} />
            <VesselLayer
              map={map.current}
              vessels={vessels}
              selectedMmsi={selectedVesselMmsi}
              onVesselClick={handleVesselClick}
            />
          </>
        )}

        {/* Loading overlay */}
        {vesselsLoading && !vessels.length && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50">
            <div className="flex items-center gap-3 rounded-lg bg-slate-800 px-6 py-4">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-600 border-t-blue-500" />
              <span>Loading vessels...</span>
            </div>
          </div>
        )}

        {/* No token warning */}
        {!import.meta.env.VITE_MAPBOX_TOKEN && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-800">
            <div className="text-center">
              <p className="text-lg text-slate-400">Map not configured</p>
              <p className="text-sm text-slate-500">
                Set VITE_MAPBOX_TOKEN in your environment
              </p>
            </div>
          </div>
        )}

        {/* Vessel details panel */}
        {isDetailsPanelOpen && selectedVesselMmsi && (
          <VesselDetails
            mmsi={selectedVesselMmsi}
            onClose={handleCloseDetails}
          />
        )}

        {/* Legend */}
        <div className="absolute bottom-8 right-4 rounded-lg bg-slate-800/90 p-3 text-sm backdrop-blur-sm">
          <h4 className="mb-2 font-semibold text-slate-300">Vessel Types</h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#3B82F6' }} />
              <span className="text-slate-400">Cargo</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#EF4444' }} />
              <span className="text-slate-400">Tanker</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#10B981' }} />
              <span className="text-slate-400">Passenger</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#F59E0B' }} />
              <span className="text-slate-400">Fishing</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#6B7280' }} />
              <span className="text-slate-400">Other</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
