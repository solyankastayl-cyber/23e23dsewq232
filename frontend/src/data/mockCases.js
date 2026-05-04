// Mock Trade Cases for V4 Case View
const now = Math.floor(Date.now() / 1000);

export const MOCK_CASES = [
  {
    id: "case_18",
    symbol: "BTCUSDT",
    direction: "LONG",
    status: "ACTIVE",
    trading_tf: "4H",
    duration: "3d 14h",
    pnl: 140,
    pnl_pct: 1.4,
    trade_count: 4,
    win_count: 3,
    loss_count: 1,
    strategy: "mean_reversion",
    thesis: "Recovery continuation after failed downside expansion",
    next_action: "Add on reclaim / reduce on rejection",
    stop: "68,900",
    target: 70500,
    avg_entry: 68950,
    entries: [
      { time: now - 86400 * 3, price: 68900, size_pct: 25 }
    ],
    adds: [
      { time: now - 86400 * 2, price: 69200, size_pct: 25 },
      { time: now - 86400 * 1, price: 69150, size_pct: 25 }
    ],
    partial_exits: [
      { time: now - 3600 * 12, price: 70100, size_pct: 25, pnl: 120 }
    ],
    exits: [],
    switched_from: "SHORT",
    switch_reason: "Failed breakdown, volume reclaim",
    execution_summary: {
      fills: 4,
      slippage_pct: 0.08,
      fees_usd: 12,
      quality: "GOOD"
    },
    timeline: [
      { label: "Signal detected", time: "Day 1 10:00" },
      { label: "First entry", time: "Day 1 14:30" },
      { label: "Added on reclaim", time: "Day 2 08:15" },
      { label: "Partial exit", time: "Day 3 12:00" },
      { label: "Thesis updated", time: "Day 3 16:45" },
      { label: "Active", time: "Now" }
    ]
  },
  {
    id: "case_17",
    symbol: "ETHUSDT",
    direction: "SHORT",
    status: "ACTIVE",
    trading_tf: "1H",
    duration: "1d 8h",
    pnl: 85,
    pnl_pct: 0.9,
    trade_count: 2,
    win_count: 2,
    loss_count: 0,
    strategy: "momentum_fade",
    thesis: "Exhaustion after parabolic move, volume divergence",
    next_action: "Monitor for reversal signs",
    stop: "3,450",
    switched_from: null,
    switch_reason: null,
    execution_summary: {
      fills: 2,
      slippage_pct: 0.12,
      fees_usd: 8,
      quality: "GOOD"
    },
    timeline: [
      { label: "Signal detected", time: "Yesterday 14:00" },
      { label: "First entry", time: "Yesterday 16:30" },
      { label: "Added on weakness", time: "Today 08:00" },
      { label: "Active", time: "Now" }
    ]
  },
  {
    id: "case_16",
    symbol: "SOLUSDT",
    direction: "LONG",
    status: "CLOSED_WIN",
    trading_tf: "4H",
    duration: "5d 2h",
    pnl: 320,
    pnl_pct: 3.8,
    trade_count: 6,
    win_count: 5,
    loss_count: 1,
    strategy: "trend_follow",
    thesis: "Strong breakout with volume confirmation",
    next_action: null,
    switched_from: null,
    switch_reason: null,
    execution_summary: {
      fills: 6,
      slippage_pct: 0.15,
      fees_usd: 28,
      quality: "GOOD"
    },
    timeline: [
      { label: "Signal detected", time: "5 days ago" },
      { label: "First entry", time: "5 days ago" },
      { label: "Added on strength", time: "4 days ago" },
      { label: "Partial exit", time: "2 days ago" },
      { label: "Full exit", time: "1 day ago" },
      { label: "Closed +", time: "Complete" }
    ]
  },
  {
    id: "case_15",
    symbol: "ADAUSDT",
    direction: "SHORT",
    status: "CLOSED_LOSS",
    trading_tf: "1H",
    duration: "12h",
    pnl: -45,
    pnl_pct: -0.6,
    trade_count: 1,
    win_count: 0,
    loss_count: 1,
    strategy: "breakdown_trade",
    thesis: "Expected continuation lower, stopped out",
    next_action: null,
    switched_from: null,
    switch_reason: null,
    execution_summary: {
      fills: 1,
      slippage_pct: 0.05,
      fees_usd: 4,
      quality: "FAIR"
    },
    timeline: [
      { label: "Signal detected", time: "Yesterday" },
      { label: "First entry", time: "Yesterday" },
      { label: "Stop hit", time: "12h ago" },
      { label: "Closed -", time: "Complete" }
    ]
  },
  {
    id: "case_14",
    symbol: "BNBUSDT",
    direction: "LONG",
    status: "WATCHING",
    trading_tf: "4H",
    duration: "—",
    pnl: 0,
    pnl_pct: 0,
    trade_count: 0,
    win_count: 0,
    loss_count: 0,
    strategy: null,
    thesis: "Potential setup forming, waiting for confirmation",
    next_action: "Wait for breakout confirmation",
    switched_from: null,
    switch_reason: null,
    execution_summary: null,
    timeline: null
  },
  {
    id: "case_13",
    symbol: "MATICUSDT",
    direction: "SHORT",
    status: "WATCHING",
    trading_tf: "1H",
    duration: "—",
    pnl: 0,
    pnl_pct: 0,
    trade_count: 0,
    win_count: 0,
    loss_count: 0,
    strategy: null,
    thesis: "Weak structure, watching for rejection",
    next_action: "Wait for volume confirmation",
    switched_from: null,
    switch_reason: null,
    execution_summary: null,
    timeline: null
  }
];
