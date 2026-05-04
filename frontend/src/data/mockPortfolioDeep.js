// Deep Portfolio Analytics Mock Data
// Includes: Multi-asset history, Entry/Exit events, Trade history per asset, Allocation over time

const now = Math.floor(Date.now() / 1000);
const DAY = 86400;

// === PORTFOLIO SUMMARY ===
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

// === MULTI-ASSET EQUITY CURVES (for stacked/multi-line chart) ===
// Each asset tracks its equity contribution over time
// ВАЖНО: Каждый актив показывает данные ТОЛЬКО после entry
export const mockMultiAssetEquityCurves = {
  // Portfolio total equity (60 дней, все точки)
  PORTFOLIO: Array.from({ length: 60 }, (_, i) => ({
    time: now - DAY * (59 - i),
    value: 26000 + (i * 70) + Math.random() * 200 - 100
  })),
  
  // BTC equity curve (entry: 55 дней назад)
  BTC: Array.from({ length: 55 }, (_, i) => ({
    time: now - DAY * (54 - i),
    value: 10030 + (i * 15) + Math.random() * 50 - 25
  })),
  
  // ETH equity curve (entry: 45 дней назад)
  ETH: Array.from({ length: 45 }, (_, i) => ({
    time: now - DAY * (44 - i),
    value: 7680 + (i * 13) + Math.random() * 40 - 20
  })),
  
  // SOL equity curve (entry: 35 дней назад)
  SOL: Array.from({ length: 35 }, (_, i) => ({
    time: now - DAY * (34 - i),
    value: 5424 + (i * 8) + Math.random() * 30 - 15
  })),
  
  // USDC (cash, последние 30 дней для наглядности)
  USDC: Array.from({ length: 30 }, (_, i) => ({
    time: now - DAY * (29 - i),
    value: 5272 + Math.random() * 20 - 10 // slight fluctuation
  }))
};

// === ASSET ENTRY/EXIT TIMELINE EVENTS ===
export const mockAssetTimeline = [
  {
    date: now - DAY * 55,
    event: "ENTRY",
    asset: "BTC",
    reason: "Strong reversal signal at support",
    allocation: 10030,
    price: 59000
  },
  {
    date: now - DAY * 45,
    event: "ENTRY",
    asset: "ETH",
    reason: "Breakout above resistance",
    allocation: 7680,
    price: 3200
  },
  {
    date: now - DAY * 38,
    event: "EXIT",
    asset: "LINK",
    reason: "Target hit, momentum fading",
    allocation: -1200,
    price: 17.9,
    pnl: 120,
    pnl_pct: 3.24
  },
  {
    date: now - DAY * 35,
    event: "ENTRY",
    asset: "SOL",
    reason: "Oversold bounce setup",
    allocation: 5424,
    price: 142
  },
  {
    date: now - DAY * 28,
    event: "EXIT",
    asset: "MATIC",
    reason: "Stop loss triggered",
    allocation: -650,
    price: 0.95,
    pnl: 85,
    pnl_pct: 3.26
  },
  {
    date: now - DAY * 20,
    event: "REBALANCE",
    asset: "BTC",
    reason: "Position size optimization",
    allocation: 850,
    price: 62000
  }
];

// === CURRENT PORTFOLIO ASSETS (detailed) ===
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
    status: "ACTIVE",
    entry_date: now - DAY * 55,
    trade_count: 4,
    win_count: 3,
    loss_count: 1,
    avg_trade_pnl: 212,
    best_trade: 320,
    worst_trade: -45
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
    status: "ACTIVE",
    entry_date: now - DAY * 45,
    trade_count: 3,
    win_count: 2,
    loss_count: 1,
    avg_trade_pnl: 200,
    best_trade: 420,
    worst_trade: -80
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
    status: "ACTIVE",
    entry_date: now - DAY * 35,
    trade_count: 2,
    win_count: 2,
    loss_count: 0,
    avg_trade_pnl: 134,
    best_trade: 180,
    worst_trade: 88
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
    status: "HOLD",
    entry_date: now - DAY * 90,
    trade_count: 0,
    win_count: 0,
    loss_count: 0,
    avg_trade_pnl: 0,
    best_trade: 0,
    worst_trade: 0
  }
];

// === TRADE HISTORY PER ASSET (expandable rows) ===
export const mockTradeHistoryByAsset = {
  BTC: [
    {
      id: "trade_btc_1",
      date: now - DAY * 55,
      type: "BUY",
      price: 59000,
      amount: 0.05,
      value: 2950,
      reason: "Initial entry"
    },
    {
      id: "trade_btc_2",
      date: now - DAY * 48,
      type: "BUY",
      price: 60500,
      amount: 0.05,
      value: 3025,
      reason: "Add on dip"
    },
    {
      id: "trade_btc_3",
      date: now - DAY * 40,
      type: "SELL",
      price: 62000,
      amount: 0.02,
      value: 1240,
      pnl: 85,
      pnl_pct: 2.23,
      reason: "Partial profit taking"
    },
    {
      id: "trade_btc_4",
      date: now - DAY * 20,
      type: "BUY",
      price: 62000,
      amount: 0.09,
      value: 5580,
      reason: "Rebalance increase"
    }
  ],
  ETH: [
    {
      id: "trade_eth_1",
      date: now - DAY * 45,
      type: "BUY",
      price: 3200,
      amount: 1.5,
      value: 4800,
      reason: "Breakout entry"
    },
    {
      id: "trade_eth_2",
      date: now - DAY * 38,
      type: "BUY",
      price: 3300,
      amount: 0.9,
      value: 2970,
      reason: "Add to winner"
    },
    {
      id: "trade_eth_3",
      date: now - DAY * 25,
      type: "SELL",
      price: 3500,
      amount: 0.2,
      value: 700,
      pnl: 55,
      pnl_pct: 2.91,
      reason: "Trim at resistance"
    }
  ],
  SOL: [
    {
      id: "trade_sol_1",
      date: now - DAY * 35,
      type: "BUY",
      price: 142,
      amount: 38.2,
      value: 5424,
      reason: "Oversold bounce"
    },
    {
      id: "trade_sol_2",
      date: now - DAY * 15,
      type: "SELL",
      price: 145,
      amount: 5,
      value: 725,
      pnl: 15,
      pnl_pct: 2.11,
      reason: "Partial exit"
    }
  ],
  USDC: []
};

// === ALLOCATION OVER TIME (for animated timeline) ===
export const mockAllocationHistory = [
  {
    date: now - DAY * 60,
    assets: [
      { asset: "USDC", value: 26000, pct: 100 }
    ]
  },
  {
    date: now - DAY * 55,
    assets: [
      { asset: "BTC", value: 10030, pct: 38.6 },
      { asset: "USDC", value: 15970, pct: 61.4 }
    ]
  },
  {
    date: now - DAY * 45,
    assets: [
      { asset: "BTC", value: 10500, pct: 40.1 },
      { asset: "ETH", value: 7680, pct: 29.3 },
      { asset: "USDC", value: 8020, pct: 30.6 }
    ]
  },
  {
    date: now - DAY * 35,
    assets: [
      { asset: "BTC", value: 10700, pct: 38.2 },
      { asset: "ETH", value: 8100, pct: 28.9 },
      { asset: "SOL", value: 5424, pct: 19.4 },
      { asset: "USDC", value: 3776, pct: 13.5 }
    ]
  },
  {
    date: now,
    assets: [
      { asset: "BTC", value: 10880, pct: 36.1 },
      { asset: "ETH", value: 8280, pct: 27.5 },
      { asset: "SOL", value: 5692, pct: 18.9 },
      { asset: "USDC", value: 5272, pct: 17.5 }
    ]
  }
];

// === ALLOCATION BY CATEGORY (for donut) ===
export const mockAllocationByCategory = [
  { category: "Bitcoin Ecosystem", value: 10880, pct: 36.1, color: "#f59e0b" },
  { category: "Ethereum Ecosystem", value: 8280, pct: 27.5, color: "#3b82f6" },
  { category: "Solana Ecosystem", value: 5692, pct: 18.9, color: "#10b981" },
  { category: "Stablecoins", value: 5272, pct: 17.5, color: "#6b7280" }
];

// === ACTIVE POSITIONS ===
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

// === CLOSED POSITIONS ===
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
