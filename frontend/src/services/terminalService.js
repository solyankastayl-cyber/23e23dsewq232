/**
 * Terminal Data Layer — PHASE F2
 * 
 * Unified data service for Trading Terminal.
 * UI → Terminal Data Layer → Backend API
 */

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

// ============================================
// DEFAULT STATE
// ============================================

const DEFAULT_TERMINAL_STATE = {
  portfolio: {
    equity: { total: 0, available_margin: 0, used_margin: 0 },
    balances: [],
    positions: [],
    exposure: {
      by_asset: {},
      by_category: {},
      directional: { long_exposure: 0, short_exposure: 0, net_exposure: 0 },
      concentration: { max_asset: '', max_weight: 0 },
    },
    metrics: {
      pnl: { daily: 0, daily_pct: 0, weekly: 0, total_realized: 0, total_unrealized: 0 },
      leverage: { current: 0, max: 5 },
      risk: { var_95: null, cvar_95: null },
      performance: { sharpe_ratio: null, sortino_ratio: null },
    },
  },
  execution: {
    plan: null,
    active: null,
    history: [],
    summary: {
      has_active_plan: false,
      total_plans: 0,
      approved_count: 0,
      blocked_count: 0,
      executed_count: 0,
      risk_distribution: {},
      execution_type_distribution: {},
    },
  },
  system: {
    mode: 'APPROVAL',
    health: 'OK',
  },
  loading: false,
  error: null,
  lastUpdated: 0,
};

// ============================================
// HELPERS
// ============================================

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
    console.warn('[TerminalService]', e.message);
    return fallback;
  }
};

const createFreshState = () => JSON.parse(JSON.stringify(DEFAULT_TERMINAL_STATE));

// ============================================
// TERMINAL SERVICE
// ============================================

export const TerminalService = {
  /**
   * Get full terminal state (portfolio + execution)
   */
  async getTerminalState(symbol = 'BTCUSDT') {
    const state = createFreshState();
    state.loading = true;

    try {
      // Fetch all data in parallel
      const [
        portfolioState,
        positions,
        exposure,
        metrics,
        executionPlan,
        executionActive,
        executionHistory,
        executionSummary,
      ] = await Promise.all([
        safe(() => fetchJSON(`${API_BASE}/api/portfolio/state`)),
        safe(() => fetchJSON(`${API_BASE}/api/portfolio/positions`)),
        safe(() => fetchJSON(`${API_BASE}/api/portfolio/exposure`)),
        safe(() => fetchJSON(`${API_BASE}/api/portfolio/metrics`)),
        safe(() => fetchJSON(`${API_BASE}/api/v1/execution/plan/${symbol}`)),
        safe(() => fetchJSON(`${API_BASE}/api/v1/execution/active/${symbol}`)),
        safe(() => fetchJSON(`${API_BASE}/api/v1/execution/history/${symbol}?limit=50`)),
        safe(() => fetchJSON(`${API_BASE}/api/v1/execution/summary/${symbol}`)),
      ]);

      // Portfolio State
      if (portfolioState) {
        state.portfolio.equity = portfolioState.equity || state.portfolio.equity;
        state.portfolio.balances = (portfolioState.balances || []).map(b => ({
          asset: b.asset,
          total: b.total_amount,
          free: b.total_free,
          locked: b.total_locked,
          usdValue: b.usd_value,
          weight: Math.round((b.weight_pct || 0) * 100),
        }));
      }

      // Positions
      if (positions && positions.positions) {
        state.portfolio.positions = positions.positions.map(p => ({
          id: p.position_id,
          symbol: p.symbol,
          exchange: p.exchange,
          side: p.side,
          size: p.size,
          entryPrice: p.entry_price,
          markPrice: p.mark_price,
          pnl: p.unrealized_pnl,
          pnlPct: p.unrealized_pnl_pct,
          leverage: p.leverage,
          marginType: p.margin_type,
          liquidationPrice: p.liquidation_price,
        }));
      }

      // Exposure
      if (exposure) {
        state.portfolio.exposure = {
          by_asset: exposure.by_asset || {},
          by_category: exposure.by_category || {},
          by_exchange: exposure.by_exchange || {},
          directional: exposure.directional || state.portfolio.exposure.directional,
          concentration: exposure.concentration || state.portfolio.exposure.concentration,
        };
      }

      // Metrics
      if (metrics) {
        state.portfolio.metrics = {
          pnl: metrics.pnl || state.portfolio.metrics.pnl,
          leverage: metrics.leverage || state.portfolio.metrics.leverage,
          risk: metrics.risk || state.portfolio.metrics.risk,
          performance: metrics.performance || state.portfolio.metrics.performance,
        };
      }

      // Execution Plan
      if (executionPlan && executionPlan.status === 'ok') {
        state.execution.plan = {
          symbol: executionPlan.symbol,
          strategy: executionPlan.strategy,
          direction: executionPlan.direction,
          positionSize: executionPlan.position_size_usd,
          positionSizeAdjusted: executionPlan.position_size_adjusted,
          entryPrice: executionPlan.entry_price,
          stopLoss: executionPlan.stop_loss,
          takeProfit: executionPlan.take_profit,
          riskLevel: executionPlan.risk_level,
          riskReward: executionPlan.risk_reward_ratio,
          executionType: executionPlan.execution_type,
          confidence: executionPlan.confidence,
          reliability: executionPlan.reliability,
          status: executionPlan.plan_status,
          blockedReason: executionPlan.blocked_reason,
          impactAdjusted: executionPlan.impact_adjusted,
          sizeReductionPct: executionPlan.size_reduction_pct,
          typeChanged: executionPlan.type_changed,
          reason: executionPlan.reason,
          timestamp: executionPlan.timestamp,
        };
      }

      // Active Plan
      if (executionActive && executionActive.has_active_plan) {
        state.execution.active = {
          symbol: executionActive.symbol,
          strategy: executionActive.strategy,
          direction: executionActive.direction,
          positionSize: executionActive.position_size_adjusted,
          entryPrice: executionActive.entry_price,
          stopLoss: executionActive.stop_loss,
          takeProfit: executionActive.take_profit,
          executionType: executionActive.execution_type,
          status: executionActive.plan_status,
        };
      }

      // History
      if (executionHistory && executionHistory.records) {
        state.execution.history = executionHistory.records.map(r => ({
          strategy: r.strategy,
          direction: r.direction,
          positionSize: r.position_size_usd,
          entryPrice: r.entry_price,
          riskLevel: r.risk_level,
          executionType: r.execution_type,
          status: r.status,
          timestamp: r.timestamp,
        }));
      }

      // Summary
      if (executionSummary && executionSummary.status === 'ok') {
        state.execution.summary = {
          has_active_plan: executionSummary.has_active_plan,
          current_direction: executionSummary.current_direction,
          current_status: executionSummary.current_status,
          total_plans: executionSummary.total_plans,
          approved_count: executionSummary.approved_count,
          blocked_count: executionSummary.blocked_count,
          executed_count: executionSummary.executed_count,
          risk_distribution: executionSummary.risk_distribution || {},
          execution_type_distribution: executionSummary.execution_type_distribution || {},
          avg_confidence: executionSummary.avg_confidence,
          avg_risk_reward: executionSummary.avg_risk_reward,
        };
      }

      state.loading = false;
      state.lastUpdated = Date.now();
      return state;
    } catch (error) {
      console.error('[TerminalService] Failed:', error);
      state.loading = false;
      state.error = error.message;
      return state;
    }
  },

  /**
   * Execute an active plan
   */
  async executePlan(symbol) {
    return fetchJSON(`${API_BASE}/api/v1/execution/execute/${symbol}`, { method: 'POST' });
  },

  /**
   * Generate new execution plan
   */
  async generatePlan(params) {
    return fetchJSON(`${API_BASE}/api/v1/execution/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  },
};

export default TerminalService;
