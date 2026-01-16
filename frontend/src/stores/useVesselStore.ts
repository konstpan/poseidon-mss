import { create } from 'zustand';
import type { Vessel, Alert } from '@/types';

interface VesselState {
  vessels: Map<string, Vessel>;
  selectedVessel: string | null;
  alerts: Alert[];
  isConnected: boolean;

  // Actions
  setVessels: (vessels: Vessel[]) => void;
  updateVessel: (vessel: Vessel) => void;
  selectVessel: (mmsi: string | null) => void;
  addAlert: (alert: Alert) => void;
  acknowledgeAlert: (alertId: string) => void;
  setConnected: (connected: boolean) => void;
}

export const useVesselStore = create<VesselState>((set) => ({
  vessels: new Map(),
  selectedVessel: null,
  alerts: [],
  isConnected: false,

  setVessels: (vessels) =>
    set({
      vessels: new Map(vessels.map((v) => [v.mmsi, v])),
    }),

  updateVessel: (vessel) =>
    set((state) => {
      const newVessels = new Map(state.vessels);
      newVessels.set(vessel.mmsi, vessel);
      return { vessels: newVessels };
    }),

  selectVessel: (mmsi) => set({ selectedVessel: mmsi }),

  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts].slice(0, 100),
    })),

  acknowledgeAlert: (alertId) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === alertId ? { ...a, acknowledged: true } : a
      ),
    })),

  setConnected: (connected) => set({ isConnected: connected }),
}));
