// Mock Portfolio Data for Fund Dashboard
// Asset-oriented (не Cases-oriented)

const now = Math.floor(Date.now() / 1000);
const DAY = 86400;

// Portfolio Summary (9 ключевых метрик)
export const mockPortfolioSummary = {
  portfolio_value: 30124,
  today_pnl: 870,
  today_pnl_pct: 2.98,
  total_pnl: 4124,
  total_pnl_pct: 15.86,
  realized_pnl: 2150,
  unrealized_pnl: 1974,
  total_invested: 26000,
  ath_balance: 32780,
  drawdown_from_ath: -2656,
  drawdown_from_ath_pct: -8.11,
  return_pct: 15.86,
  
  // Вложенные объекты для SystemState
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

// Portfolio Assets (BTC, ETH, SOL, Stablecoins)
export const mockPortfolioAssets = [
  {
    asset: "BTC",
    category: "Bitcoin Ecosystem",
    amount: 0.17,
    avg_entry: 59000,
    current_price: 64000,
    invested: 10030,
    current_value: 10880,
    pnl: 850,
    pnl_pct: 8.47,
    allocation_pct: 36.1,
    status: "ACTIVE"
  },
  {
    asset: "ETH",
    category: "Ethereum Ecosystem",
    amount: 2.4,
    avg_entry: 3200,
    current_price: 3450,
    invested: 7680,
    current_value: 8280,
    pnl: 600,
    pnl_pct: 7.81,
    allocation_pct: 27.5,
    status: "ACTIVE"
  },
  {
    asset: "SOL",
    category: "Solana Ecosystem",
    amount: 38.2,
    avg_entry: 142,
    current_price: 149,
    invested: 5424,
    current_value: 5692,
    pnl: 268,
    pnl_pct: 4.94,
    allocation_pct: 18.9,
    status: "ACTIVE"
  },
  {
    asset: "USDC",
    category: "Stablecoins",
    amount: 5272,
    avg_entry: 1,
    current_price: 1,
    invested: 5272,
    current_value: 5272,
    pnl: 0,
    pnl_pct: 0,
    allocation_pct: 17.5,
    status: "HOLD"
  }
];

// Allocation by Category
export const mockAllocationByCategory = [
  { category: "Bitcoin Ecosystem", value: 10880, pct: 36.1, color: "#f7931a" },
  { category: "Ethereum Ecosystem", value: 8280, pct: 27.5, color: "#627eea" },
  { category: "Solana Ecosystem", value: 5692, pct: 18.9, color: "#14f195" },
  { category: "Stablecoins", value: 5272, pct: 17.5, color: "#6b7280" }
];

// Equity Curve по периодам
export const mockEquityCurveData = {
  "24H": [
    { time: now - DAY + (DAY / 24) * 0, value: 29254 },
    { time: now - DAY + (DAY / 24) * 4, value: 29410 },
    { time: now - DAY + (DAY / 24) * 8, value: 29620 },
    { time: now - DAY + (DAY / 24) * 12, value: 29580 },
    { time: now - DAY + (DAY / 24) * 16, value: 29840 },
    { time: now - DAY + (DAY / 24) * 20, value: 30020 },
    { time: now, value: 30124 }
  ],
  "7D": [
    { time: now - DAY * 7, value: 28420 },
    { time: now - DAY * 6, value: 28650 },
    { time: now - DAY * 5, value: 28920 },
    { time: now - DAY * 4, value: 29140 },
    { time: now - DAY * 3, value: 29380 },
    { time: now - DAY * 2, value: 29720 },
    { time: now - DAY * 1, value: 29254 },
    { time: now, value: 30124 }
  ],
  "30D": [
    { time: now - DAY * 30, value: 26000 },
    { time: now - DAY * 27, value: 26420 },
    { time: now - DAY * 24, value: 26850 },
    { time: now - DAY * 21, value: 27180 },
    { time: now - DAY * 18, value: 27520 },
    { time: now - DAY * 15, value: 27890 },
    { time: now - DAY * 12, value: 28240 },
    { time: now - DAY * 9, value: 28620 },
    { time: now - DAY * 6, value: 28960 },
    { time: now - DAY * 3, value: 29380 },
    { time: now, value: 30124 }
  ],
  "ALL": [
    { time: now - DAY * 90, value: 26000 },
    { time: now - DAY * 80, value: 27200 },
    { time: now - DAY * 70, value: 28100 },
    { time: now - DAY * 60, value: 29500 },
    { time: now - DAY * 50, value: 31200 },
    { time: now - DAY * 40, value: 32780 }, // ATH
    { time: now - DAY * 30, value: 31400 },
    { time: now - DAY * 20, value: 30200 },
    { time: now - DAY * 10, value: 29100 },
    { time: now, value: 30124 }
  ]
};

// Active Positions (расширенная версия)
export const mockActivePositions = [
  {
    id: "pos_1",
    symbol: "BTCUSDT",
    side: "LONG",
    size_usd: 3200,
    size_base: 0.046,
    avg_entry: 68950,
    current_price: 70097,
    pnl: 140,
    pnl_pct: 1.66,
    duration: "3d 14h",
    strategy: "mean_reversion",
    tf: "4H",
    trade_count: 4,
    leverage: 1,
    status: "ACTIVE"
  },
  {
    id: "pos_2",
    symbol: "ETHUSDT",
    side: "SHORT",
    size_usd: 2800,
    size_base: 0.81,
    avg_entry: 3450,
    current_price: 3420,
    pnl: 85,
    pnl_pct: 3.04,
    duration: "1d 8h",
    strategy: "momentum_fade",
    tf: "1H",
    trade_count: 2,
    leverage: 1,
    status: "ACTIVE"
  }
];

// Closed Positions (история)
export const mockClosedPositions = [
  {
    id: "pos_c1",
    symbol: "SOLUSDT",
    side: "LONG",
    size_usd: 1800,
    entry: 142,
    exit: 149,
    pnl: 380,
    pnl_pct: 4.93,
    duration: "5d 2h",
    strategy: "trend_follow",
    exit_reason: "target_hit",
    closed_at: now - DAY * 1
  },
  {
    id: "pos_c2",
    symbol: "ADAUSDT",
    side: "SHORT",
    size_usd: 1200,
    entry: 0.58,
    exit: 0.54,
    pnl: 145,
    pnl_pct: 6.89,
    duration: "2d 18h",
    strategy: "breakdown_trade",
    exit_reason: "target_hit",
    closed_at: now - DAY * 3
  },
  {
    id: "pos_c3",
    symbol: "BNBUSDT",
    side: "LONG",
    size_usd: 900,
    entry: 385,
    exit: 382,
    pnl: -45,
    pnl_pct: -0.78,
    duration: "12h",
    strategy: "breakout_trade",
    exit_reason: "stop_loss",
    closed_at: now - DAY * 5
  },
  {
    id: "pos_c4",
    symbol: "MATICUSDT",
    side: "LONG",
    size_usd: 650,
    entry: 0.92,
    exit: 0.95,
    pnl: 85,
    pnl_pct: 3.26,
    duration: "1d 6h",
    strategy: "mean_reversion",
    exit_reason: "target_hit",
    closed_at: now - DAY * 7
  },
  {
    id: "pos_c5",
    symbol: "LINKUSDT",
    side: "SHORT",
    size_usd: 720,
    entry: 18.5,
    exit: 17.9,
    pnl: 120,
    pnl_pct: 3.24,
    duration: "3d 4h",
    strategy: "momentum_fade",
    exit_reason: "target_hit",
    closed_at: now - DAY * 10
  }
];
