import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Wifi, WifiOff } from 'lucide-react';

// Layout
import { TerminalGrid, TerminalSection } from '../../../components/terminal/layout';

// Intelligence Blocks
import {
  PortfolioIntelligenceBlock,
  MetaLayerBlock,
  LifecycleControlBlock,
  LearningStatusBlock,
  SystemHealthBlock,
  GuardActionsBlock,
  AuditTrailBlock,
  ExecutionQueueBlock,
  ExecutionHealthBlock
} from '../../../components/terminal/intelligence';

// Existing components (from old terminal)
import TradingChart from '../../../components/charts/TradingChart';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Valid timeframes
const TIMEFRAMES = ['1H', '4H', '1D'];

const TradingTerminal = () => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('4H');
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);  // P0.6 Risk Guard

  // Fetch terminal state
  const loadState = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/terminal/state/${symbol}?timeframe=${timeframe}`);
      if (!response.ok) throw new Error(`Failed: ${response.status}`);
      
      const data = await response.json();
      if (data.ok && data.data) {
        setState(data.data);
        setLastUpdate(new Date());
        setConnected(true);
      }
    } catch (error) {
      console.error('Terminal state error:', error);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe]);

  // Fetch system health (P0.6)
  const loadHealth = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/execution-reality/health`);
      if (!response.ok) throw new Error(`Health fetch failed: ${response.status}`);
      
      const health = await response.json();
      setSystemHealth(health);
    } catch (error) {
      console.error('System health error:', error);
      setSystemHealth(null);
    }
  }, []);

  useEffect(() => {
    loadState();
    loadHealth();  // P0.6
    const interval = setInterval(() => {
      loadState();
      loadHealth();  // P0.6
    }, 3000);
    return () => clearInterval(interval);
  }, [loadState, loadHealth]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0E13] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gray-700 border-t-cyan-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0E13] text-gray-100">
      {/* Header */}
      <div className="bg-[#0F141A] border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <h1 className="text-xl font-semibold text-white">Trading Terminal</h1>
            
            {/* Symbol */}
            <div>
              <span className="text-sm text-gray-500 mr-2">Symbol:</span>
              <span className="text-base font-medium text-white">{symbol}</span>
            </div>

            {/* Timeframe Selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Timeframe:</span>
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                    timeframe === tf
                      ? 'bg-cyan-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center gap-4">
            <button
              onClick={loadState}
              className="p-2 rounded hover:bg-gray-800 transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4 text-gray-400" />
            </button>
            
            <div className="flex items-center gap-2">
              {connected ? (
                <>
                  <Wifi className="w-4 h-4 text-green-500" />
                  <span className="text-xs text-gray-500">
                    {lastUpdate && lastUpdate.toLocaleTimeString()}
                  </span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4 text-red-500" />
                  <span className="text-xs text-red-500">Disconnected</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6">
        <TerminalGrid>
          {/* LEVEL 1 - COMMAND STATE */}
          <TerminalSection title="System State">
            <div className="grid grid-cols-4 gap-4">
              <PortfolioIntelligenceBlock portfolio={state?.portfolio} />
              <MetaLayerBlock meta={state?.meta} meta_execution={state?.meta_execution} />
              <LifecycleControlBlock lifecycle_control={state?.lifecycle_control} />
              <LearningStatusBlock meta_learning={state?.meta_learning} meta={state?.meta} />
            </div>
          </TerminalSection>

          {/* LEVEL 1.5 - SYSTEM RISK (P0.6 Risk Guard + P1.1 Queue) */}
          <TerminalSection title="System Risk">
            <div className="grid grid-cols-4 gap-4">
              <SystemHealthBlock health={systemHealth} />
              <GuardActionsBlock actions={systemHealth?.actions} />
              <ExecutionQueueBlock />
              <ExecutionHealthBlock />
            </div>
          </TerminalSection>

          {/* LEVEL 2 - MARKET INTELLIGENCE */}
          <TerminalSection title="Market Intelligence">
            <div className="bg-[#0A0E13] border border-gray-800 rounded-lg p-4">
              <TradingChart 
                symbol={symbol} 
                timeframe={timeframe}
                height={500}
              />
            </div>
          </TerminalSection>

          {/* LEVEL 3 - DECISION & ENFORCEMENT */}
          <TerminalSection title="Decision & Enforcement">
            <div className="grid grid-cols-2 gap-4">
              {/* Decision Block */}
              <div className="bg-[#0A0E13] border border-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-400 mb-3">Decision</div>
                {state?.decision ? (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-500">Mode</span>
                      <span className={`text-sm font-medium px-2 py-1 rounded ${
                        state.decision.mode === 'GO_FULL' ? 'bg-green-600 text-white' :
                        state.decision.mode === 'WAIT' ? 'bg-amber-500 text-white' :
                        'bg-gray-600 text-white'
                      }`}>
                        {state.decision.mode}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">Side</span>
                      <span className={`text-sm font-medium ${
                        state.decision.side === 'LONG' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {state.decision.side}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-gray-600">No decision data</div>
                )}
              </div>

              {/* Enforcement Block */}
              <div className="bg-[#0A0E13] border border-gray-800 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-400 mb-3">Enforcement</div>
                {state ? (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-500">Final Action</span>
                      <span className={`text-sm font-medium px-2 py-1 rounded ${
                        state.blocked ? 'bg-red-600 text-white' :
                        state.final_action === 'ALLOW' ? 'bg-green-600 text-white' :
                        'bg-amber-600 text-white'
                      }`}>
                        {state.blocked ? 'BLOCKED' : state.final_action}
                      </span>
                    </div>
                    {state.blocked && state.block_reason && (
                      <div className="text-xs text-red-400 mt-2">
                        Reason: {state.block_reason}
                      </div>
                    )}
                    {state.reason_chain && state.reason_chain.length > 0 && (
                      <div className="mt-2">
                        <div className="text-xs text-gray-600 mb-1">Reason Chain:</div>
                        <div className="text-xs text-gray-500 space-y-0.5">
                          {state.reason_chain.slice(0, 3).map((reason, idx) => (
                            <div key={idx}>• {reason}</div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-gray-600">No enforcement data</div>
                )}
              </div>
            </div>
          </TerminalSection>

          {/* LEVEL 4 - EXECUTION STATUS */}
          <TerminalSection title="Execution Status">
            <div className="bg-[#0A0E13] border border-gray-800 rounded-lg p-4">
              {state?.execution_control?.intent ? (
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Action</div>
                    <div className="text-sm font-medium text-white">
                      {state.execution_control.intent.action}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Size</div>
                    <div className="text-sm font-medium text-white">
                      {state.execution_control.intent.size?.toFixed(4) || '0.0000'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Mode</div>
                    <div className="text-sm font-medium text-white">
                      {state.execution_control.intent.mode}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-600">No execution data</div>
              )}
            </div>
          </TerminalSection>
        </TerminalGrid>
      </div>
    </div>
  );
};

export default TradingTerminal;
