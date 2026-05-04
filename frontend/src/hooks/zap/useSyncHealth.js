import { useEffect, useState } from "react";

const backendUrl = process.env.REACT_APP_BACKEND_URL;

export function useSyncHealth() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    const fetchData = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/exchange/health`);
        if (!res.ok) throw new Error(`Sync health request failed: ${res.status}`);
        const json = await res.json();
        if (alive) {
          setData(json);
          setError(null);
        }
      } catch (e) {
        if (alive) setError(e.message);
      }
    };

    fetchData();
    const id = setInterval(fetchData, 5000);

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return { data, error };
}
