// /app/frontend/src/hooks/dynamic_risk/useDynamicRiskStats.js
import { useEffect, useState } from "react";

export default function useDynamicRiskStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await fetch("/api/dynamic-risk/stats");
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      
      const data = await res.json();
      setStats(data || null);
      setError(null);
    } catch (e) {
      console.error("[R1 UI] stats fetch failed:", e);
      setError(e.message);
      // Keep showing stale stats on error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  return { stats, loading, error, refresh: fetchStats };
}
