import { useEffect, useState } from "react";

const backendUrl = process.env.REACT_APP_BACKEND_URL;

export function useOrders() {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    const fetchData = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/exchange/orders`);
        if (!res.ok) throw new Error(`Orders request failed: ${res.status}`);
        const json = await res.json();
        if (alive) {
          // Backend returns {ok: true, orders: [...]}
          setData(json.ok ? (json.orders || []) : []);
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
