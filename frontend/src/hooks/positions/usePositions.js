import { useEffect, useState } from "react";

export function usePositions() {
  const [positions, setPositions] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  const fetchPositions = async () => {
    try {
      const res = await fetch("/api/positions");
      const data = await res.json();
      setPositions(data || []);
      setIsConnected(true);  // Connected if fetch succeeds
    } catch (err) {
      console.error("[usePositions] Error:", err);
      setPositions([]);
      setIsConnected(false);  // Disconnected on error
    }
  };

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 2000);
    return () => clearInterval(interval);
  }, []);

  return { positions, refresh: fetchPositions, isConnected };
}
