import type { WorkflowExecution, ExecutionUpdate } from './types.js';

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectInterval: number = 3000;
  private messageHandlers: Array<(data: ExecutionUpdate) => void> = [];

  connect() {
    this.ws = new WebSocket('ws://localhost:8000/ws/canvas');
    
    this.ws.onopen = () => {
      console.log('🔗 Connected to Weev backend');
    };

    this.ws.onmessage = (event) => {
      const data: ExecutionUpdate = JSON.parse(event.data);
      console.log('📨 Received:', data);
      this.messageHandlers.forEach(handler => handler(data));
    };

    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('🔌 WebSocket connection closed, attempting reconnect...');
      setTimeout(() => this.connect(), this.reconnectInterval);
    };
  }

  onMessage(handler: (data: ExecutionUpdate) => void) {
    this.messageHandlers.push(handler);
  }

  executeWorkflow(workflow: WorkflowExecution) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('🚀 Executing workflow:', workflow.workflow_id);
      this.ws.send(JSON.stringify({
        type: 'execute_workflow',
        data: workflow
      }));
    } else {
      console.error('❌ WebSocket not connected');
    }
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
    this.messageHandlers = [];
  }
}

export const websocketService = new WebSocketService();
