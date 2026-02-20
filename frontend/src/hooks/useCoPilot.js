/**
 * useCoPilot.js — React hook that accumulates Co-Pilot alerts from the
 * telemetry stream and deduplicates them.
 *
 * Each WebSocket frame may contain an `alerts` array of new alerts.
 * This hook maintains a rolling history, prevents duplicates (same tag+time),
 * and provides a clear function.
 */

import { useState, useRef, useCallback } from "react";

const MAX_ALERTS = 50;

/**
 * @param {object|null} state — latest telemetry frame from useWebSocket
 * @returns {{ alerts, clearAlerts, alertCount }}
 */
export function useCoPilot(state) {
  const [alerts, setAlerts] = useState([]);
  const seenRef = useRef(new Set());
  const lastProcessedRef = useRef(null);

  // Process new alerts from the current state frame
  // Called on every render where state changes, but only adds truly new alerts
  if (state && state.alerts && state.alerts.length > 0) {
    const frameKey = `${state.time}`;
    if (frameKey !== lastProcessedRef.current) {
      lastProcessedRef.current = frameKey;
      const newAlerts = [];

      for (const alert of state.alerts) {
        const key = `${alert.tag}-${alert.time}`;
        if (!seenRef.current.has(key)) {
          seenRef.current.add(key);
          newAlerts.push(alert);
        }
      }

      if (newAlerts.length > 0) {
        // Use functional update so we don't need alerts in deps
        setAlerts((prev) => {
          const combined = [...prev, ...newAlerts];
          // Trim to max
          return combined.length > MAX_ALERTS
            ? combined.slice(combined.length - MAX_ALERTS)
            : combined;
        });
      }
    }
  }

  const clearAlerts = useCallback(() => {
    setAlerts([]);
    seenRef.current.clear();
    lastProcessedRef.current = null;
  }, []);

  return {
    alerts,
    clearAlerts,
    alertCount: alerts.length,
  };
}
