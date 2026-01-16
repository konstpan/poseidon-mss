import { useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useVesselStore } from '@/stores/useVesselStore';
import type { Vessel, Alert } from '@/types';

export function useSocket() {
  const socketRef = useRef<Socket | null>(null);
  const { updateVessel, addAlert, setConnected } = useVesselStore();

  useEffect(() => {
    const socket = io('/', {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('Socket connected');
      setConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Socket disconnected');
      setConnected(false);
    });

    socket.on('vessel:update', (vessel: Vessel) => {
      updateVessel(vessel);
    });

    socket.on('alert:new', (alert: Alert) => {
      addAlert(alert);
    });

    return () => {
      socket.disconnect();
    };
  }, [updateVessel, addAlert, setConnected]);

  return socketRef.current;
}
