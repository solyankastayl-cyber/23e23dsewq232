/**
 * System Control Data Layer — PHASE F3
 * 
 * Unified data service for System Control Panel.
 * UI → System Data Layer → Backend API
 */

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

const fetchJSON = async (url, options = {}, timeout = 10000) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(id);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
};

const safe = async (fn, fallback = null) => {
  try { return await fn(); } catch (e) {
    console.warn('[SystemService]', e.message);
    return fallback;
  }
};

export const SystemService = {
  async getSystemState(symbol = 'BTCUSDT') {
    const [controlState, controlSummary, killSwitchState, killSwitchStatus, breakerStatus, breakerRules, alerts] = await Promise.all([
      safe(() => fetchJSON(`${API_BASE}/api/v1/control/state/${symbol}`)),
      safe(() => fetchJSON(`${API_BASE}/api/v1/control/summary`)),
      safe(() => fetchJSON(`${API_BASE}/api/v1/safety/kill-switch/state`)),
      safe(() => fetchJSON(`${API_BASE}/api/v1/safety/kill-switch/status`)),
      safe(() => fetchJSON(`${API_BASE}/api/v1/safety/circuit-breaker/status`)),
      safe(() => fetchJSON(`${API_BASE}/api/v1/safety/circuit-breaker/rules`)),
      safe(() => fetchJSON(`${API_BASE}/api/v1/control/alerts/${symbol}?active_only=false&limit=50`)),
    ]);

    return {
      control: controlState,
      summary: controlSummary,
      killSwitch: {
        state: killSwitchState,
        status: killSwitchStatus,
      },
      circuitBreaker: {
        status: breakerStatus,
        rules: breakerRules?.rules || [],
      },
      alerts: alerts,
    };
  },

  async activateKillSwitch(reason = '', emergency = false) {
    return fetchJSON(`${API_BASE}/api/v1/safety/kill-switch/activate`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trigger: 'MANUAL', reason, user: 'admin', emergency }),
    });
  },

  async deactivateKillSwitch() {
    return fetchJSON(`${API_BASE}/api/v1/safety/kill-switch/deactivate`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user: 'admin', confirm_safe: true }),
    });
  },

  async enterSafeMode(reason = '') {
    return fetchJSON(`${API_BASE}/api/v1/safety/kill-switch/safe-mode`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason, user: 'admin' }),
    });
  },

  async resetBreakers() {
    return fetchJSON(`${API_BASE}/api/v1/safety/circuit-breaker/reset`, { method: 'POST' });
  },

  async recomputeState(symbol) {
    return fetchJSON(`${API_BASE}/api/v1/control/recompute/${symbol}`, { method: 'POST' });
  },
};

export default SystemService;
