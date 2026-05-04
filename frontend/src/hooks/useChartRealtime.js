/**
 * useChartRealtime — Real-time Chart Updates via WebSocket
 * =========================================================
 * 
 * Provides real-time candle updates for the trading chart.
 * Subscribes to market data channel and updates candles live.
 * 
 * Features:
 * - WebSocket subscription for candle updates
 * - Auto-reconnect on disconnect
 * - Fallback to polling if WS unavailable
 * - Price change events
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const getWsUrl = () => {
  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
  if (backendUrl) {
    return backendUrl.replace(/^http/, 'ws') + '/api/ws/market';
  }
  return (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + 
    window.location.host + '/api/ws/market';
};

const RECONNECT_DELAY = 5000;
const MAX_RECONNECT_ATTEMPTS = 3;
const POLL_INTERVAL = 15000; // 15 seconds fallback polling

export function useChartRealtime({
  symbol = 'BTCUSDT',
  timeframe = '4H',
  enabled = true,
  onCandleUpdate,
  onPriceChange,
}) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastPrice, setLastPrice] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [usingFallback, setUsingFallback] = useState(false);
  
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const pollIntervalRef = useRef(null);
  const onCandleUpdateRef = useRef(onCandleUpdate);
  const onPriceChangeRef = useRef(onPriceChange);

  // Keep callback refs updated
  useEffect(() => {
    onCandleUpdateRef.current = onCandleUpdate;
    onPriceChangeRef.current = onPriceChange;
  }, [onCandleUpdate, onPriceChange]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = getWsUrl();
    console.log('[ChartWS] Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[ChartWS] Connected');
        setIsConnected(true);
        setUsingFallback(false);
        reconnectAttempts.current = 0;

        // Subscribe to symbol/timeframe
        ws.send(JSON.stringify({
          type: 'subscribe',
          channel: 'candles',
          symbol: symbol,
          timeframe: timeframe,
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'candle') {
            // New or updated candle
            const candle = {
              time: data.time,
              open: data.open,
              high: data.high,
              low: data.low,
              close: data.close,
              volume: data.volume,
            };
            
            setLastPrice(data.close);
            setLastUpdate(Date.now());
            
            if (onCandleUpdateRef.current) {
              onCandleUpdateRef.current(candle);
            }
          } else if (data.type === 'price') {
            // Price tick
            setLastPrice(data.price);
            setLastUpdate(Date.now());
            
            if (onPriceChangeRef.current) {
              onPriceChangeRef.current(data.price, data.change);
            }
          }
        } catch (err) {
          console.error('[ChartWS] Parse error:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('[ChartWS] Error:', err);
      };

      ws.onclose = () => {
        console.log('[ChartWS] Disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Try reconnect
        if (enabled && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++;
          console.log(`[ChartWS] Reconnecting in ${RECONNECT_DELAY}ms (attempt ${reconnectAttempts.current})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, RECONNECT_DELAY);
        } else {
          // Fall back to polling
          console.log('[ChartWS] Max reconnect attempts reached, using fallback polling');
          setUsingFallback(true);
        }
      };
    } catch (err) {
      console.error('[ChartWS] Connection error:', err);
      setUsingFallback(true);
    }
  }, [enabled, symbol, timeframe]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);

  // Change subscription (symbol/timeframe change)
  const updateSubscription = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        channel: 'candles',
        symbol: symbol,
        timeframe: timeframe,
      }));
    }
  }, [symbol, timeframe]);

  // Fallback polling
  const pollPrice = useCallback(async () => {
    if (!usingFallback || !enabled) return;
    
    try {
      const base = process.env.REACT_APP_BACKEND_URL || '';
      const res = await fetch(`${base}/api/data/coinbase/ticker?symbol=${symbol}`);
      if (res.ok) {
        const data = await res.json();
        if (data.price) {
          const price = parseFloat(data.price);
          const prevPrice = lastPrice;
          const change = prevPrice ? ((price - prevPrice) / prevPrice) * 100 : 0;
          
          setLastPrice(price);
          setLastUpdate(Date.now());
          
          if (onPriceChangeRef.current) {
            onPriceChangeRef.current(price, change);
          }
        }
      }
    } catch (err) {
      console.error('[ChartWS] Poll error:', err);
    }
  }, [usingFallback, enabled, symbol, lastPrice]);

  // Start fallback polling
  useEffect(() => {
    if (usingFallback && enabled) {
      pollPrice(); // Initial poll
      pollIntervalRef.current = setInterval(pollPrice, POLL_INTERVAL);
    } else if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [usingFallback, enabled, pollPrice]);

  // Connect on mount
  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled]);

  // Update subscription on symbol/timeframe change
  useEffect(() => {
    updateSubscription();
  }, [symbol, timeframe, updateSubscription]);

  return {
    isConnected,
    lastPrice,
    lastUpdate,
    usingFallback,
    reconnect: connect,
    disconnect,
  };
}

export default useChartRealtime;
