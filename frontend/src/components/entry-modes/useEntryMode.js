/**
 * useEntryMode hook - React hook for AF4 data
 */
import { useState, useCallback, useEffect } from 'react';
import { entryModeApi } from './entryModeApi';

export function useEntryMode() {
  const [metrics, setMetrics] = useState([]);
  const [evaluations, setEvaluations] = useState([]);
  const [actions, setActions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch initial summary data on mount
  useEffect(() => {
    const fetchInitialSummary = async () => {
      try {
        const summaryData = await entryModeApi.getSummary();
        setSummary(summaryData);
      } catch (err) {
        console.error('Failed to fetch initial AF4 summary:', err);
        // Don't set error state for initial fetch failure
      }
    };

    fetchInitialSummary();
  }, []);

  const run = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await entryModeApi.run();
      
      setMetrics(result.metrics || []);
      setEvaluations(result.evaluations || []);
      setActions(result.actions || []);
      setSummary(result.summary || null);
      
      return result;
    } catch (err) {
      console.error('Failed to run entry mode adaptation:', err);
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const submit = useCallback(async (urgentOnly = false) => {
    try {
      setLoading(true);
      setError(null);

      const result = await entryModeApi.submit(urgentOnly);
      
      setMetrics(result.metrics || []);
      setEvaluations(result.evaluations || []);
      setActions(result.actions || []);
      setSummary(result.summary || null);
      
      return result;
    } catch (err) {
      console.error('Failed to submit entry mode actions:', err);
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    metrics,
    evaluations,
    actions,
    summary,
    loading,
    error,
    run,
    submit,
  };
}

export default useEntryMode;
