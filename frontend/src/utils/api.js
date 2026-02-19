/**
 * api.js — REST API helper functions.
 *
 * These complement the WebSocket for operations that don't need
 * streaming (e.g., fetching full history, updating config).
 */

const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  start:      (speed)        => request('/start', { method: 'POST', body: JSON.stringify({ speed }) }),
  pause:      ()             => request('/pause', { method: 'POST' }),
  stop:       ()             => request('/stop',  { method: 'POST' }),
  reset:      (cfg = {})     => request('/reset', { method: 'POST', body: JSON.stringify(cfg) }),
  setControls:(inlet_temp, airflow) =>
    request('/controls', { method: 'POST', body: JSON.stringify({ inlet_temp, airflow }) }),
  setSpeed:   (speed)        => request('/speed', { method: 'POST', body: JSON.stringify({ speed }) }),
  status:     ()             => request('/status'),
  snapshot:   ()             => request('/snapshot'),
  history:    ()             => request('/history'),
  getConfig:  ()             => request('/config'),
  setConfig:  (cfg)          => request('/config', { method: 'POST', body: JSON.stringify(cfg) }),
};
