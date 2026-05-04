import { useEffect, useState, useCallback } from "react";

const API = "/api/auto-safety";

export function useAutoSafetyConfig() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API}/config`);
      const data = await res.json();
      setConfig(data.config);
    } catch (e) {
      console.error("AutoSafety config error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
    const i = setInterval(fetchConfig, 5000);
    return () => clearInterval(i);
  }, [fetchConfig]);

  return { config, loading, refetch: fetchConfig };
}

export function useAutoSafetyState() {
  const [state, setState] = useState(null);

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${API}/state`);
      const data = await res.json();
      setState(data.state);
    } catch (e) {
      console.error("AutoSafety state error:", e);
    }
  }, []);

  useEffect(() => {
    fetchState();
    const i = setInterval(fetchState, 3000);
    return () => clearInterval(i);
  }, [fetchState]);

  return { state, refetch: fetchState };
}

export function useAutoSafetyActions(refetchAll) {
  const [updating, setUpdating] = useState(false);

  const updateConfig = async (patch) => {
    try {
      setUpdating(true);
      await fetch(`${API}/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      refetchAll?.();
    } catch (e) {
      console.error("AutoSafety update error:", e);
    } finally {
      setUpdating(false);
    }
  };

  return { updateConfig, updating };
}
