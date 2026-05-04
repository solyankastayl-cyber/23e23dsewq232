/**
 * Trading Cases API Hook
 * 
 * Fetches active trading cases from backend API.
 */

import { useState, useEffect } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export function useTradingCases() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCases = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/trading/cases/active`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch cases: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Transform backend format to frontend format
      const transformedCases = data.map(backendCase => ({
        // Frontend fields (legacy)
        id: backendCase.case_id,
        symbol: backendCase.symbol,
        direction: backendCase.side, // "LONG" or "SHORT"
        status: backendCase.status, // "ACTIVE" or "CLOSED"
        
        // Trading data
        strategy: backendCase.strategy,
        timeframe: backendCase.trading_tf,
        entry_price: backendCase.entry_price,
        current_price: backendCase.current_price,
        qty: backendCase.qty,
        
        // PnL
        pnl: backendCase.unrealized_pnl,
        pnl_pct: backendCase.unrealized_pnl_pct,
        realized_pnl: backendCase.realized_pnl,
        
        // Trade count
        trade_count: backendCase.order_ids?.length || 0,
        
        // Stop/Target
        stop_price: backendCase.stop_price,
        target_price: backendCase.target_price,
        
        // Thesis
        thesis: backendCase.thesis,
        thesis_history: backendCase.thesis_history,
        
        // Timestamps
        opened_at: backendCase.opened_at,
        closed_at: backendCase.closed_at,
        
        // Full backend data (for reference)
        _backend: backendCase
      }));
      
      setCases(transformedCases);
      setError(null);
    } catch (err) {
      console.error('[useTradingCases] Error:', err);
      setError(err.message);
      setCases([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
    
    // Refresh every 5 seconds
    const interval = setInterval(fetchCases, 5000);
    
    return () => clearInterval(interval);
  }, []);

  return {
    cases,
    loading,
    error,
    refetch: fetchCases
  };
}
