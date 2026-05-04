import { useEffect, useState } from "react";
// Phase A.3 Step 4.1 — read-only runtime migrated to canonical /api/ta/runtime/state.
import { taRuntime } from "../../modules/ta/services";

export function useRuntimeState() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;

    const fetchData = async () => {
      try {
        const json = await taRuntime.getState();
        if (alive) {
          setData(json && json.ok ? json : null);
          setError(null);
          setLoading(false);
        }
      } catch (e) {
        if (alive) {
          setError(e.message);
          setLoading(false);
        }
      }
    };

    fetchData();
    const id = setInterval(fetchData, 3000); // Poll every 3 seconds

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return { data, error, loading };
}
