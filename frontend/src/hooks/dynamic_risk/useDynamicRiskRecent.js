// /app/frontend/src/hooks/dynamic_risk/useDynamicRiskRecent.js
import { useEffect, useState } from "react";

// Formatters for clean display
export const fmtMoney = (val) => {
  if (val == null || isNaN(val)) return "-";
  return `$${Number(val).toFixed(2)}`;
};

export const fmtQty = (val) => {
  if (val == null || isNaN(val)) return "-";
  return Number(val).toFixed(6);
};

export const fmtMultiplier = (val) => {
  if (val == null || isNaN(val)) return "-";
  return `${Number(val).toFixed(2)}x`;
};

export const fmtConfidence = (val) => {
  if (val == null || isNaN(val)) return "-";
  return Number(val).toFixed(2);
};

export const fmtTime = (ts) => {
  if (!ts) return "-";
  try {
    return new Date(ts).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  } catch {
    return "-";
  }
};

export default function useDynamicRiskRecent() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchItems = async () => {
    try {
      const res = await fetch("/api/dynamic-risk/recent");
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      
      const data = await res.json();
      setItems(Array.isArray(data) ? data : []);
      setError(null);
    } catch (e) {
      console.error("[R1 UI] recent fetch failed:", e);
      setError(e.message);
      // Don't clear items on error - keep showing stale data
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
    const interval = setInterval(fetchItems, 5000);
    return () => clearInterval(interval);
  }, []);

  return { items, loading, error, refresh: fetchItems };
}
