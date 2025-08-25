// Simple WebSocket wrapper for workflow execution
// Uses Vite proxy to route to backend (configure /ws proxy in vite.config)

class WebsocketService {
  constructor() {
    this.ws = null;
    this.handlers = new Set();
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${location.host}/ws`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('[WS] connected');
    };

    this.ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        this.handlers.forEach((h) => h(data));
      } catch (e) {
        console.error('[WS] message parse error', e);
      }
    };

    this.ws.onclose = () => {
      console.log('[WS] disconnected');
    };

    this.ws.onerror = (err) => {
      console.error('[WS] error', err);
    };
  }

  onMessage(handler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  executeWorkflow(workflow) {
    const payload = {
      type: 'execute_workflow',
      data: workflow
    };
    this._send(payload);
  }

  _send(obj) {
    const data = JSON.stringify(obj);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      console.warn('[WS] not open, buffering send until open');
      const interval = setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          clearInterval(interval);
          this.ws.send(data);
        }
      }, 200);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const websocketService = new WebsocketService();
