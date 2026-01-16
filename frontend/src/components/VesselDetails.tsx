import { useVessel } from '@/hooks/useVessels';
import { getVesselCategory, VESSEL_COLORS } from '@/types';

interface VesselDetailsProps {
  mmsi: string;
  onClose: () => void;
}

function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return 'N/A';
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function formatSpeed(speed: number | undefined | null): string {
  if (speed === undefined || speed === null) return 'N/A';
  return `${speed.toFixed(1)} kn`;
}

function formatCourse(course: number | undefined | null): string {
  if (course === undefined || course === null) return 'N/A';
  return `${course.toFixed(1)}°`;
}

function formatCoordinate(value: number | undefined | null, type: 'lat' | 'lon'): string {
  if (value === undefined || value === null) return 'N/A';
  const direction = type === 'lat' ? (value >= 0 ? 'N' : 'S') : (value >= 0 ? 'E' : 'W');
  return `${Math.abs(value).toFixed(4)}° ${direction}`;
}

export default function VesselDetails({ mmsi, onClose }: VesselDetailsProps) {
  const { data: vessel, isLoading, error } = useVessel(mmsi);

  const category = vessel ? getVesselCategory(vessel.ship_type) : 'other';
  const color = VESSEL_COLORS[category];

  return (
    <div className="absolute right-0 top-0 z-10 h-full w-80 bg-slate-800 shadow-xl md:w-96">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-700 p-4">
        <h2 className="text-lg font-semibold">Vessel Details</h2>
        <button
          onClick={onClose}
          className="rounded-lg p-1 text-slate-400 hover:bg-slate-700 hover:text-white"
          aria-label="Close"
        >
          <svg
            className="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="overflow-y-auto p-4" style={{ maxHeight: 'calc(100% - 64px)' }}>
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-blue-500" />
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-900/50 p-4 text-red-300">
            Failed to load vessel details
          </div>
        )}

        {vessel && (
          <div className="space-y-4">
            {/* Vessel Name and Type */}
            <div className="rounded-lg bg-slate-700 p-4">
              <div className="flex items-start gap-3">
                <div
                  className="mt-1 h-4 w-4 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">
                    {vessel.name || 'Unknown Vessel'}
                  </h3>
                  <p className="text-sm text-slate-400">
                    {vessel.ship_type_text || category.replace('_', ' ').toUpperCase()}
                  </p>
                </div>
              </div>
            </div>

            {/* Identification */}
            <div className="rounded-lg bg-slate-700 p-4">
              <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
                Identification
              </h4>
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-slate-400">MMSI</dt>
                  <dd className="font-mono">{vessel.mmsi}</dd>
                </div>
                {vessel.imo && (
                  <div className="flex justify-between">
                    <dt className="text-slate-400">IMO</dt>
                    <dd className="font-mono">{vessel.imo}</dd>
                  </div>
                )}
                {vessel.call_sign && (
                  <div className="flex justify-between">
                    <dt className="text-slate-400">Call Sign</dt>
                    <dd className="font-mono">{vessel.call_sign}</dd>
                  </div>
                )}
                {vessel.flag_state && (
                  <div className="flex justify-between">
                    <dt className="text-slate-400">Flag</dt>
                    <dd>{vessel.flag_state}</dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Position */}
            <div className="rounded-lg bg-slate-700 p-4">
              <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
                Position
              </h4>
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-slate-400">Latitude</dt>
                  <dd className="font-mono">{formatCoordinate(vessel.latitude, 'lat')}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Longitude</dt>
                  <dd className="font-mono">{formatCoordinate(vessel.longitude, 'lon')}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Last Seen</dt>
                  <dd className="text-sm">{formatDate(vessel.last_seen)}</dd>
                </div>
              </dl>
            </div>

            {/* Navigation */}
            <div className="rounded-lg bg-slate-700 p-4">
              <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
                Navigation
              </h4>
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-slate-400">Speed</dt>
                  <dd className="font-mono">{formatSpeed(vessel.speed)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Course</dt>
                  <dd className="font-mono">{formatCourse(vessel.course)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Heading</dt>
                  <dd className="font-mono">{formatCourse(vessel.heading)}</dd>
                </div>
              </dl>
            </div>

            {/* Voyage */}
            {(vessel.destination || vessel.eta) && (
              <div className="rounded-lg bg-slate-700 p-4">
                <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Voyage
                </h4>
                <dl className="space-y-2">
                  {vessel.destination && (
                    <div className="flex justify-between">
                      <dt className="text-slate-400">Destination</dt>
                      <dd>{vessel.destination}</dd>
                    </div>
                  )}
                  {vessel.eta && (
                    <div className="flex justify-between">
                      <dt className="text-slate-400">ETA</dt>
                      <dd className="text-sm">{formatDate(vessel.eta)}</dd>
                    </div>
                  )}
                </dl>
              </div>
            )}

            {/* Dimensions */}
            {(vessel.length || vessel.width || vessel.draught) && (
              <div className="rounded-lg bg-slate-700 p-4">
                <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Dimensions
                </h4>
                <dl className="space-y-2">
                  {vessel.length && (
                    <div className="flex justify-between">
                      <dt className="text-slate-400">Length</dt>
                      <dd>{vessel.length} m</dd>
                    </div>
                  )}
                  {vessel.width && (
                    <div className="flex justify-between">
                      <dt className="text-slate-400">Width</dt>
                      <dd>{vessel.width} m</dd>
                    </div>
                  )}
                  {vessel.draught && (
                    <div className="flex justify-between">
                      <dt className="text-slate-400">Draught</dt>
                      <dd>{vessel.draught} m</dd>
                    </div>
                  )}
                </dl>
              </div>
            )}

            {/* Risk Assessment */}
            {vessel.risk_score !== undefined && vessel.risk_score !== null && (
              <div className="rounded-lg bg-slate-700 p-4">
                <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Risk Assessment
                </h4>
                <dl className="space-y-2">
                  <div className="flex justify-between">
                    <dt className="text-slate-400">Risk Score</dt>
                    <dd
                      className={`font-semibold ${
                        vessel.risk_score > 70
                          ? 'text-red-400'
                          : vessel.risk_score > 40
                          ? 'text-yellow-400'
                          : 'text-green-400'
                      }`}
                    >
                      {vessel.risk_score.toFixed(0)}
                    </dd>
                  </div>
                  {vessel.risk_category && (
                    <div className="flex justify-between">
                      <dt className="text-slate-400">Category</dt>
                      <dd>{vessel.risk_category}</dd>
                    </div>
                  )}
                </dl>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
