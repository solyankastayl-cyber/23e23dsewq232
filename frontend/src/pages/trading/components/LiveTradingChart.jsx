/**
 * Live Trading Chart — Real-time chart with positions overlay
 * 
 * Features:
 * - Shows real open positions (entry, stop, target)
 * - Real-time price updates
 * - Technical analysis overlays
 * - Light design (matching system)
 * - Multi-symbol support (BTC + altcoins)
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Scatter,
  ReferenceDot
} from 'recharts';
import { 
  Layers, 
  TrendingUp, 
  Activity, 
  Calendar, 
  Triangle, 
  GitBranch,
  Target,
  ShieldAlert
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Custom Candlestick
const Candlestick = (props) => {
  const { x, y, width, height, low, high, openClose } = props;
  const isGrowing = openClose[1] > openClose[0];
  const color = isGrowing ? '#04A584' : '#EF4444';
  const ratio = Math.abs(height / (openClose[1] - openClose[0]));

  return (
    <g>
      {/* Wick */}
      <line
        x1={x + width / 2}
        y1={y}
        x2={x + width / 2}
        y2={y + height}
        stroke={color}
        strokeWidth={1.5}
      />
      {/* Body */}
      <rect
        x={x}
        y={y + (isGrowing ? (height - ratio * (openClose[1] - openClose[0])) : 0)}
        width={width}
        height={ratio * Math.abs(openClose[1] - openClose[0])}
        fill={color}
        stroke={color}
        strokeWidth={0}
      />
    </g>
  );
};

const LiveTradingChart = ({ symbol = 'BTCUSDT', height = 600 }) => {
  const [candles, setCandles] = useState([]);
  const [positions, setPositions] = useState([]);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Control states
  const [showPositions, setShowPositions] = useState(true);
  const [showRange, setShowRange] = useState(true);
  const [showSwings, setShowSwings] = useState(false);
  const [showTA, setShowTA] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000); // Update every 3s
    return () => clearInterval(interval);
  }, [symbol]);

  const fetchData = async () => {
    try {
      // Fetch candles
      const candlesRes = await fetch(`${API_URL}/api/market/candles?symbol=${symbol}&date_range=7d`);
      const candlesData = await candlesRes.json();
      
      if (candlesData.ok && candlesData.candles) {
        const transformed = candlesData.candles.map(c => ({
          time: new Date(c.time * 1000).toLocaleDateString('ru-RU', { 
            day: '2-digit', 
            month: 'short' 
          }),
          timestamp: c.time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
          volume: c.volume,
          openClose: [c.open, c.close],
          highLow: [c.low, c.high],
        }));
        
        setCandles(transformed);
        setCurrentPrice(transformed[transformed.length - 1]?.close);
      }

      // Fetch open positions
      const positionsRes = await fetch(`${API_URL}/api/trading/positions`);
      const positionsData = await positionsRes.json();
      
      if (positionsData.ok && positionsData.positions) {
        // Filter positions for current symbol
        const symbolPositions = positionsData.positions.filter(
          p => p.symbol === symbol
        );
        setPositions(symbolPositions);
      }
      
    } catch (error) {
      console.error('Chart data fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  // Calculate support/resistance
  const supportResistance = useMemo(() => {
    if (candles.length < 20) return { support: null, resistance: null };
    
    const recent = candles.slice(-20);
    const support = Math.min(...recent.map(c => c.low));
    const resistance = Math.max(...recent.map(c => c.high));
    
    return { support, resistance };
  }, [candles]);

  // Calculate swing points
  const swingPoints = useMemo(() => {
    if (!showSwings || candles.length < 5) return [];
    
    const swings = [];
    for (let i = 2; i < candles.length - 2; i++) {
      const c = candles[i];
      const prev = candles[i - 1];
      const next = candles[i + 1];
      
      // Swing high
      if (c.high > prev.high && c.high > next.high) {
        swings.push({
          time: c.time,
          timestamp: c.timestamp,
          price: c.high,
          type: 'high'
        });
      }
      
      // Swing low
      if (c.low < prev.low && c.low < next.low) {
        swings.push({
          time: c.time,
          timestamp: c.timestamp,
          price: c.low,
          type: 'low'
        });
      }
    }
    
    return swings;
  }, [candles, showSwings]);

  // Control buttons
  const controls = [
    { 
      id: 'positions', 
      label: 'Позиції', 
      icon: Layers, 
      active: showPositions, 
      toggle: () => setShowPositions(!showPositions),
      count: positions.length
    },
    { 
      id: 'range', 
      label: 'Рівні', 
      icon: TrendingUp, 
      active: showRange, 
      toggle: () => setShowRange(!showRange) 
    },
    { 
      id: 'swings', 
      label: 'Екстремуми', 
      icon: Activity, 
      active: showSwings, 
      toggle: () => setShowSwings(!showSwings) 
    },
    { 
      id: 'ta', 
      label: 'Технічний аналіз', 
      icon: Triangle, 
      active: showTA, 
      toggle: () => setShowTA(!showTA) 
    },
  ];

  if (loading) {
    return (
      <div className="bg-white rounded-xl p-6 border border-[#e6eaf2]" style={{ boxShadow: '2px 2px 8px rgba(0,5,48,0.06)', height }}>
        <div className="flex items-center justify-center h-full">
          <div className="text-sm text-gray-500">Завантаження графіка...</div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="bg-white rounded-xl p-4 border border-[#e6eaf2]" 
      style={{ boxShadow: '2px 2px 8px rgba(0,5,48,0.06)' }}
      data-testid="live-trading-chart"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-gray-900">{symbol}</h3>
          {currentPrice && (
            <div className="text-lg font-bold text-gray-900">
              ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          )}
          {positions.length > 0 && (
            <div className="px-2 py-1 bg-[#04A584] bg-opacity-10 text-[#04A584] rounded-md text-xs font-medium">
              {positions.length} {positions.length === 1 ? 'позиція' : 'позицій'}
            </div>
          )}
        </div>
        
        <div className="text-xs text-gray-500">
          1H • Оновлено щойно
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {controls.map(ctrl => {
          const Icon = ctrl.icon;
          return (
            <button
              key={ctrl.id}
              onClick={ctrl.toggle}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                transition-all duration-200
                ${ctrl.active 
                  ? 'bg-[#04A584] text-white shadow-sm' 
                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }
              `}
              data-testid={`chart-control-${ctrl.id}`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{ctrl.label}</span>
              {ctrl.count !== undefined && ctrl.count > 0 && (
                <span className="ml-1 px-1.5 py-0.5 bg-white bg-opacity-30 rounded text-[10px]">
                  {ctrl.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height - 120}>
        <ComposedChart
          data={candles}
          margin={{ top: 10, right: 50, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e6eaf2" />
          
          <XAxis 
            dataKey="time" 
            tick={{ fontSize: 11, fill: '#6B7280' }}
            stroke="#e6eaf2"
          />
          
          <YAxis 
            yAxisId="price"
            domain={['dataMin - 1000', 'dataMax + 1000']}
            tick={{ fontSize: 11, fill: '#6B7280' }}
            stroke="#e6eaf2"
            orientation="right"
          />
          
          <YAxis 
            yAxisId="volume"
            orientation="left"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            stroke="#e6eaf2"
          />
          
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e6eaf2',
              borderRadius: '8px',
              fontSize: '12px',
              padding: '8px 12px'
            }}
            formatter={(value, name) => {
              if (name === 'volume') return [value.toLocaleString(), 'Об\'єм'];
              return [`$${value.toFixed(2)}`, name];
            }}
          />
          
          {/* Volume bars */}
          <Bar 
            yAxisId="volume"
            dataKey="volume" 
            fill="#e6eaf2" 
            opacity={0.3}
            barSize={3}
          />
          
          {/* Candlesticks */}
          <Scatter
            yAxisId="price"
            data={candles}
            shape={<Candlestick />}
          />
          
          {/* Support/Resistance */}
          {showRange && supportResistance.support && (
            <ReferenceLine
              yAxisId="price"
              y={supportResistance.support}
              stroke="#04A584"
              strokeDasharray="5 5"
              strokeWidth={1.5}
              label={{ 
                value: `Підтримка $${supportResistance.support.toFixed(0)}`, 
                fontSize: 10, 
                fill: '#04A584', 
                position: 'insideBottomRight' 
              }}
            />
          )}
          
          {showRange && supportResistance.resistance && (
            <ReferenceLine
              yAxisId="price"
              y={supportResistance.resistance}
              stroke="#EF4444"
              strokeDasharray="5 5"
              strokeWidth={1.5}
              label={{ 
                value: `Опір $${supportResistance.resistance.toFixed(0)}`, 
                fontSize: 10, 
                fill: '#EF4444', 
                position: 'insideTopRight' 
              }}
            />
          )}
          
          {/* Current price */}
          {currentPrice && (
            <ReferenceLine
              yAxisId="price"
              y={currentPrice}
              stroke="#6B7280"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{ 
                value: `$${currentPrice.toFixed(2)}`, 
                fontSize: 11, 
                fill: '#6B7280', 
                position: 'right' 
              }}
            />
          )}
          
          {/* POSITION OVERLAYS */}
          {showPositions && positions.map((pos, idx) => {
            const side = pos.side?.toUpperCase();
            const isLong = side === 'LONG';
            
            return (
              <React.Fragment key={pos.position_id || idx}>
                {/* Entry Price */}
                <ReferenceLine
                  yAxisId="price"
                  y={pos.entry_price}
                  stroke={isLong ? '#04A584' : '#EF4444'}
                  strokeWidth={2}
                  label={{ 
                    value: `Вхід ${isLong ? 'LONG' : 'SHORT'} $${pos.entry_price?.toFixed(2)}`, 
                    fontSize: 10, 
                    fill: isLong ? '#04A584' : '#EF4444', 
                    position: 'insideLeft' 
                  }}
                />
                
                {/* Stop Loss */}
                {pos.stop_loss && (
                  <ReferenceLine
                    yAxisId="price"
                    y={pos.stop_loss}
                    stroke="#EF4444"
                    strokeDasharray="3 3"
                    strokeWidth={2}
                    label={{ 
                      value: `СТОП $${pos.stop_loss?.toFixed(2)}`, 
                      fontSize: 9, 
                      fill: '#EF4444', 
                      position: 'insideLeft' 
                    }}
                  />
                )}
                
                {/* Take Profit */}
                {pos.take_profit && (
                  <ReferenceLine
                    yAxisId="price"
                    y={pos.take_profit}
                    stroke="#04A584"
                    strokeDasharray="3 3"
                    strokeWidth={2}
                    label={{ 
                      value: `ЦІЛЬ $${pos.take_profit?.toFixed(2)}`, 
                      fontSize: 9, 
                      fill: '#04A584', 
                      position: 'insideLeft' 
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Position Summary */}
      {showPositions && positions.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
            Активні позиції
          </div>
          {positions.map((pos, idx) => {
            const isLong = pos.side?.toUpperCase() === 'LONG';
            const unrealizedPnl = pos.unrealized_pnl || 0;
            const isProfitable = unrealizedPnl > 0;
            
            return (
              <div 
                key={pos.position_id || idx}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className={`px-2 py-1 rounded text-xs font-medium ${
                    isLong 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {pos.side?.toUpperCase()}
                  </div>
                  <div className="text-sm text-gray-900">
                    {pos.size} {symbol.replace('USDT', '')}
                  </div>
                  <div className="text-xs text-gray-500">
                    @ ${pos.entry_price?.toFixed(2)}
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  {pos.stop_loss && (
                    <div className="flex items-center gap-1 text-xs">
                      <ShieldAlert className="w-3 h-3 text-red-500" />
                      <span className="text-gray-500">SL:</span>
                      <span className="font-medium text-red-600">
                        ${pos.stop_loss.toFixed(2)}
                      </span>
                    </div>
                  )}
                  
                  {pos.take_profit && (
                    <div className="flex items-center gap-1 text-xs">
                      <Target className="w-3 h-3 text-green-500" />
                      <span className="text-gray-500">TP:</span>
                      <span className="font-medium text-green-600">
                        ${pos.take_profit.toFixed(2)}
                      </span>
                    </div>
                  )}
                  
                  <div className={`text-sm font-bold ${
                    isProfitable ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {isProfitable ? '+' : ''}${unrealizedPnl.toFixed(2)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      
      {showPositions && positions.length === 0 && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg text-center text-sm text-gray-500">
          Немає відкритих позицій для {symbol}
        </div>
      )}
    </div>
  );
};

export default LiveTradingChart;
