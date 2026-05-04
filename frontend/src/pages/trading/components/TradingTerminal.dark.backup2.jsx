import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, TrendingUp, Activity, AlertTriangle, CheckCircle2, XCircle, Clock, Zap, Shield, Database } from 'lucide-react';
import TradingChart from '../../../components/charts/TradingChart';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const TradingTerminal = () => {
  const [symbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('4H');
  
  // State
  const [terminalState, setTerminalState] = useState(null);
  const [systemState, setSystemState] = useState(null);
  const [auditRecent, setAuditRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch all data
  const fetchData = useCallback(async () => {
    try {
      const [terminalRes, systemRes, auditRes] = await Promise.all([
        fetch(`${API_URL}/api/terminal/state/${symbol}?timeframe=${timeframe}`),
        fetch(`${API_URL}/api/execution-reality/system/state`),
        fetch(`${API_URL}/api/audit/summary?limit=15`)
      ]);

      const terminalData = await terminalRes.json();
      const systemData = await systemRes.json();
      const auditData = await auditRes.json();

      if (terminalData.ok && terminalData.data) setTerminalState(terminalData.data);
      if (systemData.ok) setSystemState(systemData);
      if (auditData.ok && auditData.events) setAuditRecent(auditData.events);

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Data fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0C1A2B] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-gray-700 border-t-[#04A584] rounded-full animate-spin" />
          <p className="text-sm text-gray-400 font-medium">Loading Terminal...</p>
        </div>
      </div>
    );
  }

  const execHealth = systemState?.execution_health || {};
  const positions = systemState?.positions || [];
  const openOrders = systemState?.open_orders || [];
  const dlqItems = systemState?.dlq_summary?.items || [];
  const decision = terminalState?.decision || {};
  const meta = terminalState?.meta || {};
  const portfolio = terminalState?.portfolio || {};
  const risk = terminalState?.risk || {};
  const analysis = terminalState?.analysis || {};

  const circuitState = execHealth.circuit_breaker?.state || 'UNKNOWN';
  const rateLimiter = execHealth.rate_limiter || {};
  const latency = execHealth.latency || {};
  const queueData = execHealth.queue || {};

  return (
    <div className="min-h-screen bg-[#0C1A2B]" style={{ fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <header className="bg-[#0C1A2B] border-b border-gray-800 sticky top-0 z-10">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <h1 className="text-2xl font-semibold text-white">Trading OS</h1>
              <div className="h-8 w-px bg-gray-700" />
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">Symbol:</span>
                <span className="text-lg font-semibold text-white">{symbol}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">Timeframe:</span>
                <div className="flex gap-1">
                  {['1H', '4H', '1D'].map(tf => (
                    <button
                      key={tf}
                      onClick={() => setTimeframe(tf)}
                      className={`px-3 py-1 text-sm font-medium rounded-lg transition-all ${
                        timeframe === tf
                          ? 'bg-[#04A584] text-white'
                          : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={fetchData}
                className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
                title="Refresh"
              >
                <RefreshCw className="w-5 h-5 text-gray-400" />
              </button>
              <div className="text-xs text-gray-500">
                {lastUpdate && `Updated: ${lastUpdate.toLocaleTimeString()}`}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6 max-w-[1920px] mx-auto">
        <div className="grid grid-cols-12 gap-4">
          
          {/* Left Column - Stats */}
          <div className="col-span-3 space-y-4">
            
            {/* Portfolio Card */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white">Portfolio</h3>
                <Database className="w-4 h-4 text-[#04A584]" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Equity</span>
                  <span className="text-lg font-bold text-white">
                    ${(portfolio?.equity?.equity || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Unrealized PnL</span>
                  <span className={`text-sm font-semibold ${
                    (portfolio?.pnl?.unrealized?.total_unrealized || 0) >= 0 ? 'text-[#04A584]' : 'text-red-400'
                  }`}>
                    {(portfolio?.pnl?.unrealized?.total_unrealized || 0) >= 0 ? '+' : ''}
                    ${(portfolio?.pnl?.unrealized?.total_unrealized || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Realized PnL</span>
                  <span className={`text-sm font-semibold ${
                    (portfolio?.pnl?.realized?.total_realized || 0) >= 0 ? 'text-[#04A584]' : 'text-red-400'
                  }`}>
                    ${(portfolio?.pnl?.realized?.total_realized || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Drawdown</span>
                  <span className="text-sm text-gray-300">
                    {(portfolio?.drawdown?.current_dd_pct || 0).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Execution Health */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white">Execution Health</h3>
                {execHealth.status === 'HEALTHY' ? (
                  <CheckCircle2 className="w-4 h-4 text-[#04A584]" />
                ) : execHealth.status === 'WARNING' ? (
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-400" />
                )}
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Status</span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    execHealth.status === 'HEALTHY' ? 'bg-[#04A584]/20 text-[#04A584]' :
                    execHealth.status === 'WARNING' ? 'bg-amber-400/20 text-amber-400' :
                    'bg-red-400/20 text-red-400'
                  }`}>
                    {execHealth.status || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">P95 Latency</span>
                  <span className="text-sm text-gray-300">
                    {latency.p95_submit_to_fill_ms?.toFixed(0) || '0'}ms
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Circuit</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                    circuitState === 'CLOSED' ? 'bg-[#04A584]/20 text-[#04A584]' : 'bg-red-400/20 text-red-400'
                  }`}>
                    {circuitState}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Rate Limit</span>
                  <span className="text-sm text-gray-300">
                    {rateLimiter.available_tokens || 0}/{rateLimiter.capacity || 0}
                  </span>
                </div>
              </div>
            </div>

            {/* Queue Metrics */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white">Queue</h3>
                <Activity className="w-4 h-4 text-purple-400" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Depth</span>
                  <span className="text-lg font-bold text-white">
                    {queueData.queue_depth || 0}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Inflight</span>
                  <span className="text-sm text-gray-300">
                    {queueData.inflight_orders || 0}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Pressure</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                    queueData.pressure_level === 'NORMAL' ? 'bg-[#04A584]/20 text-[#04A584]' :
                    queueData.pressure_level === 'HIGH' ? 'bg-amber-400/20 text-amber-400' :
                    'bg-red-400/20 text-red-400'
                  }`}>
                    {queueData.pressure_level || 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* Decision Engine */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white">Decision</h3>
                <Zap className="w-4 h-4 text-amber-400" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Mode</span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    decision.mode === 'GO_FULL' ? 'bg-[#04A584]/20 text-[#04A584]' :
                    decision.mode === 'WAIT' ? 'bg-amber-400/20 text-amber-400' :
                    'bg-gray-700 text-gray-300'
                  }`}>
                    {decision.mode || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Action</span>
                  <span className={`text-sm font-semibold ${
                    decision.action === 'BUY' ? 'text-[#04A584]' :
                    decision.action === 'SELL' ? 'text-red-400' :
                    'text-gray-300'
                  }`}>
                    {decision.action || 'WAIT'}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Confidence</span>
                  <span className="text-sm text-gray-300">
                    {decision.confidence?.toFixed(2) || '0.00'}
                  </span>
                </div>
              </div>
            </div>

            {/* Risk */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white">Risk</h3>
                <Shield className="w-4 h-4 text-blue-400" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Heat</span>
                  <span className={`text-sm font-semibold ${
                    (risk.heat || 0) > 5 ? 'text-red-400' :
                    (risk.heat || 0) > 2 ? 'text-amber-400' :
                    'text-[#04A584]'
                  }`}>
                    {(risk.heat || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Kill Switch</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                    risk.kill_switch ? 'bg-red-400/20 text-red-400' : 'bg-[#04A584]/20 text-[#04A584]'
                  }`}>
                    {risk.kill_switch ? 'ACTIVE' : 'OFF'}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-gray-400">Can Trade</span>
                  <span className="text-sm text-gray-300">
                    {risk.can_open_new ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>
            </div>

          </div>

          {/* Middle Column - Chart */}
          <div className="col-span-6 space-y-4">
            <div className="bg-[#0F1F30] rounded-xl p-6 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <TradingChart 
                symbol={symbol} 
                timeframe={timeframe}
                height={700}
              />
            </div>

            {/* Analysis Summary */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <h3 className="text-sm font-semibold text-white mb-3">Analysis</h3>
              <div className="grid grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-gray-400 block mb-1">Regime</span>
                  <span className="text-white font-medium">{analysis.context?.market_regime || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-gray-400 block mb-1">Trend</span>
                  <span className="text-white font-medium">{analysis.structure_analysis?.trend_state || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-gray-400 block mb-1">Bias</span>
                  <span className={`font-medium ${
                    analysis.structure_analysis?.structural_bias === 'BULLISH' ? 'text-[#04A584]' :
                    analysis.structure_analysis?.structural_bias === 'BEARISH' ? 'text-red-400' :
                    'text-gray-300'
                  }`}>
                    {analysis.structure_analysis?.structural_bias || 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Orders & Audit */}
          <div className="col-span-3 space-y-4">
            
            {/* Positions */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <h3 className="text-sm font-semibold text-white mb-3">Positions ({positions.length})</h3>
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {positions.length > 0 ? positions.map((pos, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                    <div>
                      <div className="text-sm font-medium text-white">{pos.symbol}</div>
                      <div className="text-xs text-gray-400">{pos.side} • {pos.size}</div>
                    </div>
                    <div className="text-right">
                      <div className={`text-sm font-semibold ${
                        (pos.unrealized_pnl || 0) >= 0 ? 'text-[#04A584]' : 'text-red-400'
                      }`}>
                        {(pos.unrealized_pnl || 0) >= 0 ? '+' : ''}${(pos.unrealized_pnl || 0).toFixed(2)}
                      </div>
                      <div className="text-xs text-gray-400">${pos.entry_price?.toFixed(2) || '0'}</div>
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-6 text-sm text-gray-500">No open positions</div>
                )}
              </div>
            </div>

            {/* Open Orders */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <h3 className="text-sm font-semibold text-white mb-3">Orders ({openOrders.length})</h3>
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {openOrders.length > 0 ? openOrders.slice(0, 10).map((order, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                    <div>
                      <div className="text-sm font-medium text-white">{order.symbol}</div>
                      <div className="text-xs text-gray-400">{order.order_type} • {order.side}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-white">${order.price?.toFixed(2) || '0'}</div>
                      <div className="text-xs text-gray-400">{order.qty}</div>
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-6 text-sm text-gray-500">No active orders</div>
                )}
              </div>
            </div>

            {/* DLQ (if any) */}
            {dlqItems.length > 0 && (
              <div className="bg-[#0F1F30] rounded-xl p-4 border border-red-900" style={{ boxShadow: '2px 2px 8px 0px #ff000020' }}>
                <h3 className="text-sm font-semibold text-red-400 mb-3">Dead Letter Queue ({dlqItems.length})</h3>
                <div className="space-y-2 max-h-[200px] overflow-y-auto">
                  {dlqItems.map((item, idx) => (
                    <div key={idx} className="text-xs text-gray-400 py-1 border-b border-gray-800 last:border-0">
                      <div className="text-red-400 font-medium">{item.error_type}</div>
                      <div className="truncate">{item.reason}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Audit Trail */}
            <div className="bg-[#0F1F30] rounded-xl p-4 border border-gray-800" style={{ boxShadow: '2px 2px 8px 0px #00053014' }}>
              <h3 className="text-sm font-semibold text-white mb-3">Audit Trail</h3>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {auditRecent.length > 0 ? auditRecent.map((event, idx) => (
                  <div key={idx} className="flex items-start gap-2 py-2 border-b border-gray-800 last:border-0">
                    <Clock className="w-3 h-3 text-gray-500 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-white truncate">{event.source || event.type}</span>
                        <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
                          {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5 truncate">
                        {event.decision_mode || event.action || event.event_type || 'Event'}
                        {event.symbol && ` • ${event.symbol}`}
                      </div>
                      {event.trace_id && (
                        <div className="text-xs text-[#04A584] font-mono mt-0.5 truncate">
                          {event.trace_id.substring(0, 12)}...
                        </div>
                      )}
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-6 text-sm text-gray-500">No audit events</div>
                )}
              </div>
            </div>

          </div>

        </div>
      </main>
    </div>
  );
};

export default TradingTerminal;
