import { useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useVesselStore } from '@/stores/useVesselStore';
import type { Vessel, Alert } from '@/types';

export function useSocket() {
  const socketRef = useRef<Socket | null>(null);
  const { updateVessel, addAlert, setConnected } = useVesselStore();

  useEffect(() => {
    // Connect directly to backend for WebSocket
    // In Docker: frontend proxy may have issues with WS upgrades
    const backendUrl = window.location.hostname === 'localhost'
      ? 'http://localhost:8000'
      : window.location.origin;

    const socket = io(backendUrl, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('Socket connected');
      setConnected(true);
    });

    socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      setConnected(false);
    });

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error.message);
    });

    socket.on('vessel:update', (vessel: Vessel) => {
      console.log('Received vessel:update', vessel.mmsi);
      updateVessel(vessel);
    });

    socket.on('alert:new', (alert: Alert) => {
      console.log('Received alert:new', alert.id, alert.type);
      addAlert(alert);
    });

    return () => {
      socket.disconnect();
    };
  }, [updateVessel, addAlert, setConnected]);

  return socketRef.current;
}
