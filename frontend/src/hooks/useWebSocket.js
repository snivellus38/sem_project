/**
 * useWebSocket.js — React hook for bidirectional WebSocket telemetry.
 *
 * Connects to ws://host/ws/telemetry and provides:
 *   - Real-time state updates (latest + history buffer)
 *   - Command sending (start, pause, stop, reset, set_controls, set_speed)
 *   - Connection status tracking
 */

import { useEffect, useRef, useCallback, useState } from 'react';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/telemetry`;
const RECONNECT_DELAY = 2000;
const MAX_HISTORY = 600; // ~1 min at 10 Hz

/**
 * @returns {{ state, history, status, simStatus, send, sendCmd }}
 */
export function useWebSocket() {
  const [state, setState] = useState(null);
  const [history, setHistory] = useState([]);
  const [status, setStatus] = useState('disconnected'); // disconnected | connecting | connected
  const [simStatus, setSimStatus] = useState('idle');

  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const historyRef = useRef([]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      console.log('[WS] connected');
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);

        // Server pushes telemetry frames with a "time" field,
        // or status/response objects with a "status" field.
        if (data.status !== undefined) {
          setSimStatus(data.status);
        }

        if (data.time !== undefined) {
          // Telemetry frame
          setState(data);
          historyRef.current = [...historyRef.current.slice(-(MAX_HISTORY - 1)), data];
          setHistory(historyRef.current);
        } else if (data.state) {
          // Status response that includes embedded state
          if (data.state.time !== undefined) {
            setState(data.state);
          }
        }
      } catch (e) {
        console.warn('[WS] parse error', e);
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      console.log('[WS] disconnected, reconnecting...');
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = (err) => {
      console.error('[WS] error', err);
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  /** Send raw JSON to the server */
  const send = useCallback((obj) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(obj));
    }
  }, []);

  /** Convenience: send a command */
  const sendCmd = useCallback(
    (cmd, params = {}) => send({ cmd, ...params }),
    [send],
  );

  /** Reset local history buffer */
  const clearHistory = useCallback(() => {
    historyRef.current = [];
    setHistory([]);
    setState(null);
  }, []);

  return { state, history, status, simStatus, send, sendCmd, clearHistory };
}
