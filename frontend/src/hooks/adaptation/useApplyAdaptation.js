/**
 * Sprint 7.8: Apply/Reject Adaptation Hook
 * 
 * Handles operator approval/rejection of recommendations.
 * CRITICAL: Only operator can apply. System cannot auto-apply.
 */

import { useState } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

export function useApplyAdaptation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const apply = async (changeId) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/adaptation/changes/${changeId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ applied_by: 'operator' })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to apply');
      }
      
      const result = await response.json();
      return { success: true, data: result };
    } catch (err) {
      console.error('[useApplyAdaptation] Apply failed:', err);
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const reject = async (changeId) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/adaptation/changes/${changeId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected_by: 'operator' })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to reject');
      }
      
      const result = await response.json();
      return { success: true, data: result };
    } catch (err) {
      console.error('[useApplyAdaptation] Reject failed:', err);
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  return { apply, reject, loading, error };
}
