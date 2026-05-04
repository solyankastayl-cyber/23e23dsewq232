/**
 * Validation API client for Live Validation Layer (V1)
 */

const getApiBase = () => {
  return process.env.REACT_APP_BACKEND_URL || '';
};

export const validationApi = {
  // ========== Metrics ==========
  async getMetrics(symbol = null) {
    const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : '';
    const res = await fetch(`${getApiBase()}/api/validation/metrics${query}`);
    if (!res.ok) throw new Error('Failed to fetch validation metrics');
    const data = await res.json();
    return data.data;
  },

  async getMetricsBySymbol() {
    const res = await fetch(`${getApiBase()}/api/validation/metrics/by-symbol`);
    if (!res.ok) throw new Error('Failed to fetch metrics by symbol');
    const data = await res.json();
    return data.data;
  },

  // ========== Shadow Trades ==========
  async getRecentShadowTrades(symbol = null, limit = 20) {
    const params = new URLSearchParams();
    if (symbol) params.set('symbol', symbol);
    if (limit) params.set('limit', limit.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    
    const res = await fetch(`${getApiBase()}/api/validation/shadow/recent${query}`);
    if (!res.ok) throw new Error('Failed to fetch shadow trades');
    const data = await res.json();
    return data.data;
  },

  async getPendingShadowTrades() {
    const res = await fetch(`${getApiBase()}/api/validation/shadow/pending`);
    if (!res.ok) throw new Error('Failed to fetch pending trades');
    const data = await res.json();
    return data.data;
  },

  async getActiveShadowTrades() {
    const res = await fetch(`${getApiBase()}/api/validation/shadow/active`);
    if (!res.ok) throw new Error('Failed to fetch active trades');
    const data = await res.json();
    return data.data;
  },

  async getShadowTrade(shadowId) {
    const res = await fetch(`${getApiBase()}/api/validation/shadow/${shadowId}`);
    if (!res.ok) throw new Error('Shadow trade not found');
    const data = await res.json();
    return data.data;
  },

  async createShadowTrade(terminalState) {
    const res = await fetch(`${getApiBase()}/api/validation/shadow/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ terminal_state: terminalState }),
    });
    if (!res.ok) throw new Error('Failed to create shadow trade');
    const data = await res.json();
    return data.data;
  },

  async createManualShadowTrade({ symbol, direction, plannedEntry, plannedStop, plannedTarget, timeframe = '4H', entryMode = 'ENTER_ON_CLOSE' }) {
    const res = await fetch(`${getApiBase()}/api/validation/shadow/create-manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol,
        direction,
        planned_entry: plannedEntry,
        planned_stop: plannedStop,
        planned_target: plannedTarget,
        timeframe,
        entry_mode: entryMode,
      }),
    });
    if (!res.ok) throw new Error('Failed to create shadow trade');
    const data = await res.json();
    return data.data;
  },

  async cancelShadowTrade(shadowId) {
    const res = await fetch(`${getApiBase()}/api/validation/shadow/${shadowId}/cancel`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to cancel shadow trade');
    const data = await res.json();
    return data.data;
  },

  // ========== Validation Results ==========
  async getRecentResults(symbol = null, limit = 20) {
    const params = new URLSearchParams();
    if (symbol) params.set('symbol', symbol);
    if (limit) params.set('limit', limit.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    
    const res = await fetch(`${getApiBase()}/api/validation/results/recent${query}`);
    if (!res.ok) throw new Error('Failed to fetch validation results');
    const data = await res.json();
    return data.data;
  },

  async getValidationResult(shadowId) {
    const res = await fetch(`${getApiBase()}/api/validation/results/${shadowId}`);
    if (!res.ok) throw new Error('Validation result not found');
    const data = await res.json();
    return data.data;
  },

  // ========== Evaluation ==========
  async evaluateShadowTrade(shadowId, marketPath) {
    const res = await fetch(`${getApiBase()}/api/validation/shadow/${shadowId}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ market_path: marketPath }),
    });
    if (!res.ok) throw new Error('Failed to evaluate shadow trade');
    const data = await res.json();
    return data.data;
  },

  // ========== Summary & Stats ==========
  async getSummary() {
    const res = await fetch(`${getApiBase()}/api/validation/summary`);
    if (!res.ok) throw new Error('Failed to fetch summary');
    const data = await res.json();
    return data.data;
  },

  async getStats() {
    const res = await fetch(`${getApiBase()}/api/validation/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    const data = await res.json();
    return data.data;
  },

  async getCombinedRecent(symbol = null, limit = 20) {
    const params = new URLSearchParams();
    if (symbol) params.set('symbol', symbol);
    if (limit) params.set('limit', limit.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    
    const res = await fetch(`${getApiBase()}/api/validation/combined/recent${query}`);
    if (!res.ok) throw new Error('Failed to fetch combined data');
    const data = await res.json();
    return data.data;
  },

  // ========== Admin ==========
  async reset() {
    const res = await fetch(`${getApiBase()}/api/validation/reset`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to reset validation');
    const data = await res.json();
    return data;
  },
};

export default validationApi;
