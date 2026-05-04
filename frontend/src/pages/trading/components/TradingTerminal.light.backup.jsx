import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, TrendingUp, TrendingDown, Activity, AlertTriangle, CheckCircle2, XCircle, Clock, BarChart3, Shield, Zap } from 'lucide-react';
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
      // 1. Terminal State (decision, meta, lifecycle, learning)
      const terminalRes = await fetch(`${API_URL}/api/terminal/state/${symbol}?timeframe=${timeframe}`);
      const terminalData = await terminalRes.json();
      if (terminalData.ok && terminalData.data) {
        setTerminalState(terminalData.data);
      }

      // 2. System State (P1 aggregator: execution reality + queue + positions + pnl + audit)
      const systemRes = await fetch(`${API_URL}/api/execution-reality/system/state`);
      const systemData = await systemRes.json();
      if (systemData.ok) {
        setSystemState(systemData);
      }

      // 3. Audit Recent (last 20 events)
      const auditRes = await fetch(`${API_URL}/api/audit/summary?limit=10`);
      const auditData = await auditRes.json();
      if (auditData.ok && auditData.events) {
        setAuditRecent(auditData.events);
      }

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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-sm text-gray-600 font-medium">Загрузка терминала...</p>
        </div>
      </div>
    );
  }

  const portfolio = systemState?.portfolio_stats || {};
  const executionHealth = systemState?.execution_health || {};
  const queueMetrics = systemState?.queue_metrics || {};
  const positions = systemState?.positions || [];
  const openOrders = systemState?.open_orders || [];
  const decision = terminalState?.decision || {};
  const meta = terminalState?.meta || {};

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <h1 className="text-2xl font-bold text-gray-900">Trading OS</h1>
              <div className="h-8 w-px bg-gray-200" />
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Символ:</span>
                <span className="text-lg font-semibold text-gray-900">{symbol}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Таймфрейм:</span>
                <div className="flex gap-1">
                  {['1H', '4H', '1D'].map(tf => (
                    <button
                      key={tf}
                      onClick={() => setTimeframe(tf)}
                      className={`px-3 py-1 text-sm font-medium rounded transition-all ${
                        timeframe === tf
                          ? 'bg-blue-600 text-white shadow-sm'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                title="Обновить"
              >
                <RefreshCw className="w-5 h-5 text-gray-600" />
              </button>
              <div className="text-xs text-gray-500">
                {lastUpdate && `Обновлено: ${lastUpdate.toLocaleTimeString()}`}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6 max-w-[1920px] mx-auto">
        <div className="space-y-6">
          
          {/* Portfolio & System State */}
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Состояние системы</h2>
            <div className="grid grid-cols-4 gap-4">
              {/* Portfolio */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-gray-700">Портфель</h3>
                  <BarChart3 className="w-4 h-4 text-blue-600" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Баланс</span>
                    <span className="text-lg font-bold text-gray-900">
                      ${(portfolio.total_balance_usd || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Unrealized PnL</span>
                    <span className={`text-sm font-semibold ${
                      (portfolio.unrealized_pnl_usd || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {(portfolio.unrealized_pnl_usd || 0) >= 0 ? '+' : ''}
                      ${(portfolio.unrealized_pnl_usd || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Комиссии</span>
                    <span className="text-sm text-gray-700">
                      ${Math.abs(portfolio.total_fees_usd || 0).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Execution Health */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-gray-700">Execution Health</h3>
                  {executionHealth.status === 'HEALTHY' ? (
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                  ) : executionHealth.status === 'WARNING' ? (
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-600" />
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Статус</span>
                    <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                      executionHealth.status === 'HEALTHY' ? 'bg-green-100 text-green-700' :
                      executionHealth.status === 'WARNING' ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {executionHealth.status || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Latency</span>
                    <span className="text-sm text-gray-700">
                      {executionHealth.latency_health?.p95_latency_ms?.toFixed(0) || '0'}ms
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Circuit</span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                      executionHealth.circuit_breaker?.state === 'CLOSED' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {executionHealth.circuit_breaker?.state || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Queue */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-gray-700">Очередь</h3>
                  <Activity className="w-4 h-4 text-purple-600" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">В очереди</span>
                    <span className="text-lg font-bold text-gray-900">
                      {queueMetrics.queue_depth || 0}
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Обработка</span>
                    <span className="text-sm text-gray-700">
                      {queueMetrics.inflight_count || 0}
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Успешно</span>
                    <span className="text-sm text-green-600">
                      {queueMetrics.total_processed || 0}
                    </span>
                  </div>
                </div>
              </div>

              {/* Decision Engine */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-gray-700">Decision</h3>
                  <Zap className="w-4 h-4 text-amber-600" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Режим</span>
                    <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                      decision.mode === 'GO_FULL' ? 'bg-green-100 text-green-700' :
                      decision.mode === 'WAIT' ? 'bg-amber-100 text-amber-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {decision.mode || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Сторона</span>
                    <span className={`text-sm font-semibold ${
                      decision.side === 'LONG' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {decision.side || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs text-gray-500">Уверенность</span>
                    <span className="text-sm text-gray-700">
                      {meta.final_confidence?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Chart */}
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">График</h2>
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <TradingChart 
                symbol={symbol} 
                timeframe={timeframe}
                height={600}
              />
            </div>
          </section>

          {/* Positions & Orders */}
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Позиции и ордера</h2>
            <div className="grid grid-cols-2 gap-6">
              {/* Positions */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Открытые позиции</h3>
                {positions.length > 0 ? (
                  <div className="space-y-2">
                    {positions.map((pos, idx) => (
                      <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                        <div>
                          <div className="text-sm font-semibold text-gray-900">{pos.symbol}</div>
                          <div className="text-xs text-gray-500">{pos.side} • {pos.quantity}</div>
                        </div>
                        <div className="text-right">
                          <div className={`text-sm font-semibold ${
                            (pos.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {(pos.unrealized_pnl || 0) >= 0 ? '+' : ''}${(pos.unrealized_pnl || 0).toFixed(2)}
                          </div>
                          <div className="text-xs text-gray-500">{pos.entry_price}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-sm text-gray-500">
                    Нет открытых позиций
                  </div>
                )}
              </div>

              {/* Orders */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Активные ордера</h3>
                {openOrders.length > 0 ? (
                  <div className="space-y-2">
                    {openOrders.map((order, idx) => (
                      <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                        <div>
                          <div className="text-sm font-semibold text-gray-900">{order.symbol}</div>
                          <div className="text-xs text-gray-500">{order.type} • {order.side}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold text-gray-900">${order.price}</div>
                          <div className="text-xs text-gray-500">{order.quantity}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-sm text-gray-500">
                    Нет активных ордеров
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Audit Trail */}
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Audit Trail (последние события)</h2>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              {auditRecent.length > 0 ? (
                <div className="space-y-2">
                  {auditRecent.map((event, idx) => (
                    <div key={idx} className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
                      <Clock className="w-4 h-4 text-gray-400 mt-0.5" />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-900">{event.source || event.type}</span>
                          <span className="text-xs text-gray-500">
                            {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}
                          </span>
                        </div>
                        <div className="text-xs text-gray-600 mt-1">
                          {event.decision_mode || event.action || event.event_type || 'Event'}
                          {event.symbol && ` • ${event.symbol}`}
                          {event.trace_id && (
                            <span className="ml-2 text-blue-600 font-mono">
                              trace: {event.trace_id.substring(0, 8)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-sm text-gray-500">
                  Нет событий в audit trail
                </div>
              )}
            </div>
          </section>

        </div>
      </main>
    </div>
  );
};

export default TradingTerminal;
