/**
 * useWsChannel Hook (Production Version)
 * Sprint WS-1: Event streaming with dedupe
 */

import { useEffect, useState } from "react";
import wsClient from "./wsClient";

export default function useWsChannel(channel) {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const unsubscribeStatus = wsClient.onStatus(setIsConnected);

    const handler = (msg) => {
      setMessages((prev) => {
        // ✅ Dedupe по ts + event
        const exists = prev.find(
          (e) => e.ts === msg.ts && e.event === msg.event
        );
        if (exists) return prev;

        return [msg, ...prev].slice(0, 200);
      });
    };

    wsClient.subscribe(channel, handler);

    return () => {
      wsClient.unsubscribe(channel, handler);
      unsubscribeStatus();
    };
  }, [channel]);

  return { messages, isConnected };
}
