/**
 * useValidation Hook - React hook for validation data
 */
import { useState, useEffect, useCallback } from 'react';
import { validationApi } from './validationApi';

export function useValidation(symbol = null, autoRefresh = true) {
  const [metrics, setMetrics] = useState(null);
  const [shadowTrades, setShadowTrades] = useState([]);
  const [validationResults, setValidationResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [metricsData, shadowsData, resultsData, statsData] = await Promise.all([
        validationApi.getMetrics(symbol),
        validationApi.getRecentShadowTrades(symbol, 20),
        validationApi.getRecentResults(symbol, 20),
        validationApi.getStats(),
      ]);

      setMetrics(metricsData);
      setShadowTrades(shadowsData);
      setValidationResults(resultsData);
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load validation data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    load();

    if (autoRefresh) {
      const interval = setInterval(load, 10000); // Refresh every 10s
      return () => clearInterval(interval);
    }
  }, [load, autoRefresh]);

  return {
    metrics,
    shadowTrades,
    validationResults,
    stats,
    loading,
    error,
    reload: load,
  };
}

export function useValidationMetrics(symbol = null) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await validationApi.getMetrics(symbol);
      setMetrics(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [load]);

  return { metrics, loading, error, reload: load };
}

export default useValidation;
