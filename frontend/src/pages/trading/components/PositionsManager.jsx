/**
 * Positions Manager — Multi-symbol position management
 * 
 * Features:
 * - List all open positions (all symbols)
 * - View/Edit/Close positions
 * - Symbol selection
 * - Real-time P&L updates
 */

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  X, 
  Edit2, 
  Eye,
  Target,
  ShieldAlert,
  RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const PositionsManager = ({ onSymbolSelect }) => {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchPositions = async () => {
    try {
      const res = await fetch(`${API_URL}/api/trading/positions`);
      const data = await res.json();
      
      if (data.ok && data.positions) {
        setPositions(data.positions);
      }
    } catch (error) {
      console.error('Positions fetch error:', error);
    }
  };

  const handleClosePosition = async (positionId) => {
    if (!confirm('Закрити позицію?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/trading/positions/${positionId}/close`, {
        method: 'POST'
      });
      const data = await res.json();
      
      if (data.ok) {
        toast.success('Позицію закрито');
        fetchPositions();
      } else {
        toast.error(`Помилка: ${data.error || 'Не вдалося закрити'}`);
      }
    } catch (error) {
      console.error('Close position error:', error);
      toast.error('Помилка закриття позиції');
    }
  };

  const handleSymbolClick = (symbol) => {
    setSelectedSymbol(symbol);
    if (onSymbolSelect) {
      onSymbolSelect(symbol);
    }
  };

  // Group by symbol
  const groupedPositions = positions.reduce((acc, pos) => {
    const symbol = pos.symbol;
    if (!acc[symbol]) acc[symbol] = [];
    acc[symbol].push(pos);
    return acc;
  }, {});

  const symbols = Object.keys(groupedPositions).sort();

  return (
    <div 
      className="bg-white rounded-xl p-4 border border-[#e6eaf2]" 
      style={{ boxShadow: '2px 2px 8px rgba(0,5,48,0.06)' }}
      data-testid="positions-manager"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Управління позиціями
        </h3>
        <div className="flex items-center gap-2">
          <div className="text-xs text-gray-500">
            {positions.length} {positions.length === 1 ? 'позиція' : 'позицій'}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchPositions}
            className="h-7 w-7 p-0"
          >
            <RefreshCw className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {/* Symbol Tabs */}
      {symbols.length > 0 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          {symbols.map(symbol => {
            const count = groupedPositions[symbol].length;
            const totalPnl = groupedPositions[symbol].reduce(
              (sum, p) => sum + (p.unrealized_pnl || 0), 
              0
            );
            const isProfitable = totalPnl > 0;
            
            return (
              <button
                key={symbol}
                onClick={() => handleSymbolClick(symbol)}
                className={`
                  px-3 py-2 rounded-lg text-xs font-medium transition-all
                  ${selectedSymbol === symbol
                    ? 'bg-[#04A584] text-white shadow-sm'
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                  }
                `}
              >
                <div className="flex items-center gap-2">
                  <span>{symbol.replace('USDT', '')}</span>
                  <span className={`text-[10px] ${
                    selectedSymbol === symbol ? 'text-white opacity-80' : 'text-gray-500'
                  }`}>
                    {count}
                  </span>
                  <span className={`text-[10px] font-bold ${
                    selectedSymbol === symbol 
                      ? 'text-white' 
                      : isProfitable ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {isProfitable ? '+' : ''}{totalPnl.toFixed(0)}$
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Positions List */}
      <div className="space-y-2">
        {positions.length === 0 && (
          <div className="text-center py-8 text-sm text-gray-500">
            Немає відкритих позицій
          </div>
        )}
        
        {positions
          .filter(p => p.symbol === selectedSymbol)
          .map((pos, idx) => {
            const isLong = pos.side?.toUpperCase() === 'LONG';
            const unrealizedPnl = pos.unrealized_pnl || 0;
            const isProfitable = unrealizedPnl > 0;
            
            return (
              <div 
                key={pos.position_id || idx}
                className="border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`px-2 py-1 rounded text-xs font-bold ${
                      isLong 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {isLong ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-900">
                        {pos.symbol}
                      </div>
                      <div className="text-xs text-gray-500">
                        {pos.size} × ${pos.entry_price?.toFixed(2)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <div className={`text-sm font-bold ${
                      isProfitable ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {isProfitable ? '+' : ''}${unrealizedPnl.toFixed(2)}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleClosePosition(pos.position_id)}
                      className="h-7 w-7 p-0 text-red-500 hover:text-red-600 hover:bg-red-50"
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {pos.stop_loss && (
                    <div className="flex items-center gap-1 text-gray-600">
                      <ShieldAlert className="w-3 h-3 text-red-500" />
                      <span>SL:</span>
                      <span className="font-medium">${pos.stop_loss.toFixed(2)}</span>
                    </div>
                  )}
                  
                  {pos.take_profit && (
                    <div className="flex items-center gap-1 text-gray-600">
                      <Target className="w-3 h-3 text-green-500" />
                      <span>TP:</span>
                      <span className="font-medium">${pos.take_profit.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
};

export default PositionsManager;
