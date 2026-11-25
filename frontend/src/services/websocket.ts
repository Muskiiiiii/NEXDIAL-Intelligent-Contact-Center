import { useState, useEffect, useCallback } from 'react';

type MessageHandler = (data: any) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<MessageHandler>> = new Map();
  private reconnectTimeout: any = null;
  private url: string = '';
  public isConnected: boolean = false;

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    this.url = `${protocol}//${host}/ws/live`;
  }

  public connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.emit('connection_change', { connected: true });
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.emit('connection_change', { connected: false });
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.warn('WebSocket encountered error:', err);
        if (this.ws) {
          this.ws.close();
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type) {
            this.emit(payload.type, payload.data);
            this.emit('*', payload);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
    } catch (e) {
      console.error('Failed to initialize WebSocket:', e);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, 3000);
  }

  public on(type: string, handler: MessageHandler) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(handler);
    return () => this.off(type, handler);
  }

  public off(type: string, handler: MessageHandler) {
    const handlers = this.listeners.get(type);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.listeners.delete(type);
      }
    }
  }

  private emit(type: string, data: any) {
    const handlers = this.listeners.get(type);
    if (handlers) {
      handlers.forEach((h) => {
        try {
          h(data);
        } catch (err) {
          console.error(`Error in WebSocket listener for ${type}:`, err);
        }
      });
    }
  }
}

export const wsClient = new WebSocketClient();

export function useWebSocketEvent(eventType: string, callback: MessageHandler) {
  useEffect(() => {
    wsClient.connect();
    const unsubscribe = wsClient.on(eventType, callback);
    return () => {
      unsubscribe();
    };
  }, [eventType, callback]);
}

export function useWebSocketStatus() {
  const [connected, setConnected] = useState<boolean>(wsClient.isConnected);

  useEffect(() => {
    wsClient.connect();
    const unsubscribe = wsClient.on('connection_change', (data: { connected: boolean }) => {
      setConnected(data.connected);
    });
    return () => {
      unsubscribe();
    };
  }, []);

  return connected;
}
