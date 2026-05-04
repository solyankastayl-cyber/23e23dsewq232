/**
 * useWsSnapshot Hook
 * Sprint WS-2/WS-3: State snapshot streaming with race condition protection
 */

import { useEffect, useState } from "react";
import wsClient from "./wsClient";

export default function useWsSnapshot(channel, initialValue = null) {
  const [data, setData] = useState(initialValue);
  const [lastWsData, setLastWsData] = useState(null); // ✅ Race condition fix
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const unsubscribeStatus = wsClient.onStatus(setIsConnected);

    const handler = (msg) => {
      if (msg.type === "snapshot") {
        setData(msg.data);
        setLastWsData(msg.data); // ✅ Persist last WS data
      }
    };

    wsClient.subscribe(channel, handler);

    return () => {
      wsClient.unsubscribe(channel, handler);
      unsubscribeStatus();
    };
  }, [channel]);

  // ✅ Return lastWsData (persisted) instead of data (can be null on reconnect)
  return { data: lastWsData ?? data, isConnected };
}
