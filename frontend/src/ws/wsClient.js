/**
 * WebSocket Client (Production-Grade)
 * Sprint WS-1: Single singleton with proper listener management
 */

class WsClient {
  constructor() {
    this.ws = null;
    this.listeners = new Map(); // channel -> Set<cb>
    this.channels = new Set();
    this.statusListeners = new Set(); // ✅ Fix: не перезаписываемый

    this.connected = false;
    this.reconnectAttempts = 0;
    this.baseUrl = this.getWsUrl();
  }

  getWsUrl() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/ws`;
  }

  connect() {
    if (this.ws && (this.ws.readyState === 1 || this.ws.readyState === 0)) {
      return;
    }

    this.ws = new WebSocket(this.baseUrl);

    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectAttempts = 0;

      this.notifyStatus(true);

      if (this.channels.size > 0) {
        this.send({
          type: "subscribe",
          channels: Array.from(this.channels),
        });
      }
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.channel && this.listeners.has(msg.channel)) {
        for (const cb of this.listeners.get(msg.channel)) {
          cb(msg);
        }
      }
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.notifyStatus(false);
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.connected = false;
      this.notifyStatus(false);
      try {
        this.ws.close();
      } catch {}
    };
  }

  notifyStatus(state) {
    for (const cb of this.statusListeners) {
      cb(state);
    }
  }

  onStatus(cb) {
    this.statusListeners.add(cb);
    return () => this.statusListeners.delete(cb);
  }

  scheduleReconnect() {
    const delays = [1000, 2000, 5000, 10000, 20000];
    const delay = delays[Math.min(this.reconnectAttempts, delays.length - 1)];

    this.reconnectAttempts += 1;

    setTimeout(() => this.connect(), delay);
  }

  send(payload) {
    if (!this.ws || this.ws.readyState !== 1) return;
    this.ws.send(JSON.stringify(payload));
  }

  subscribe(channel, cb) {
    if (!this.listeners.has(channel)) {
      this.listeners.set(channel, new Set());
    }

    this.listeners.get(channel).add(cb);
    this.channels.add(channel);

    this.connect();

    if (this.connected) {
      this.send({ type: "subscribe", channels: [channel] });
    }
  }

  unsubscribe(channel, cb) {
    if (!this.listeners.has(channel)) return;

    this.listeners.get(channel).delete(cb);

    if (this.listeners.get(channel).size === 0) {
      this.listeners.delete(channel);
      this.channels.delete(channel);

      if (this.connected) {
        this.send({ type: "unsubscribe", channels: [channel] });
      }
    }
  }
}

const wsClient = new WsClient();
export default wsClient;
