import { useEffect } from 'react';
import { API_BASE_URL, getAccessToken } from '../config/auth.js';

function socketUrl() {
  const token = getAccessToken();
  if (!token) return null;
  const query = `token=${encodeURIComponent(token)}`;
  if (/^https?:\/\//i.test(API_BASE_URL)) {
    const base = API_BASE_URL.replace(/^http/i, 'ws').replace(/\/$/, '');
    return `${base}/notifications/ws?${query}`;
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const path = `${API_BASE_URL.replace(/\/$/, '')}/notifications/ws`;
  return `${proto}//${window.location.host}${path}?${query}`;
}

/** Keeps a notification socket open and tells the UI to reload when one arrives. */
export default function useNotificationSocket(active = true) {
  useEffect(() => {
    if (!active) return undefined;

    let socket = null;
    let stopped = false;
    let retryTimer = null;
    let pingTimer = null;
    let attempt = 0;

    const clearTimers = () => {
      if (retryTimer) clearTimeout(retryTimer);
      if (pingTimer) clearInterval(pingTimer);
      retryTimer = null;
      pingTimer = null;
    };

    const connect = () => {
      if (stopped) return;
      const url = socketUrl();
      if (!url) return;
      socket = new WebSocket(url);
      socket.onopen = () => {
        attempt = 0;
        pingTimer = setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) socket.send('ping');
        }, 25000);
      };
      socket.onmessage = () => {
        window.dispatchEvent(new Event('notifications-changed'));
      };
      socket.onclose = () => {
        clearTimers();
        socket = null;
        if (stopped) return;
        attempt += 1;
        const delay = Math.min(30000, 1000 * attempt);
        retryTimer = setTimeout(connect, delay);
      };
      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();
    return () => {
      stopped = true;
      clearTimers();
      socket?.close();
    };
  }, [active]);
}
