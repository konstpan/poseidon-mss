import { create } from 'zustand';
import type { BoundingBox } from '@/types';

interface MapState {
  // Map bounds for bbox queries
  bounds: BoundingBox | null;

  // Selected vessel MMSI
  selectedVesselMmsi: string | null;

  // Map center and zoom
  center: [number, number]; // [lng, lat]
  zoom: number;

  // UI state
  isDetailsPanelOpen: boolean;

  // Actions
  setBounds: (bounds: BoundingBox | null) => void;
  selectVessel: (mmsi: string | null) => void;
  setCenter: (center: [number, number]) => void;
  setZoom: (zoom: number) => void;
  setDetailsPanelOpen: (open: boolean) => void;
}

// Default center: Thessaloniki
const DEFAULT_CENTER: [number, number] = [22.9444, 40.6401];
const DEFAULT_ZOOM = 11;

export const useMapStore = create<MapState>((set) => ({
  bounds: null,
  selectedVesselMmsi: null,
  center: DEFAULT_CENTER,
  zoom: DEFAULT_ZOOM,
  isDetailsPanelOpen: false,

  setBounds: (bounds) => set({ bounds }),

  selectVessel: (mmsi) => set({
    selectedVesselMmsi: mmsi,
    isDetailsPanelOpen: mmsi !== null,
  }),

  setCenter: (center) => set({ center }),

  setZoom: (zoom) => set({ zoom }),

  setDetailsPanelOpen: (open) => set({
    isDetailsPanelOpen: open,
    // Clear selection when closing panel
    selectedVesselMmsi: open ? undefined : null,
  }),
}));
