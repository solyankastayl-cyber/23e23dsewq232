import { useEffect, useState } from "react";
// Phase A.3 Step 4.3A — pending decisions list routed through canonical
// taRuntime.decisions.listPending() (-> /api/ta/runtime/decisions/pending).
// Approve/reject/note remain on legacy until Step 4.3B. DO NOT migrate
// them here. Cockpit module stays on legacy until Phase A.5.
import { taRuntime } from "../../modules/ta/services";

export function usePendingDecisions() {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  // Manual refetch (used by parent components after approve/reject).
  // taRuntime.decisions.listPending() returns an already-parsed JSON
  // body identical to the legacy fetch().json() shape: { ok, decisions }.
  // Non-2xx responses are surfaced as thrown Errors with .status / .data.
  const refetch = async () => {
    try {
      const json = await taRuntime.decisions.listPending();
      setData(json && json.ok ? (json.decisions || []) : []);
      setError(null);
      setLoading(false);
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    let alive = true;

    const fetchData = async () => {
      try {
        const json = await taRuntime.decisions.listPending();
        if (alive) {
          setData(json && json.ok ? (json.decisions || []) : []);
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
    const id = setInterval(fetchData, 2000); // Poll every 2 seconds

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return { data, error, loading, refetch };
}
