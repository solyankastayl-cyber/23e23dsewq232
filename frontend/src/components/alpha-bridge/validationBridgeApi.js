/**
 * AF3 Validation Bridge API client
 */

const getApiBase = () => {
  return process.env.REACT_APP_BACKEND_URL || '';
};

export const validationBridgeApi = {
  // ========== Truths ==========
  async getSymbolsTruth() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/validation-bridge/symbols`);
    if (!res.ok) throw new Error('Failed to fetch symbols truth');
    const data = await res.json();
    return data.data;
  },

  async getEntryModesTruth() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/validation-bridge/entry-modes`);
    if (!res.ok) throw new Error('Failed to fetch entry modes truth');
    const data = await res.json();
    return data.data;
  },

  // ========== Actions ==========
  async getActions() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/validation-bridge/actions`);
    if (!res.ok) throw new Error('Failed to fetch actions');
    const data = await res.json();
    return data.data;
  },

  // ========== Full Evaluation ==========
  async getFullEvaluation() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/validation-bridge/full-evaluation`);
    if (!res.ok) throw new Error('Failed to fetch full evaluation');
    const data = await res.json();
    return data.data;
  },

  // ========== Summary ==========
  async getSummary() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/validation-bridge/summary`);
    if (!res.ok) throw new Error('Failed to fetch summary');
    const data = await res.json();
    return data.data;
  },

  // ========== Submit to Control ==========
  async submitActions(urgentOnly = false) {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/validation-bridge/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filter_urgent_only: urgentOnly }),
    });
    if (!res.ok) throw new Error('Failed to submit actions');
    const data = await res.json();
    return data.data;
  },

  // ========== Health ==========
  async getHealth() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/validation-bridge/health`);
    if (!res.ok) throw new Error('Failed to fetch health');
    const data = await res.json();
    return data.data;
  },
};

export default validationBridgeApi;
