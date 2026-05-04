import { useEffect, useState } from "react";

const backendUrl = process.env.REACT_APP_BACKEND_URL;

export function useRejections() {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    const fetchData = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/strategy/rejections`);
        if (!res.ok) throw new Error(`Rejections request failed: ${res.status}`);
        const json = await res.json();
        if (alive) {
          // Backend returns {ok: true, rejections: [...]}
          setData(json.ok ? (json.rejections || []) : []);
          setError(null);
        }
      } catch (e) {
        if (alive) setError(e.message);
      }
    };

    fetchData();
    const id = setInterval(fetchData, 3000);

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return { data, error };
}
