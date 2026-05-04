/**
 * ChartLab — Research Main Screen
 * 
 * Chart-first research interface
 * Uses real backend /api/v1/chart/full-analysis endpoint
 */

import React, { useState, useEffect, useCallback } from 'react';
import { UnifiedResearchChart } from '../../components/chart-engine/UnifiedResearchChart';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// ═══════════════════════════════════════════════════════════════
// DATA FETCHING
// ═══════════════════════════════════════════════════════════════

async function fetchChartAnalysis(symbol, timeframe) {
  try {
    const response = await fetch(
      `${API_URL}/api/v1/chart/full-analysis/${symbol}/${timeframe}?include_hypothesis=true&include_fractals=true`
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch chart analysis:', error);
    return null;
  }
}

// ═══════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════

export function ChartLab() {
  const [symbol, setSymbol] = useState('BTC');
  const [timeframe, setTimeframe] = useState('1D');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Chart data from backend
  const [chartData, setChartData] = useState({
    candles: [],
    volume: [],
    objects: [],
    indicators: [],
    hypothesis: null,
    fractalMatches: [],
    marketRegime: 'unknown',
    stats: {},
  });
  
  // Sidebar panels
  const [activePanel, setActivePanel] = useState('regime');
  
  // ═══════════════════════════════════════════════════════════════
  // LOAD DATA
  // ═══════════════════════════════════════════════════════════════
  
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    const data = await fetchChartAnalysis(symbol, timeframe);
    
    if (data) {
      // Transform candles to TV format (Unix timestamp required!)
      const candles = (data.candles || []).map(c => {
        let time;
        if (typeof c.time === 'number') {
          time = c.time;
        } else if (c.timestamp) {
          time = Math.floor(new Date(c.timestamp).getTime() / 1000);
        } else if (typeof c.time === 'string') {
          time = Math.floor(new Date(c.time).getTime() / 1000);
        } else {
          time = Math.floor(Date.now() / 1000);
        }
        
        return {
          time,
          open: c.open || c.o,
          high: c.high || c.h,
          low: c.low || c.l,
          close: c.close || c.c,
          volume: c.volume || c.v || 0,
        };
      }).sort((a, b) => a.time - b.time);
      
      // Debug: log candle data
      console.log('ChartLab: Loaded', candles.length, 'candles');
      console.log('ChartLab: First candle:', candles[0]);
      console.log('ChartLab: Last candle:', candles[candles.length - 1]);
      
      setChartData({
        candles,
        volume: data.volume || [],
        objects: data.objects || [],
        indicators: data.indicators || [],
        hypothesis: data.hypothesis || null,
        fractalMatches: data.fractal_matches || [],
        marketRegime: data.market_regime || 'unknown',
        capitalFlowBias: data.capital_flow_bias || 'neutral',
        stats: data.stats || {},
        suggestedIndicators: data.suggested_indicators || [],
        activePreset: data.active_preset || 'default',
      });
    } else {
      setError('Failed to load chart data');
    }
    
    setLoading(false);
  }, [symbol, timeframe]);
  
  useEffect(() => {
    loadData();
  }, [loadData]);
  
  // ═══════════════════════════════════════════════════════════════
  // HANDLERS
  // ═══════════════════════════════════════════════════════════════
  
  const handleSymbolChange = (newSymbol) => {
    setSymbol(newSymbol);
  };
  
  const handleTimeframeChange = (newTimeframe) => {
    setTimeframe(newTimeframe);
  };
  
  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════
  
  return (
    <div className="chart-lab min-h-screen bg-slate-900" data-testid="chart-lab">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-slate-700">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-white">Chart Lab</h1>
          
          {/* Symbol Selector */}
          <div className="flex items-center gap-2">
            {['BTC', 'ETH', 'SOL'].map(s => (
              <button
                key={s}
                data-testid={`symbol-${s}`}
                onClick={() => handleSymbolChange(s)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  symbol === s
                    ? 'bg-blue-500 text-white'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        
        {/* Stats */}
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Regime:</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              chartData.marketRegime?.includes('up') ? 'bg-green-500/20 text-green-400' :
              chartData.marketRegime?.includes('down') ? 'bg-red-500/20 text-red-400' :
              'bg-slate-500/20 text-slate-400'
            }`}>
              {chartData.marketRegime || 'Unknown'}
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Objects:</span>
            <span className="text-white">{chartData.stats?.total_objects || 0}</span>
          </div>
          
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg text-sm hover:bg-slate-600 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex overflow-hidden">
        {/* Chart Area (main) */}
        <div className="flex-1 min-w-0 relative">
          {error ? (
            <div className="flex items-center justify-center h-[600px] text-red-400">
              {error}
            </div>
          ) : (
            <UnifiedResearchChart
              candles={chartData.candles}
              volume={chartData.volume}
              objects={chartData.objects}
              indicators={chartData.indicators}
              hypothesis={chartData.hypothesis}
              fractalMatches={chartData.fractalMatches}
              symbol={symbol}
              timeframe={timeframe}
              height={600}
              theme="dark"
              onTimeframeChange={handleTimeframeChange}
            />
          )}
        </div>
        
        {/* Sidebar Panels */}
        <div className="w-80 border-l border-slate-700 bg-slate-800/50">
          {/* Panel Tabs */}
          <div className="flex border-b border-slate-700">
            {[
              { id: 'regime', label: 'Regime' },
              { id: 'hypothesis', label: 'Hypothesis' },
              { id: 'patterns', label: 'Patterns' },
              { id: 'fractals', label: 'Fractals' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActivePanel(tab.id)}
                className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                  activePanel === tab.id
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          
          {/* Panel Content */}
          <div className="p-4 space-y-4 max-h-[550px] overflow-y-auto">
            {activePanel === 'regime' && (
              <RegimePanel 
                regime={chartData.marketRegime} 
                capitalFlow={chartData.capitalFlowBias}
              />
            )}
            
            {activePanel === 'hypothesis' && (
              <HypothesisPanel hypothesis={chartData.hypothesis} />
            )}
            
            {activePanel === 'patterns' && (
              <PatternsPanel objects={chartData.objects} />
            )}
            
            {activePanel === 'fractals' && (
              <FractalsPanel fractals={chartData.fractalMatches} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SIDEBAR PANELS
// ═══════════════════════════════════════════════════════════════

function RegimePanel({ regime, capitalFlow }) {
  return (
    <div className="space-y-4">
      <div className="p-3 bg-slate-700/50 rounded-lg">
        <div className="text-xs text-slate-400 mb-1">Market Regime</div>
        <div className={`text-lg font-bold ${
          regime?.includes('up') ? 'text-green-400' :
          regime?.includes('down') ? 'text-red-400' :
          'text-slate-300'
        }`}>
          {regime?.replace(/_/g, ' ').toUpperCase() || 'Unknown'}
        </div>
      </div>
      
      <div className="p-3 bg-slate-700/50 rounded-lg">
        <div className="text-xs text-slate-400 mb-1">Capital Flow Bias</div>
        <div className={`text-lg font-bold ${
          capitalFlow === 'bullish' ? 'text-green-400' :
          capitalFlow === 'bearish' ? 'text-red-400' :
          'text-slate-300'
        }`}>
          {capitalFlow?.toUpperCase() || 'Neutral'}
        </div>
      </div>
      
      <div className="text-xs text-slate-500">
        Regime determines which indicators and analysis methods are most relevant for current market conditions.
      </div>
    </div>
  );
}

function HypothesisPanel({ hypothesis }) {
  if (!hypothesis) {
    return <div className="text-slate-400 text-sm">No hypothesis data available</div>;
  }
  
  return (
    <div className="space-y-4">
      {/* Direction */}
      <div className="p-3 bg-slate-700/50 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-400">Direction</span>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            hypothesis.direction === 'bullish' ? 'bg-green-500/20 text-green-400' :
            hypothesis.direction === 'bearish' ? 'bg-red-500/20 text-red-400' :
            'bg-slate-500/20 text-slate-400'
          }`}>
            {hypothesis.direction?.toUpperCase() || 'NEUTRAL'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-slate-600 rounded-full overflow-hidden">
            <div 
              className={`h-full ${
                hypothesis.direction === 'bullish' ? 'bg-green-500' :
                hypothesis.direction === 'bearish' ? 'bg-red-500' :
                'bg-slate-400'
              }`}
              style={{ width: `${(hypothesis.confidence || 0) * 100}%` }}
            />
          </div>
          <span className="text-xs text-slate-300">
            {((hypothesis.confidence || 0) * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      
      {/* Scenarios */}
      {hypothesis.scenarios?.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs text-slate-400 font-medium">Scenarios</div>
          {hypothesis.scenarios.map((scenario, i) => (
            <div key={i} className="p-2 bg-slate-700/30 rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-white capitalize">{scenario.type}</span>
                <span className="text-xs text-slate-400">
                  {(scenario.probability * 100).toFixed(0)}% prob
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Target:</span>
                {(() => {
                  const pct = scenario.target_pct ?? (
                    hypothesis.current_price && scenario.target_price
                      ? (scenario.target_price - hypothesis.current_price) / hypothesis.current_price
                      : null
                  );
                  return pct !== null ? (
                    <span className={pct > 0 ? 'text-green-400' : 'text-red-400'}>
                      {pct > 0 ? '+' : ''}{(pct * 100).toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-white">
                      ${scenario.target_price?.toFixed(0) || '—'}
                    </span>
                  );
                })()}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Entry/Exit */}
      {(hypothesis.entry_zone || hypothesis.stop_loss || hypothesis.take_profit) && (
        <div className="space-y-2">
          <div className="text-xs text-slate-400 font-medium">Levels</div>
          
          {hypothesis.entry_zone && (
            <div className="flex items-center justify-between p-2 bg-blue-500/10 rounded">
              <span className="text-xs text-blue-400">Entry Zone</span>
              <span className="text-xs text-white">
                {Array.isArray(hypothesis.entry_zone) 
                  ? `$${hypothesis.entry_zone[0]} - $${hypothesis.entry_zone[1]}`
                  : `$${hypothesis.entry_zone}`
                }
              </span>
            </div>
          )}
          
          {hypothesis.stop_loss && (
            <div className="flex items-center justify-between p-2 bg-red-500/10 rounded">
              <span className="text-xs text-red-400">Stop Loss</span>
              <span className="text-xs text-white">${hypothesis.stop_loss}</span>
            </div>
          )}
          
          {hypothesis.take_profit && (
            <div className="flex items-center justify-between p-2 bg-green-500/10 rounded">
              <span className="text-xs text-green-400">Take Profit</span>
              <span className="text-xs text-white">
                {Array.isArray(hypothesis.take_profit)
                  ? hypothesis.take_profit.map(tp => `$${tp}`).join(' / ')
                  : `$${hypothesis.take_profit}`
                }
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PatternsPanel({ objects }) {
  const patterns = objects?.filter(o => o.category === 'pattern' || o.category === 'geometry') || [];
  
  if (patterns.length === 0) {
    return <div className="text-slate-400 text-sm">No patterns detected</div>;
  }
  
  return (
    <div className="space-y-2">
      {patterns.map((pattern, i) => (
        <div key={i} className="p-2 bg-slate-700/30 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm text-white capitalize">
              {pattern.type?.replace(/_/g, ' ')}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              pattern.confidence > 0.7 ? 'bg-green-500/20 text-green-400' :
              pattern.confidence > 0.5 ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-slate-500/20 text-slate-400'
            }`}>
              {((pattern.confidence || 0) * 100).toFixed(0)}%
            </span>
          </div>
          {pattern.label && (
            <div className="text-xs text-slate-400 mt-1">{pattern.label}</div>
          )}
        </div>
      ))}
    </div>
  );
}

function FractalsPanel({ fractals }) {
  if (!fractals || fractals.length === 0) {
    return <div className="text-slate-400 text-sm">No fractal matches</div>;
  }
  
  return (
    <div className="space-y-2">
      {fractals.map((fractal, i) => (
        <div key={i} className="p-2 bg-slate-700/30 rounded-lg">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-white">Match #{i + 1}</span>
            <span className="text-xs text-purple-400">
              {((fractal.similarity || 0) * 100).toFixed(0)}% similar
            </span>
          </div>
          {fractal.date && (
            <div className="text-xs text-slate-400">
              Reference: {fractal.date}
            </div>
          )}
          {fractal.expected_return !== undefined && (
            <div className="text-xs mt-1">
              <span className="text-slate-400">Expected: </span>
              <span className={fractal.expected_return > 0 ? 'text-green-400' : 'text-red-400'}>
                {fractal.expected_return > 0 ? '+' : ''}{(fractal.expected_return * 100).toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default ChartLab;
