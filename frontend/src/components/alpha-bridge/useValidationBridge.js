/**
 * useValidationBridge hook - React hook for AF3 data
 */
import { useState, useEffect, useCallback } from 'react';
import { validationBridgeApi } from './validationBridgeApi';

export function useValidationBridge(autoRefresh = true) {
  const [truths, setTruths] = useState([]);
  const [actions, setActions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const evaluation = await validationBridgeApi.getFullEvaluation();
      
      setTruths(evaluation.truths || []);
      setActions(evaluation.actions || []);
      setSummary(evaluation.summary || null);
    } catch (err) {
      console.error('Failed to load validation bridge data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const submitActions = useCallback(async (urgentOnly = false) => {
    try {
      const result = await validationBridgeApi.submitActions(urgentOnly);
      await load(); // Reload after submit
      return result;
    } catch (err) {
      console.error('Failed to submit actions:', err);
      throw err;
    }
  }, [load]);

  useEffect(() => {
    load();

    if (autoRefresh) {
      const interval = setInterval(load, 15000); // Refresh every 15s
      return () => clearInterval(interval);
    }
  }, [load, autoRefresh]);

  return {
    truths,
    actions,
    summary,
    loading,
    error,
    reload: load,
    submitActions,
  };
}

export default useValidationBridge;
