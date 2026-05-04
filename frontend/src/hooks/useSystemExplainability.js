import { useEffect, useState } from "react";

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function useSystemExplainability() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const res = await fetch(`${API_URL}/api/trading/system/explainability`);
        const json = await res.json();
        if (active && json.ok) {
          setData(json.data);
        }
      } catch (err) {
        console.error("Explainability fetch error:", err);
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    const interval = setInterval(load, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return { data, loading };
}
