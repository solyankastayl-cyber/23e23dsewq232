/**
 * Sprint 7.8: Adaptation Recommendations Hook
 * 
 * Fetches system-generated recommendations.
 * DOES NOT auto-apply - only displays for operator approval.
 */

import { useState, useEffect } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

export function useAdaptationRecommendations() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRecommendations = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/adaptation/recommendations`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      console.error('[useAdaptationRecommendations] Failed:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();

    // Refresh every 30 seconds (less frequent - operator-triggered mostly)
    const interval = setInterval(fetchRecommendations, 30000);

    return () => clearInterval(interval);
  }, []);

  return { 
    data, 
    loading, 
    error,
    refresh: fetchRecommendations 
  };
}
