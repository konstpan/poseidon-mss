import { useQuery } from '@tanstack/react-query';
import { fetchVessels, fetchVessel, fetchVesselTrack, type FetchVesselsParams, type FetchVesselTrackParams } from '@/lib/api';
import type { BoundingBox } from '@/types';

// Query keys for cache management
export const vesselKeys = {
  all: ['vessels'] as const,
  lists: () => [...vesselKeys.all, 'list'] as const,
  list: (params?: FetchVesselsParams) => [...vesselKeys.lists(), params] as const,
  details: () => [...vesselKeys.all, 'detail'] as const,
  detail: (mmsi: string) => [...vesselKeys.details(), mmsi] as const,
  tracks: () => [...vesselKeys.all, 'track'] as const,
  track: (mmsi: string, params?: FetchVesselTrackParams) => [...vesselKeys.tracks(), mmsi, params] as const,
};

/**
 * Hook to fetch vessels with optional filtering
 * Auto-refetches every 60 seconds
 */
export function useVessels(params?: FetchVesselsParams) {
  return useQuery({
    queryKey: vesselKeys.list(params),
    queryFn: () => fetchVessels(params),
    refetchInterval: 60 * 1000, // 60 seconds
    staleTime: 30 * 1000, // Consider data stale after 30 seconds
  });
}

/**
 * Hook to fetch vessels within a bounding box
 * Useful for fetching only visible vessels on map
 */
export function useVesselsInBounds(bbox: BoundingBox | null, enabled = true) {
  return useQuery({
    queryKey: vesselKeys.list(bbox ? { bbox } : undefined),
    queryFn: () => fetchVessels(bbox ? { bbox, limit: 500 } : { limit: 500 }),
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
    enabled,
  });
}

/**
 * Hook to fetch a single vessel's details
 */
export function useVessel(mmsi: string | null) {
  return useQuery({
    queryKey: vesselKeys.detail(mmsi ?? ''),
    queryFn: () => fetchVessel(mmsi!),
    enabled: !!mmsi,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch vessel track history
 */
export function useVesselTrack(mmsi: string | null, params?: FetchVesselTrackParams) {
  return useQuery({
    queryKey: vesselKeys.track(mmsi ?? '', params),
    queryFn: () => fetchVesselTrack(mmsi!, params),
    enabled: !!mmsi,
    staleTime: 60 * 1000,
  });
}
