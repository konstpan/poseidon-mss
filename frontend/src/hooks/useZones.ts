import { useQuery } from '@tanstack/react-query';
import { fetchZones, fetchZone } from '@/lib/api';

// Query keys for cache management
export const zoneKeys = {
  all: ['zones'] as const,
  lists: () => [...zoneKeys.all, 'list'] as const,
  list: (params?: { zoneType?: string; activeOnly?: boolean; securityLevel?: number }) =>
    [...zoneKeys.lists(), params] as const,
  details: () => [...zoneKeys.all, 'detail'] as const,
  detail: (id: string) => [...zoneKeys.details(), id] as const,
};

/**
 * Hook to fetch all zones
 * Zones don't change frequently, so we use a longer stale time
 */
export function useZones(params?: { zoneType?: string; activeOnly?: boolean; securityLevel?: number }) {
  return useQuery({
    queryKey: zoneKeys.list(params),
    queryFn: () => fetchZones(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

/**
 * Hook to fetch active zones only
 */
export function useActiveZones() {
  return useZones({ activeOnly: true });
}

/**
 * Hook to fetch a single zone's details
 */
export function useZone(zoneId: string | null) {
  return useQuery({
    queryKey: zoneKeys.detail(zoneId ?? ''),
    queryFn: () => fetchZone(zoneId!),
    enabled: !!zoneId,
    staleTime: 5 * 60 * 1000,
  });
}
