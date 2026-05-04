// Mock Portfolio Data for V3
// CRITICAL: timestamps в СЕКУНДАХ (для lightweight-charts v5)

const now = Math.floor(Date.now() / 1000);
const DAY = 86400;

// Portfolio Summary Aggregate
export const mockPortfolioSummary = {
  equity: 10140,
  total_pnl: 140,
  total_return_pct: 1.4,

  capital_deployed_pct: 34,
  active_cases: 2,
  watching_cases: 4,

  risk: {
    mode: "NORMAL",
    heat: 34,
    drawdown: -0.3
  },

  performance: {
    winrate: 68,
    avg_win: 1.8,
    avg_loss: -0.6,
    profit_factor: 2.1
  },

  system: {
    regime: "CHOP",
    bias: "SELECTIVE",
    best_strategy: "MEAN_REVERSION"
  }
};

// Equity Curve Data (timestamps в СЕКУНДАХ)
export const mockEquityCurve = [
  { time: now - DAY * 30, value: 10000 },
  { time: now - DAY * 28, value: 10020 },
  { time: now - DAY * 26, value: 10015 },
  { time: now - DAY * 24, value: 10035 },
  { time: now - DAY * 22, value: 10028 },
  { time: now - DAY * 20, value: 10055 },
  { time: now - DAY * 18, value: 10048 },
  { time: now - DAY * 16, value: 10070 },
  { time: now - DAY * 14, value: 10065 },
  { time: now - DAY * 12, value: 10090 },
  { time: now - DAY * 10, value: 10082 },
  { time: now - DAY * 8, value: 10105 },
  { time: now - DAY * 6, value: 10098 },
  { time: now - DAY * 4, value: 10125 },
  { time: now - DAY * 2, value: 10118 },
  { time: now - DAY * 1, value: 10140 }
];

// Empty State Portfolio Summary (для testing)
export const mockPortfolioSummaryEmpty = {
  equity: 10000,
  total_pnl: 0,
  total_return_pct: 0,

  capital_deployed_pct: 0,
  active_cases: 0,
  watching_cases: 6,

  risk: {
    mode: "DEFENSIVE",
    heat: 0,
    drawdown: 0
  },

  performance: {
    winrate: 0,
    avg_win: 0,
    avg_loss: 0,
    profit_factor: 0
  },

  system: {
    regime: "WAIT",
    bias: "NEUTRAL",
    best_strategy: "—"
  }
};
