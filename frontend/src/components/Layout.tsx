import { Outlet } from 'react-router-dom';
import { useVesselStore } from '@/stores/useVesselStore';

export default function Layout() {
  const isConnected = useVesselStore((state) => state.isConnected);

  return (
    <div className="flex h-screen flex-col bg-slate-900 text-white">
      {/* Header */}
      <header className="flex h-14 items-center justify-between border-b border-slate-700 bg-slate-800 px-4">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-maritime-400">
            Poseidon MSS
          </h1>
          <span className="text-sm text-slate-400">
            Maritime Security System
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div
              className={`h-2 w-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm text-slate-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
