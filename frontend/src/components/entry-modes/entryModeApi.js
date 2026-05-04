/**
 * AF4 Entry Mode Adaptation API client
 */

const getApiBase = () => {
  return process.env.REACT_APP_BACKEND_URL || '';
};

export const entryModeApi = {
  // ========== Run & Get Data ==========
  async run() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/run`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to run entry mode adaptation');
    const data = await res.json();
    return data.data;
  },

  async getMetrics() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/metrics`);
    if (!res.ok) throw new Error('Failed to fetch metrics');
    const data = await res.json();
    return data.data;
  },

  async getEvaluations() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/evaluations`);
    if (!res.ok) throw new Error('Failed to fetch evaluations');
    const data = await res.json();
    return data;
  },

  async getActions() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/actions`);
    if (!res.ok) throw new Error('Failed to fetch actions');
    const data = await res.json();
    return data;
  },

  async getSummary() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/summary`);
    if (!res.ok) throw new Error('Failed to fetch summary');
    const data = await res.json();
    return data.data;
  },

  // ========== Submit ==========
  async submit(urgentOnly = false) {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urgent_only: urgentOnly }),
    });
    if (!res.ok) throw new Error('Failed to submit actions');
    const data = await res.json();
    return data.data;
  },

  // ========== Query ==========
  async getBroken() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/broken`);
    if (!res.ok) throw new Error('Failed to fetch broken modes');
    const data = await res.json();
    return data.data;
  },

  async getStrong() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/strong`);
    if (!res.ok) throw new Error('Failed to fetch strong modes');
    const data = await res.json();
    return data.data;
  },

  // ========== Health ==========
  async getHealth() {
    const res = await fetch(`${getApiBase()}/api/alpha-factory/entry-modes/health`);
    if (!res.ok) throw new Error('Failed to fetch health');
    const data = await res.json();
    return data.data;
  },
};

export default entryModeApi;
