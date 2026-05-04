import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Activity, TrendingUp, Target, Layers, BarChart2, 
  RefreshCw, Wifi, WifiOff, ChevronRight, Clock
} from 'lucide-react';
import TradingChart from '../../../components/charts/TradingChart';
import { ValidationSummaryBlock, useValidationMetrics } from '../../../components/validation';
import { ValidationBridgeSummaryBlock, CombinedTruthsBlock, useValidationBridge } from '../../../components/alpha-bridge';
import { EntryModeSummaryBlock, EntryModeEvaluationsBlock, EntryModeActionsBlock, useEntryMode } from '../../../components/entry-modes';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Valid timeframes
const TIMEFRAMES = ['1H', '4H', '1D'];

// Unified API fetch with timeframe
const fetchTerminalState = async (symbol, timeframe) => {
  const res = await fetch(`${API_URL}/api/terminal/state/${symbol}?timeframe=${timeframe}`);
  if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
  return res.json();
};

// Decision status colors
const DECISION_STYLES = {
  GO_FULL: 'bg-green-600 text-white',
  GO_REDUCED: 'bg-emerald-500 text-white',
  WAIT: 'bg-amber-500 text-white',
  WAIT_MICRO: 'bg-orange-500 text-white',
  SKIP: 'bg-gray-500 text-white'
};

// Strength badge colors
const STRENGTH_COLORS = {
  strong: 'bg-green-100 text-green-700 border-green-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  weak: 'bg-gray-100 text-gray-600 border-gray-200'
};

const TradingTerminal = () => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('4H');
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tfLoading, setTfLoading] = useState(false);  // Loading on TF change
  const [connected, setConnected] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  // V1 Validation metrics
  const { metrics: validationMetrics } = useValidationMetrics(symbol);

  // AF3 Validation Bridge
  const { 
    truths: bridgeTruths, 
    summary: bridgeSummary, 
    submitActions: submitBridgeActions 
  } = useValidationBridge(true);

  // AF4 Entry Mode Adaptation
  const {
    evaluations: entryModeEvaluations,
    actions: entryModeActions,
    summary: entryModeSummary,
    loading: entryModeLoading,
    run: runEntryMode,
    submit: submitEntryMode
  } = useEntryMode();

  // Single unified fetch
  const loadState = useCallback(async (showTfLoading = false) => {
    try {
      if (showTfLoading) setTfLoading(true);
      const response = await fetchTerminalState(symbol, timeframe);
      if (response.ok && response.data) {
        setState(response.data);
        setLastUpdate(new Date());
        setConnected(true);
      }
    } catch (error) {
      console.error('Terminal state error:', error);
      setConnected(false);
    } finally {
      setLoading(false);
      setTfLoading(false);
    }
  }, [symbol, timeframe]);

  // Handle timeframe change
  const handleTimeframeChange = (newTf) => {
    if (newTf !== timeframe) {
      setTimeframe(newTf);
    }
  };

  useEffect(() => {
    loadState(true);  // Show loading on initial/TF change
    const interval = setInterval(() => loadState(false), 3000);
    return () => clearInterval(interval);
  }, [loadState]);

  const handleRefresh = () => loadState(true);

  if (loading && !state) {
    return (
      <div className="flex h-screen w-full bg-gray-50 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading terminal...</p>
        </div>
      </div>
    );
  }

  const decision = state?.decision || {};
  const execution = state?.execution || {};
  const executionStatus = state?.execution_status || {};
  const ordersPreview = state?.orders_preview || [];
  const positionsPreview = state?.positions_preview || [];
  const micro = state?.micro || {};
  const position = state?.position || {};
  const portfolio = state?.portfolio || {};
  const risk = state?.risk || {};
  const tradesPreview = state?.trades_preview || [];  // TT4
  const tradeAnalytics = state?.trade_analytics || {};  // TT4
  const validation = state?.validation || {};
  const systemTimeframe = state?.timeframe || timeframe;

  return (
    <div className="flex h-screen w-full bg-gray-50 overflow-hidden font-sans" data-testid="trading-terminal">
      {/* Sidebar - Dark */}
      <aside className="h-full w-16 lg:w-56 bg-gray-900 border-r border-gray-800 flex-shrink-0 flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center justify-center lg:justify-start lg:px-4 border-b border-gray-800">
          <Target className="w-6 h-6 text-white" />
          <span className="hidden lg:block ml-2 text-white font-bold text-sm tracking-widest uppercase">Terminal</span>
        </div>

        {/* Symbol Selector */}
        <div className="p-2 lg:p-4 border-b border-gray-800">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="w-full bg-gray-800 text-white text-sm font-medium px-3 py-2 rounded border border-gray-700 focus:border-gray-500 outline-none"
            data-testid="symbol-selector"
          >
            <option value="BTCUSDT">BTC/USDT</option>
            <option value="ETHUSDT">ETH/USDT</option>
            <option value="SOLUSDT">SOL/USDT</option>
          </select>
        </div>

        {/* Timeframe Selector */}
        <div className="p-2 lg:p-4 border-b border-gray-800">
          <div className="hidden lg:flex items-center gap-1 mb-2">
            <Clock className="w-3 h-3 text-gray-500" />
            <span className="text-xs text-gray-500 uppercase tracking-wider">Timeframe</span>
          </div>
          <div className="flex gap-1" data-testid="timeframe-selector">
            {TIMEFRAMES.map(tf => (
              <button
                key={tf}
                onClick={() => handleTimeframeChange(tf)}
                disabled={tfLoading}
                className={`flex-1 px-2 py-1.5 text-xs font-bold rounded transition-all ${
                  timeframe === tf
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
                } ${tfLoading ? 'opacity-50 cursor-wait' : ''}`}
                data-testid={`tf-${tf}`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 p-2 lg:p-3 space-y-1">
          <NavItem icon={Activity} label="Dashboard" active />
          <NavItem icon={BarChart2} label="Analysis" />
          <NavItem icon={Layers} label="Positions" />
          <NavItem icon={TrendingUp} label="History" />
        </nav>

        {/* Connection Status */}
        <div className="p-4 border-t border-gray-800">
          <div className={`flex items-center gap-2 text-xs ${connected ? 'text-green-400' : 'text-red-400'}`}>
            {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            <span className="hidden lg:block font-medium">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="mt-1 text-xs text-gray-500 hidden lg:block">
            Source: {micro.source || 'mock'}
          </div>
        </div>
      </aside>

      {/* Main Area - Light */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 border-b border-gray-200 bg-white flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-4">
            <h1 className="text-sm font-bold uppercase tracking-widest text-gray-900">
              {symbol}
            </h1>
            {/* Timeframe Badge */}
            <span className="text-xs px-2 py-0.5 rounded bg-gray-900 text-white font-bold" data-testid="active-timeframe">
              {systemTimeframe}
            </span>
            {lastUpdate && (
              <span className="text-xs text-gray-500">
                Last: {lastUpdate.toLocaleTimeString()}
              </span>
            )}
            {/* Mode Badge */}
            <span className={`text-xs px-2 py-0.5 rounded ${
              state?.system?.mode === 'LIVE' 
                ? 'bg-green-100 text-green-700' 
                : 'bg-amber-100 text-amber-700'
            }`}>
              {state?.system?.mode === 'LIVE' ? 'LIVE' : 'SIMULATION'}
            </span>
            {/* TF Loading indicator */}
            {tfLoading && (
              <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
            )}
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={handleRefresh}
              className="p-2 hover:bg-gray-100 rounded transition-colors"
              data-testid="refresh-button"
            >
              <RefreshCw className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </header>

        {/* Grid Content */}
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {/* Operator Control Block - TT5 + AF2 Policy */}
          <OperatorControlBlock />
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6 mt-4">
            
            {/* Validation Block - Shows only when there are issues */}
            {(validation.critical_count > 0 || validation.warning_count > 0) && (
              <div className="lg:col-span-12">
                <ValidationBlock validation={validation} />
              </div>
            )}
            
            {/* Chart Block - FULL WIDTH */}
            <div className="lg:col-span-12 bg-white border border-gray-200 rounded-sm shadow-sm overflow-hidden">
              <TradingChart
                symbol={symbol}
                timeframe={systemTimeframe}
                execution={execution}
                decision={decision}
                structure={state?.structure || null}
                height={450}
                showVolume={true}
              />
            </div>

            {/* Decision Block */}
            <div className="lg:col-span-3 bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="decision-block">
              <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">Decision</h2>
              <div className="space-y-4">
                <div className={`inline-flex px-4 py-2 rounded text-2xl font-bold tracking-tight ${DECISION_STYLES[decision.action] || 'bg-gray-200'}`}>
                  {decision.action || 'WAIT'}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">Confidence:</span>
                  <span className="text-lg font-bold tabular-nums">{Math.round((decision.confidence || 0) * 100)}%</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-600 rounded-full transition-all"
                      style={{ width: `${(decision.confidence || 0) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="text-sm text-gray-600">
                  Direction: <span className="font-medium">{decision.direction || 'NEUTRAL'}</span>
                </div>
              </div>
            </div>

            {/* Why Block */}
            <div className="lg:col-span-3 bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="why-block">
              <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">Why</h2>
              <div className="space-y-2">
                {decision.reasons?.length > 0 ? (
                  decision.reasons.map((reason, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <ChevronRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
                      <span className="text-sm text-gray-700">{reason}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-gray-400 text-sm">No reasons</div>
                )}
              </div>
            </div>

            {/* Execution Block */}
            <div className="lg:col-span-3 bg-white border border-gray-200 rounded-sm shadow-sm border-l-4 border-l-blue-600 p-5" data-testid="execution-block">
              <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">Execution</h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-gray-500 uppercase tracking-wider">Mode</label>
                    <div className="text-sm font-bold text-gray-900 mt-1">{execution.mode || 'PASSIVE_LIMIT'}</div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase tracking-wider">Size</label>
                    <div className="text-sm font-bold text-gray-900 mt-1">{execution.size || 0}x</div>
                  </div>
                </div>

                <div className="border-t border-gray-100 pt-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500 uppercase">Entry</span>
                    <span className="text-sm font-bold tabular-nums">${execution.entry?.toLocaleString() || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500 uppercase">Stop Loss</span>
                    <span className="text-sm font-bold tabular-nums text-red-600">${execution.stop?.toLocaleString() || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500 uppercase">Take Profit</span>
                    <span className="text-sm font-bold tabular-nums text-green-600">${execution.target?.toLocaleString() || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center border-t border-gray-100 pt-3">
                    <span className="text-xs text-gray-500 uppercase">R:R</span>
                    <span className="text-lg font-bold tabular-nums">{execution.rr || '—'}</span>
                  </div>
                </div>

                <button 
                  className="w-full py-3 bg-blue-600 text-white font-bold uppercase tracking-widest text-sm hover:bg-blue-700 transition-colors rounded disabled:opacity-50"
                  disabled={decision.action === 'SKIP' || decision.action?.startsWith('WAIT')}
                  data-testid="execute-button"
                >
                  Execute Trade
                </button>
              </div>
            </div>

            {/* Microstructure Block */}
            <div className="lg:col-span-3 bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="micro-block">
              <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">Microstructure</h2>
              <div className="grid grid-cols-2 gap-3">
                <MicroStat 
                  label="Imbalance"
                  value={`${micro.imbalance > 0 ? '+' : ''}${((micro.imbalance || 0) * 100).toFixed(1)}%`}
                  color={micro.imbalance > 0.1 ? 'green' : micro.imbalance < -0.1 ? 'red' : 'gray'}
                />
                <MicroStat 
                  label="Spread"
                  value={`${micro.spread?.toFixed(1) || '—'} bps`}
                  color={micro.spread < 1.5 ? 'green' : micro.spread > 2.5 ? 'red' : 'amber'}
                />
                <MicroStat 
                  label="Liquidity"
                  value={micro.liquidity || 'unknown'}
                  color={micro.liquidity === 'strong_bid' ? 'green' : micro.liquidity === 'thin' ? 'red' : 'gray'}
                />
                <MicroStat 
                  label="State"
                  value={micro.state || 'unknown'}
                  color={micro.state === 'favorable' ? 'green' : micro.state === 'hostile' ? 'red' : 'amber'}
                />
              </div>
            </div>

            {/* Execution Status Block */}
            <div className="lg:col-span-4">
              <ExecutionStatusBlock executionStatus={executionStatus} />
            </div>

            {/* Position Status Block - Using new component */}
            <div className="lg:col-span-4">
              <PositionStatusBlock position={position} />
            </div>

            {/* Portfolio Block - TT3 */}
            <div className="lg:col-span-4">
              <PortfolioStatusBlock portfolio={portfolio} />
            </div>

            {/* Risk Block - TT3 */}
            <div className="lg:col-span-4">
              <RiskConsoleBlock risk={risk} />
            </div>

            {/* Trades Preview Block - TT4 */}
            <div className="lg:col-span-4">
              <TradesPreviewBlock trades={tradesPreview} />
            </div>

            {/* Trade Analytics Block - TT4 */}
            <div className="lg:col-span-4">
              <TradeAnalyticsBlock data={tradeAnalytics} />
            </div>

            {/* Alpha Factory Summary Block - AF1 */}
            <div className="lg:col-span-4">
              <AlphaFactorySummaryBlock />
            </div>

            {/* V1 Validation Summary Block */}
            {validationMetrics && validationMetrics.trades > 0 && (
              <div className="lg:col-span-4">
                <ValidationSummaryBlock metrics={validationMetrics} />
              </div>
            )}

            {/* AF3 Validation Bridge Summary */}
            {bridgeSummary && bridgeSummary.total_symbols > 0 && (
              <div className="lg:col-span-4">
                <ValidationBridgeSummaryBlock 
                  summary={bridgeSummary} 
                  onSubmitActions={bridgeSummary.high_priority_actions > 0 ? submitBridgeActions : null}
                />
              </div>
            )}

            {/* AF3 Combined Truths */}
            {bridgeTruths && bridgeTruths.length > 0 && (
              <div className="lg:col-span-8">
                <CombinedTruthsBlock truths={bridgeTruths} />
              </div>
            )}

            {/* AF4 Entry Mode Summary */}
            {entryModeSummary && (
              <div className="lg:col-span-4">
                <EntryModeSummaryBlock 
                  summary={entryModeSummary}
                  onRun={runEntryMode}
                  onSubmit={() => submitEntryMode(true)}
                  loading={entryModeLoading}
                />
              </div>
            )}

            {/* AF4 Entry Mode Evaluations */}
            {entryModeEvaluations && entryModeEvaluations.length > 0 && (
              <div className="lg:col-span-4">
                <EntryModeEvaluationsBlock evaluations={entryModeEvaluations} />
              </div>
            )}

            {/* AF4 Entry Mode Actions */}
            {entryModeActions && entryModeActions.length > 0 && (
              <div className="lg:col-span-4">
                <EntryModeActionsBlock actions={entryModeActions} />
              </div>
            )}

            {/* Orders Tab - Full Width */}
            <div className="lg:col-span-12">
              <div className="bg-white border border-gray-200 rounded-sm shadow-sm">
                <div className="px-5 py-4 border-b border-gray-100">
                  <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase">Orders</h2>
                </div>
                <div className="p-0">
                  <OrdersTab orders={ordersPreview} symbol={symbol} />
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

// Helper Components
const NavItem = ({ icon: Icon, label, active = false }) => (
  <button className={`w-full flex items-center gap-3 px-3 py-2 rounded transition-colors ${
    active ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
  }`}>
    <Icon className="w-5 h-5 flex-shrink-0" />
    <span className="hidden lg:block text-sm font-medium">{label}</span>
  </button>
);

const MicroStat = ({ label, value, color = 'gray' }) => {
  const colorMap = {
    green: 'text-green-600',
    red: 'text-red-600',
    amber: 'text-amber-600',
    gray: 'text-gray-600'
  };
  
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
      <span className={`text-lg font-bold tabular-nums mt-1 ${colorMap[color]}`}>{value}</span>
    </div>
  );
};

// Validation Block Component
const ValidationBlock = ({ validation }) => {
  if (!validation || !validation.issues?.length) return null;
  
  const hasCritical = validation.critical_count > 0;
  const hasWarning = validation.warning_count > 0;
  
  // Only show if there are actual issues worth displaying
  const relevantIssues = validation.issues?.filter(
    i => i.severity === 'critical' || i.severity === 'warning'
  ) || [];
  
  if (relevantIssues.length === 0) return null;
  
  return (
    <div 
      className={`rounded-sm border p-4 ${
        hasCritical 
          ? 'border-red-300 bg-red-50' 
          : hasWarning 
            ? 'border-amber-300 bg-amber-50'
            : 'border-gray-200 bg-gray-50'
      }`}
      data-testid="validation-block"
    >
      <div className={`text-xs font-bold uppercase tracking-widest mb-3 ${
        hasCritical ? 'text-red-700' : hasWarning ? 'text-amber-700' : 'text-gray-500'
      }`}>
        {hasCritical ? 'DATA ERROR' : 'Data Warning'}
      </div>
      <div className="space-y-2">
        {relevantIssues.map((issue, idx) => (
          <div 
            key={idx} 
            className={`flex items-start gap-2 text-sm ${
              issue.severity === 'critical' ? 'text-red-700' : 'text-amber-700'
            }`}
          >
            <span className="font-bold flex-shrink-0">
              {issue.valid ? '✓' : '✗'}
            </span>
            <span>{issue.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Execution Status Block Component
const ExecutionStatusBlock = ({ executionStatus, onPlaceOrder }) => {
  const stateColors = {
    IDLE: 'bg-gray-100 text-gray-700',
    WAITING_ENTRY: 'bg-amber-100 text-amber-700',
    READY_TO_PLACE: 'bg-green-100 text-green-700',
    ORDER_PLANNED: 'bg-blue-100 text-blue-700',
    ORDER_PLACED: 'bg-blue-500 text-white',
    PARTIAL_FILL: 'bg-purple-500 text-white',
    FILLED: 'bg-green-600 text-white',
    CANCELLED: 'bg-gray-400 text-white',
    REJECTED: 'bg-red-500 text-white',
    EXPIRED: 'bg-gray-500 text-white',
    CLOSED: 'bg-gray-600 text-white',
  };
  
  const state = executionStatus.execution_state || 'IDLE';
  const filledPct = (executionStatus.filled_pct || 0) * 100;
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="execution-status-block">
      <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
        Execution Status
      </h2>
      
      {/* State Badge */}
      <div className={`inline-block px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider mb-4 ${stateColors[state] || stateColors.IDLE}`}>
        {executionStatus.status_label || state}
      </div>
      
      {/* Progress bar for fills */}
      {(state === 'ORDER_PLACED' || state === 'PARTIAL_FILL') && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Fill Progress</span>
            <span className="font-bold">{filledPct.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${filledPct}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Status Details */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Intent State</span>
          <span className="font-medium">{executionStatus.intent_state || 'IDLE'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Order Present</span>
          <span className={`font-medium ${executionStatus.order_present ? 'text-green-600' : 'text-gray-400'}`}>
            {executionStatus.order_present ? 'Yes' : 'No'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Position Open</span>
          <span className={`font-medium ${executionStatus.position_open ? 'text-blue-600' : 'text-gray-400'}`}>
            {executionStatus.position_open ? 'Yes' : 'No'}
          </span>
        </div>
      </div>
      
      {/* Reason */}
      {executionStatus.status_reason && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <span className="text-xs text-gray-500 block">Reason</span>
          <span className="text-sm text-gray-700">{executionStatus.status_reason}</span>
        </div>
      )}
    </div>
  );
};

// Position Status Block Component
const PositionStatusBlock = ({ position }) => {
  const healthColors = {
    GOOD: 'bg-green-100 text-green-700 border-green-200',
    WARNING: 'bg-amber-100 text-amber-700 border-amber-200',
    CRITICAL: 'bg-red-100 text-red-700 border-red-200',
  };
  
  const statusColors = {
    OPEN: 'bg-blue-500 text-white',
    OPENING: 'bg-blue-400 text-white',
    SCALING: 'bg-purple-500 text-white',
    REDUCING: 'bg-amber-500 text-white',
    CLOSING: 'bg-orange-500 text-white',
    CLOSED: 'bg-gray-500 text-white',
    FLAT: 'bg-gray-200 text-gray-600',
  };
  
  const hasPosition = position?.has_position;
  const pnl = position?.unrealized_pnl || 0;
  const pnlPct = position?.pnl_pct || 0;
  const health = position?.health || 'GOOD';
  const status = position?.status || 'FLAT';
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="position-status-block">
      <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
        Position
      </h2>
      
      {!hasPosition ? (
        <div className="text-center py-4">
          <span className={`inline-block px-3 py-1.5 rounded text-xs font-bold uppercase ${statusColors.FLAT}`}>
            FLAT
          </span>
          <p className="text-sm text-gray-500 mt-2">No open position</p>
        </div>
      ) : (
        <>
          {/* Status + Health Badges */}
          <div className="flex gap-2 mb-4">
            <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${statusColors[status] || statusColors.OPEN}`}>
              {status}
            </span>
            <span className={`px-2 py-1 rounded text-xs font-bold uppercase border ${healthColors[health] || healthColors.GOOD}`}>
              {health}
            </span>
          </div>
          
          {/* Side + Size */}
          <div className="flex items-center gap-3 mb-4">
            <span className={`text-lg font-bold ${position.side === 'LONG' ? 'text-green-600' : 'text-red-600'}`}>
              {position.side}
            </span>
            <span className="text-lg font-semibold text-gray-900">
              {position.size} {position.symbol?.replace('USDT', '')}
            </span>
          </div>
          
          {/* PnL */}
          <div className={`p-3 rounded mb-4 ${pnl >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className="text-xs text-gray-500 mb-1">Unrealized PnL</div>
            <div className={`text-xl font-bold ${pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {pnl >= 0 ? '+' : ''}{pnl.toLocaleString()} USD
            </div>
            <div className={`text-sm font-medium ${pnlPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
            </div>
          </div>
          
          {/* Entry/Mark/Levels */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Entry</span>
              <span className="font-medium tabular-nums">${position.entry_price?.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Mark</span>
              <span className="font-medium tabular-nums">${position.mark_price?.toLocaleString()}</span>
            </div>
            {position.stop && (
              <div className="flex justify-between">
                <span className="text-gray-500">Stop</span>
                <span className="font-medium text-red-600 tabular-nums">${position.stop?.toLocaleString()}</span>
              </div>
            )}
            {position.target && (
              <div className="flex justify-between">
                <span className="text-gray-500">Target</span>
                <span className="font-medium text-green-600 tabular-nums">${position.target?.toLocaleString()}</span>
              </div>
            )}
            {position.rr && (
              <div className="flex justify-between">
                <span className="text-gray-500">R:R</span>
                <span className="font-semibold">{position.rr}</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

// Orders Tab Component
const OrdersTab = ({ orders, symbol }) => {
  const [allOrders, setAllOrders] = React.useState([]);
  const [showAll, setShowAll] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  const loadAllOrders = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/terminal/orders?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setAllOrders(data.orders || []);
        setShowAll(true);
      }
    } catch (e) {
      console.error('Failed to load orders:', e);
    }
    setLoading(false);
  };

  const displayOrders = showAll ? allOrders : orders;
  
  if (!displayOrders || displayOrders.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-sm p-6 text-center">
        <div className="text-sm text-gray-500 mb-3">No orders for {symbol}</div>
        <button
          onClick={loadAllOrders}
          disabled={loading}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          {loading ? 'Loading...' : 'Show all orders'}
        </button>
      </div>
    );
  }
  
  const statusColors = {
    ORDER_PLACED: 'text-blue-600',
    PARTIAL_FILL: 'text-purple-600',
    FILLED: 'text-green-600',
    CANCELLED: 'text-gray-500',
    REJECTED: 'text-red-600',
  };
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm overflow-hidden" data-testid="orders-tab">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Order ID</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Symbol</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Side</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Price</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Size</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Filled</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {displayOrders.map((order, idx) => (
            <tr key={order.order_id || idx} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-mono text-xs text-gray-600">
                {order.order_id?.slice(0, 8)}...
              </td>
              <td className="px-4 py-3 font-semibold">{order.symbol}</td>
              <td className={`px-4 py-3 font-semibold ${order.side === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>
                {order.side}
              </td>
              <td className={`px-4 py-3 font-medium ${statusColors[order.status] || 'text-gray-600'}`}>
                {order.status}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                ${order.price?.toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">{order.size}</td>
              <td className="px-4 py-3 text-right tabular-nums font-medium">
                {((order.filled_pct || 0) * 100).toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!showAll && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 text-center">
          <button
            onClick={loadAllOrders}
            disabled={loading}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            {loading ? 'Loading...' : 'Load all orders'}
          </button>
        </div>
      )}
    </div>
  );
};

// Portfolio Status Block Component - TT3
const PortfolioStatusBlock = ({ portfolio }) => {
  const equity = portfolio?.equity || 0;
  const freeCapital = portfolio?.free_capital || 0;
  const usedCapital = portfolio?.used_capital || 0;
  const realizedPnl = portfolio?.realized_pnl || 0;
  const unrealizedPnl = portfolio?.unrealized_pnl || 0;
  const dailyPnl = portfolio?.daily_pnl || 0;
  const grossExposure = portfolio?.gross_exposure || 0;
  const netExposure = portfolio?.net_exposure || 0;
  const openPositions = portfolio?.open_positions || 0;
  const openOrders = portfolio?.open_orders || 0;
  
  const exposureColor = grossExposure > 0.7 ? 'text-red-600' : grossExposure > 0.45 ? 'text-amber-600' : 'text-green-600';
  const pnlColor = dailyPnl >= 0 ? 'text-green-600' : 'text-red-600';
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="portfolio-status-block">
      <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
        Portfolio
      </h2>
      
      {/* Equity Header */}
      <div className="mb-4 pb-4 border-b border-gray-100">
        <div className="text-xs text-gray-500 uppercase tracking-wider">Equity</div>
        <div className="text-2xl font-bold text-gray-900">${equity.toLocaleString()}</div>
        <div className={`text-sm font-medium ${pnlColor}`}>
          {dailyPnl >= 0 ? '+' : ''}{dailyPnl.toLocaleString()} USD today
        </div>
      </div>
      
      {/* Capital Usage */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Capital Usage</span>
          <span className={`font-bold ${exposureColor}`}>{(grossExposure * 100).toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all ${grossExposure > 0.7 ? 'bg-red-500' : grossExposure > 0.45 ? 'bg-amber-500' : 'bg-green-500'}`}
            style={{ width: `${Math.min(grossExposure * 100, 100)}%` }}
          />
        </div>
      </div>
      
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-xs text-gray-500 block">Free Capital</span>
          <span className="font-semibold text-gray-900">${freeCapital.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Used Capital</span>
          <span className="font-semibold text-gray-900">${usedCapital.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Realized PnL</span>
          <span className={`font-semibold ${realizedPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {realizedPnl >= 0 ? '+' : ''}{realizedPnl.toLocaleString()}
          </span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Unrealized PnL</span>
          <span className={`font-semibold ${unrealizedPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {unrealizedPnl >= 0 ? '+' : ''}{unrealizedPnl.toLocaleString()}
          </span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Net Exposure</span>
          <span className="font-semibold text-gray-900">{(netExposure * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Positions / Orders</span>
          <span className="font-semibold text-gray-900">{openPositions} / {openOrders}</span>
        </div>
      </div>
    </div>
  );
};

// Risk Console Block Component - TT3
const RiskConsoleBlock = ({ risk }) => {
  const heat = risk?.heat || 0;
  const dailyDrawdown = risk?.daily_drawdown || 0;
  const maxDrawdown = risk?.max_drawdown || 0;
  const status = risk?.status || 'unknown';
  const killSwitch = risk?.kill_switch || false;
  const canOpenNew = risk?.can_open_new ?? true;
  const guardrailsCount = risk?.active_guardrails_count || risk?.active_guardrails?.length || 0;
  const blockCount = risk?.block_reasons_count || risk?.block_reasons?.length || 0;
  const alerts = risk?.risk_alerts || [];
  
  const statusColors = {
    normal: 'bg-green-100 text-green-700 border-green-200',
    warning: 'bg-amber-100 text-amber-700 border-amber-200',
    critical: 'bg-red-100 text-red-700 border-red-200',
    kill_switch: 'bg-red-600 text-white border-red-700',
    unknown: 'bg-gray-100 text-gray-600 border-gray-200',
  };
  
  const heatColor = heat > 0.7 ? 'text-red-600' : heat > 0.45 ? 'text-amber-600' : 'text-green-600';
  const heatBg = heat > 0.7 ? 'bg-red-500' : heat > 0.45 ? 'bg-amber-500' : 'bg-green-500';
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="risk-console-block">
      <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
        Risk Console
      </h2>
      
      {/* Status Badge */}
      <div className="flex items-center gap-2 mb-4">
        <span className={`px-3 py-1.5 rounded text-xs font-bold uppercase border ${statusColors[status.toLowerCase()] || statusColors.unknown}`}>
          {status.toUpperCase()}
        </span>
        {killSwitch && (
          <span className="px-2 py-1 rounded text-xs font-bold uppercase bg-red-600 text-white animate-pulse">
            KILL SWITCH
          </span>
        )}
        {!canOpenNew && !killSwitch && (
          <span className="px-2 py-1 rounded text-xs font-bold uppercase bg-amber-500 text-white">
            BLOCKED
          </span>
        )}
      </div>
      
      {/* Heat Gauge */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Portfolio Heat</span>
          <span className={`font-bold ${heatColor}`}>{(heat * 100).toFixed(0)}%</span>
        </div>
        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all ${heatBg}`}
            style={{ width: `${Math.min(heat * 100, 100)}%` }}
          />
        </div>
      </div>
      
      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-3 text-sm mb-4">
        <div>
          <span className="text-xs text-gray-500 block">Daily DD</span>
          <span className={`font-semibold ${dailyDrawdown > 0.05 ? 'text-red-600' : 'text-gray-900'}`}>
            {(dailyDrawdown * 100).toFixed(2)}%
          </span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Max DD</span>
          <span className={`font-semibold ${maxDrawdown > 0.1 ? 'text-red-600' : 'text-gray-900'}`}>
            {(maxDrawdown * 100).toFixed(2)}%
          </span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Guardrails</span>
          <span className={`font-semibold ${guardrailsCount > 0 ? 'text-amber-600' : 'text-green-600'}`}>
            {guardrailsCount} active
          </span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Block Reasons</span>
          <span className={`font-semibold ${blockCount > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {blockCount}
          </span>
        </div>
      </div>
      
      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="border-t border-gray-100 pt-3">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Alerts</div>
          <div className="space-y-1">
            {alerts.slice(0, 3).map((alert, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded">
                <span className="w-1.5 h-1.5 bg-amber-500 rounded-full flex-shrink-0"></span>
                <span className="truncate">{alert}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Trades Preview Block - TT4
const TradesPreviewBlock = ({ trades }) => {
  if (!trades || trades.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="trades-preview-block">
        <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
          Recent Trades
        </h2>
        <div className="text-center py-6">
          <div className="text-sm text-gray-400">No trades yet</div>
          <div className="text-xs text-gray-300 mt-1">Closed positions will appear here</div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="trades-preview-block">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase">
          Recent Trades
        </h2>
        <span className="text-xs font-medium text-gray-400">{trades.length}</span>
      </div>
      
      <div className="space-y-3">
        {trades.slice(0, 5).map((trade) => (
          <div key={trade.trade_id} className="flex justify-between items-center text-sm">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">{trade.symbol?.replace('USDT', '')}</span>
              <span className={`text-xs font-medium ${trade.side === 'LONG' ? 'text-green-600' : 'text-red-600'}`}>
                {trade.side}
              </span>
            </div>
            
            <div className="flex items-center gap-3">
              <span className={`font-bold tabular-nums ${
                trade.result === 'WIN' ? 'text-green-600' : 
                trade.result === 'LOSS' ? 'text-red-600' : 
                'text-gray-500'
              }`}>
                {trade.pnl >= 0 ? '+' : ''}{trade.pnl?.toFixed(0)}
              </span>
              
              <span className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                trade.result === 'WIN' ? 'bg-green-100 text-green-700' : 
                trade.result === 'LOSS' ? 'bg-red-100 text-red-700' : 
                'bg-gray-100 text-gray-600'
              }`}>
                {trade.result}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Trade Analytics Block - TT4
const TradeAnalyticsBlock = ({ data }) => {
  const trades = data?.trades || 0;
  const winRate = data?.win_rate || 0;
  const profitFactor = data?.profit_factor;
  const expectancy = data?.expectancy || 0;
  const avgRr = data?.avg_rr || 0;
  const netPnl = data?.net_pnl || 0;
  
  const winRateColor = winRate >= 0.6 ? 'text-green-600' : winRate >= 0.4 ? 'text-amber-600' : 'text-red-600';
  const pfColor = profitFactor && profitFactor >= 1.5 ? 'text-green-600' : profitFactor && profitFactor >= 1 ? 'text-amber-600' : 'text-red-600';
  const pnlColor = netPnl >= 0 ? 'text-green-600' : 'text-red-600';
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="trade-analytics-block">
      <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
        Performance
      </h2>
      
      {trades === 0 ? (
        <div className="text-center py-6">
          <div className="text-sm text-gray-400">No data</div>
          <div className="text-xs text-gray-300 mt-1">Complete trades to see analytics</div>
        </div>
      ) : (
        <>
          {/* Net PnL Header */}
          <div className="mb-4 pb-3 border-b border-gray-100">
            <div className="text-xs text-gray-500 uppercase tracking-wider">Net P&L</div>
            <div className={`text-2xl font-bold ${pnlColor}`}>
              {netPnl >= 0 ? '+' : ''}{netPnl.toLocaleString()}
            </div>
            <div className="text-xs text-gray-400">{trades} trades</div>
          </div>
          
          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-xs text-gray-500 block">Win Rate</span>
              <span className={`font-bold ${winRateColor}`}>
                {(winRate * 100).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">Profit Factor</span>
              <span className={`font-bold ${pfColor}`}>
                {profitFactor ? profitFactor.toFixed(2) : '—'}
              </span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">Expectancy</span>
              <span className={`font-bold ${expectancy >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {expectancy >= 0 ? '+' : ''}{expectancy.toFixed(0)}
              </span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">Avg R:R</span>
              <span className="font-bold text-gray-900">
                {avgRr ? avgRr.toFixed(2) : '—'}
              </span>
            </div>
          </div>
          
          {/* Win/Loss Bar */}
          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>{data?.wins || 0} wins</span>
              <span>{data?.losses || 0} losses</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden flex">
              <div 
                className="h-full bg-green-500"
                style={{ width: `${winRate * 100}%` }}
              />
              <div 
                className="h-full bg-red-500"
                style={{ width: `${(1 - winRate) * 100}%` }}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// Alpha Factory Summary Block - AF1 + AF2 Policy
const AlphaFactorySummaryBlock = () => {
  const [summary, setSummary] = React.useState(null);
  const [running, setRunning] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [submitResult, setSubmitResult] = React.useState(null);
  
  const fetchSummary = async () => {
    try {
      const res = await fetch(`${API_URL}/api/alpha-factory/summary`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data.data);
      }
    } catch (e) {
      console.error('Failed to fetch alpha summary:', e);
    }
  };
  
  const runAlphaFactory = async () => {
    try {
      setRunning(true);
      const res = await fetch(`${API_URL}/api/alpha-factory/run`, { method: 'POST' });
      if (res.ok) {
        await fetchSummary();
      }
    } catch (e) {
      console.error('Failed to run alpha factory:', e);
    } finally {
      setRunning(false);
    }
  };

  const submitViaPolicy = async () => {
    try {
      setSubmitting(true);
      setSubmitResult(null);
      const res = await fetch(`${API_URL}/api/alpha-factory/submit`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSubmitResult(data.data);
        await fetchSummary();
        setTimeout(() => setSubmitResult(null), 5000);
      }
    } catch (e) {
      console.error('Failed to submit via policy:', e);
    } finally {
      setSubmitting(false);
    }
  };
  
  React.useEffect(() => {
    fetchSummary();
    const interval = setInterval(fetchSummary, 30000);
    return () => clearInterval(interval);
  }, []);
  
  const strong = summary?.strong_edge || 0;
  const weak = summary?.weak_edge || 0;
  const unstable = summary?.unstable_edge || 0;
  const noEdge = summary?.no_edge || 0;
  const pendingCount = summary?.pending_actions || summary?.actionable_count || 0;
  
  const totalEvals = strong + weak + unstable + noEdge;
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-5" data-testid="alpha-factory-block">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase">
          Alpha Factory
        </h2>
        <div className="flex gap-2">
          <button
            onClick={submitViaPolicy}
            disabled={submitting || totalEvals === 0}
            className="text-xs font-medium text-purple-600 hover:text-purple-800 disabled:text-gray-400"
            data-testid="submit-policy-btn"
          >
            {submitting ? 'Submitting...' : 'Submit via Policy'}
          </button>
          <button
            onClick={runAlphaFactory}
            disabled={running}
            className="text-xs font-medium text-blue-600 hover:text-blue-800 disabled:text-gray-400"
            data-testid="run-alpha-btn"
          >
            {running ? 'Running...' : 'Run'}
          </button>
        </div>
      </div>
      
      {totalEvals === 0 ? (
        <div className="text-center py-6">
          <div className="text-sm text-gray-400">No analysis yet</div>
          <div className="text-xs text-gray-300 mt-1">Run Alpha Factory to analyze trades</div>
        </div>
      ) : (
        <>
          {/* Edge Distribution */}
          <div className="mb-4">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Edge Distribution</span>
              <span>{totalEvals} evaluated</span>
            </div>
            <div className="h-3 bg-gray-100 rounded-full overflow-hidden flex">
              {strong > 0 && (
                <div className="h-full bg-green-500" style={{ width: `${(strong / totalEvals) * 100}%` }} title={`Strong: ${strong}`} />
              )}
              {weak > 0 && (
                <div className="h-full bg-blue-400" style={{ width: `${(weak / totalEvals) * 100}%` }} title={`Weak: ${weak}`} />
              )}
              {unstable > 0 && (
                <div className="h-full bg-amber-400" style={{ width: `${(unstable / totalEvals) * 100}%` }} title={`Unstable: ${unstable}`} />
              )}
              {noEdge > 0 && (
                <div className="h-full bg-red-400" style={{ width: `${(noEdge / totalEvals) * 100}%` }} title={`No Edge: ${noEdge}`} />
              )}
            </div>
          </div>
          
          {/* Verdict Counts */}
          <div className="grid grid-cols-4 gap-2 text-center text-xs mb-4">
            <div>
              <div className="font-bold text-green-600">{strong}</div>
              <div className="text-gray-400">Strong</div>
            </div>
            <div>
              <div className="font-bold text-blue-500">{weak}</div>
              <div className="text-gray-400">Weak</div>
            </div>
            <div>
              <div className="font-bold text-amber-500">{unstable}</div>
              <div className="text-gray-400">Unstable</div>
            </div>
            <div>
              <div className="font-bold text-red-500">{noEdge}</div>
              <div className="text-gray-400">No Edge</div>
            </div>
          </div>

          {/* Submit Result */}
          {submitResult && (
            <div className="mb-3 p-2 bg-purple-50 border border-purple-200 rounded text-xs" data-testid="submit-result">
              <div className="font-bold text-purple-700 mb-1">Policy Result ({submitResult.alpha_mode})</div>
              <div className="flex gap-3">
                <span className="text-green-600">{submitResult.auto_applied} auto</span>
                <span className="text-amber-600">{submitResult.manual_queued} manual</span>
                <span className="text-red-600">{submitResult.blocked} blocked</span>
              </div>
            </div>
          )}
          
          {/* Pending Actions */}
          {pendingCount > 0 && (
            <div className="flex justify-between items-center p-2 bg-amber-50 border border-amber-200 rounded text-sm">
              <span className="text-amber-700 font-medium">{pendingCount} pending action{pendingCount > 1 ? 's' : ''}</span>
              <span className="text-xs text-amber-500">Review needed</span>
            </div>
          )}
          
          {pendingCount === 0 && (
            <div className="flex justify-between items-center p-2 bg-green-50 border border-green-200 rounded text-sm">
              <span className="text-green-700 font-medium">No actions required</span>
              <span className="text-xs text-green-500">System optimal</span>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// Operator Control Block - TT5 + AF2 Policy
const OperatorControlBlock = () => {
  const [controlState, setControlState] = React.useState(null);
  const [pending, setPending] = React.useState([]);
  const [policyState, setPolicyState] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [showPolicy, setShowPolicy] = React.useState(false);
  const [policyRules, setPolicyRules] = React.useState([]);
  
  const fetchControl = async () => {
    try {
      const [stateRes, pendingRes, policyRes] = await Promise.all([
        fetch(`${API_URL}/api/control/state`),
        fetch(`${API_URL}/api/control/alpha/pending`),
        fetch(`${API_URL}/api/alpha-policy/state`)
      ]);
      
      if (stateRes.ok) {
        const data = await stateRes.json();
        setControlState(data.data);
      }
      if (pendingRes.ok) {
        const data = await pendingRes.json();
        setPending(data.data || []);
      }
      if (policyRes.ok) {
        const data = await policyRes.json();
        setPolicyState(data.data);
      }
    } catch (e) {
      console.error('Failed to fetch control state:', e);
    }
  };
  
  const fetchRules = async () => {
    try {
      const res = await fetch(`${API_URL}/api/alpha-policy/rules`);
      if (res.ok) {
        const data = await res.json();
        setPolicyRules(data.data || []);
      }
    } catch (e) {
      console.error('Failed to fetch policy rules:', e);
    }
  };
  
  React.useEffect(() => {
    fetchControl();
    const interval = setInterval(fetchControl, 5000);
    return () => clearInterval(interval);
  }, []);
  
  const handleAction = async (action) => {
    setLoading(true);
    try {
      await fetch(`${API_URL}/api/control/${action}`, { method: 'POST' });
      await fetchControl();
    } catch (e) {
      console.error(`Failed to ${action}:`, e);
    }
    setLoading(false);
  };
  
  const handleAlphaMode = async (mode) => {
    setLoading(true);
    try {
      await fetch(`${API_URL}/api/control/alpha/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      await fetchControl();
    } catch (e) {
      console.error('Failed to set alpha mode:', e);
    }
    setLoading(false);
  };
  
  const handleApprove = async (pendingId) => {
    try {
      await fetch(`${API_URL}/api/control/alpha/approve/${pendingId}`, { method: 'POST' });
      await fetchControl();
    } catch (e) {
      console.error('Failed to approve:', e);
    }
  };
  
  const handleReject = async (pendingId) => {
    try {
      await fetch(`${API_URL}/api/control/alpha/reject/${pendingId}`, { method: 'POST' });
      await fetchControl();
    } catch (e) {
      console.error('Failed to reject:', e);
    }
  };

  const handleApproveAll = async () => {
    try {
      await fetch(`${API_URL}/api/control/alpha/approve-all`, { method: 'POST' });
      await fetchControl();
    } catch (e) {
      console.error('Failed to approve all:', e);
    }
  };

  const handleRejectAll = async () => {
    try {
      await fetch(`${API_URL}/api/control/alpha/reject-all`, { method: 'POST' });
      await fetchControl();
    } catch (e) {
      console.error('Failed to reject all:', e);
    }
  };

  const togglePolicyRules = () => {
    if (!showPolicy) fetchRules();
    setShowPolicy(!showPolicy);
  };
  
  if (!controlState) return null;
  
  const state = controlState.system_state || 'UNKNOWN';
  const alphaMode = controlState.alpha_mode || 'MANUAL';
  const ps = policyState?.state || {};
  
  const stateColors = {
    ACTIVE: 'bg-green-100 text-green-700 border-green-200',
    PAUSED: 'bg-amber-100 text-amber-700 border-amber-200',
    SOFT_KILL: 'bg-orange-100 text-orange-700 border-orange-200',
    HARD_KILL: 'bg-red-100 text-red-700 border-red-200',
    EMERGENCY: 'bg-red-600 text-white border-red-700',
  };
  
  return (
    <div className="bg-white border border-gray-200 rounded-sm shadow-sm p-4" data-testid="operator-control-block">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* System State Badge */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 uppercase tracking-wider">System</span>
          <span className={`px-3 py-1 rounded text-xs font-bold border ${stateColors[state] || 'bg-gray-100 text-gray-700'}`} data-testid="system-state-badge">
            {state}
          </span>
          {controlState.soft_kill && (
            <span className="px-2 py-1 rounded text-xs font-bold bg-orange-500 text-white">SOFT KILL</span>
          )}
          {controlState.hard_kill && (
            <span className="px-2 py-1 rounded text-xs font-bold bg-red-600 text-white animate-pulse">HARD KILL</span>
          )}
        </div>
        
        {/* Control Buttons */}
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => handleAction('pause')}
            disabled={loading || state === 'PAUSED'}
            className="px-3 py-1.5 rounded text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-50"
            data-testid="pause-btn"
          >
            Pause
          </button>
          <button
            onClick={() => handleAction('resume')}
            disabled={loading || state === 'ACTIVE'}
            className="px-3 py-1.5 rounded text-xs font-medium bg-green-100 hover:bg-green-200 text-green-700 disabled:opacity-50"
            data-testid="resume-btn"
          >
            Resume
          </button>
          <button
            onClick={() => handleAction('kill/soft')}
            disabled={loading}
            className="px-3 py-1.5 rounded text-xs font-medium bg-orange-100 hover:bg-orange-200 text-orange-700 disabled:opacity-50"
            data-testid="soft-kill-btn"
          >
            Soft Kill
          </button>
          <button
            onClick={() => handleAction('kill/hard')}
            disabled={loading}
            className="px-3 py-1.5 rounded text-xs font-medium bg-red-100 hover:bg-red-200 text-red-700 disabled:opacity-50"
            data-testid="hard-kill-btn"
          >
            Hard Kill
          </button>
        </div>
        
        {/* Alpha Mode Toggle */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Alpha</span>
          {['AUTO', 'MANUAL', 'OFF'].map(mode => (
            <button
              key={mode}
              onClick={() => handleAlphaMode(mode)}
              disabled={loading}
              data-testid={`alpha-mode-${mode.toLowerCase()}`}
              className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                alphaMode === mode
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* AF2 Policy Stats (compact) */}
      {policyState && (
        <div className="mt-3 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-4" data-testid="policy-stats">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Policy</span>
          <div className="flex gap-3 text-xs">
            <span className="text-green-600 font-semibold">{ps.total_auto_applied || 0} auto</span>
            <span className="text-amber-600 font-semibold">{ps.total_manual_queued || 0} manual</span>
            <span className="text-red-600 font-semibold">{ps.total_blocked || 0} blocked</span>
          </div>
          <button
            onClick={togglePolicyRules}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium ml-auto"
            data-testid="toggle-policy-rules"
          >
            {showPolicy ? 'Hide Rules' : 'Show Rules'}
          </button>
        </div>
      )}
      
      {/* Policy Rules Detail */}
      {showPolicy && policyRules.length > 0 && (
        <div className="mt-3 bg-gray-50 border border-gray-200 rounded p-3" data-testid="policy-rules-panel">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Auto-Apply Thresholds</div>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
            {policyRules.map(rule => (
              <div key={rule.action_type} className="bg-white border border-gray-100 rounded p-2">
                <div className="text-xs font-bold text-gray-800">{rule.action_type.replace(/_/g, ' ')}</div>
                <div className="text-xs text-gray-500 mt-1">
                  Confidence: <span className="font-semibold text-gray-700">{(rule.min_confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="text-xs text-gray-500">
                  Cooldown: <span className="font-semibold text-gray-700">{rule.cooldown_seconds >= 3600 ? `${rule.cooldown_seconds / 3600}h` : `${rule.cooldown_seconds / 60}m`}</span>
                </div>
                <div className="text-xs text-gray-500">
                  Min samples: <span className="font-semibold text-gray-700">{rule.min_sample_size}</span>
                </div>
                {rule.require_manual && (
                  <div className="text-xs font-bold text-amber-600 mt-1">ALWAYS MANUAL</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Pending Actions */}
      {pending.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500 uppercase tracking-wider">
              Pending Alpha Actions ({pending.length})
            </span>
            <div className="flex gap-2">
              <button
                onClick={handleApproveAll}
                className="px-2 py-0.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 rounded"
                data-testid="approve-all-btn"
              >
                Approve All
              </button>
              <button
                onClick={handleRejectAll}
                className="px-2 py-0.5 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded"
                data-testid="reject-all-btn"
              >
                Reject All
              </button>
            </div>
          </div>
          <div className="space-y-2">
            {pending.slice(0, 5).map(p => (
              <div key={p.pending_id} className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded p-2" data-testid={`pending-action-${p.pending_id}`}>
                <div>
                  <span className="font-medium text-sm text-gray-900">{p.scope_key}</span>
                  <span className="mx-2 text-gray-400">→</span>
                  <span className="text-sm font-bold text-amber-700">{p.action}</span>
                  <span className="ml-2 text-xs text-gray-500">{p.reason}</span>
                  {p.confidence > 0 && (
                    <span className="ml-2 text-xs text-gray-400">({(p.confidence * 100).toFixed(0)}%)</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(p.pending_id)}
                    className="px-2 py-1 text-xs font-bold bg-green-600 hover:bg-green-700 text-white rounded"
                    data-testid={`approve-${p.pending_id}`}
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(p.pending_id)}
                    className="px-2 py-1 text-xs font-bold bg-red-600 hover:bg-red-700 text-white rounded"
                    data-testid={`reject-${p.pending_id}`}
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TradingTerminal;
