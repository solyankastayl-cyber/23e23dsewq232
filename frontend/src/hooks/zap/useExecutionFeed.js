import { useEffect, useState } from "react";

const backendUrl = process.env.REACT_APP_BACKEND_URL;

export function useExecutionFeed() {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    const fetchData = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/execution/feed`);
        if (!res.ok) throw new Error(`Feed request failed: ${res.status}`);
        const json = await res.json();
        if (alive) {
          // Backend returns {ok: true, feed: [...]}
          setData(json.ok ? (json.feed || []) : []);
          setError(null);
        }
      } catch (e) {
        if (alive) setError(e.message);
      }
    };

    fetchData();
    const id = setInterval(fetchData, 2000);

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return { data, error };
}
