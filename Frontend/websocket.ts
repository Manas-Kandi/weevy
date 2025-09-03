import type { WorkflowExecution, ExecutionUpdate } from './types';
import { inputManager } from './InputManager';

export interface EnhancedExecutionUpdate extends ExecutionUpdate {
  // Enhanced properties from backend
  processing_mode?: string;
  total_nodes?: number;
  node_type?: string;
  success?: boolean;
  confidence?: number;
  selected_tools?: string[];
  reasoning?: string;
  tool_execution_results?: Array<{
    tool: string;
    status: string;
    result: any;
    execution_time: number;
    error?: string;
  }>;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectInterval: number = 3000;
  private maxReconnectAttempts: number = 5;
  private reconnectAttempts: number = 0;
  private isConnected: boolean = false;
  private isIntentionalDisconnect: boolean = false;
  private messageHandlers: Array<(data: EnhancedExecutionUpdate) => void> = [];
  private connectionHandlers: Array<(connected: boolean) => void> = [];
  private currentWorkflowId: string | null = null;

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${protocol}://${window.location.host}/ws`;
      
      this.ws = new WebSocket(url);
      
      this.ws.onopen = () => {
        console.log('🔗 Enhanced WebSocket connected to Weev backend');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.connectionHandlers.forEach(handler => handler(true));
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const data: EnhancedExecutionUpdate = JSON.parse(event.data);
          this._handleEnhancedMessage(data);
          this.messageHandlers.forEach(handler => handler(data));
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('❌ Enhanced WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = (event) => {
        console.log('🔌 Enhanced WebSocket connection closed:', event.code, event.reason);
        this.isConnected = false;
        this.connectionHandlers.forEach(handler => handler(false));
        
        if (!this.isIntentionalDisconnect) {
          this._attemptReconnect();
        }
      };
    });
  }

  private _handleEnhancedMessage(data: EnhancedExecutionUpdate) {
    // Enhanced message handling with more detailed logging
    const messageTypes = {
      'workflow_started': '🚀',
      'node_executed': '✅',
      'execution_error': '❌',
      'workflow_finished': '🎉',
      'execution_update': '📊',
      'node_result': '📋'
    };

    const emoji = messageTypes[data.type as keyof typeof messageTypes] || '📨';
    
    if (data.type === 'node_executed' && data.node_type) {
      console.log(`${emoji} Node executed:`, {
        nodeId: data.node_id,
        nodeType: data.node_type,
        success: data.success,
        confidence: data.confidence,
        selectedTools: data.selected_tools
      });
    } else if (data.type === 'workflow_started' && data.processing_mode) {
      console.log(`${emoji} Workflow started:`, {
        workflowId: data.workflow_id,
        processingMode: data.processing_mode,
        totalNodes: data.total_nodes
      });
    } else {
      console.log(`${emoji} Received:`, data.type, data);
    }
  }

  private _attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`🔄 Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectInterval}ms`);
      setTimeout(() => {
        this.connect().catch(() => this._attemptReconnect());
      }, this.reconnectInterval);
    } else {
      console.error('❌ Max reconnection attempts reached. Please refresh the page.');
    }
  }

  onMessage(handler: (data: EnhancedExecutionUpdate) => void) {
    this.messageHandlers.push(handler);
  }

  onConnectionChange(handler: (connected: boolean) => void) {
    this.connectionHandlers.push(handler);
  }

  executeWorkflow(workflow: WorkflowExecution, workflowId?: string) {
    if (!this.isConnected || this.ws?.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not connected');
      return false;
    }

    // Get processed workflow data using InputManager
    const processedWorkflow = workflowId ? 
      inputManager.translateToBackendFormat(workflowId, workflow.nodes as any, workflow.connections as any) :
      workflow;

    this.currentWorkflowId = processedWorkflow.workflow_id;

    console.log('🚀 Executing enhanced workflow:', {
      workflowId: processedWorkflow.workflow_id,
      nodeCount: processedWorkflow.nodes.length,
      connectionCount: processedWorkflow.connections.length
    });

    this.ws.send(JSON.stringify({
      type: 'execute_workflow',
      data: processedWorkflow
    }));

    return true;
  }

  sendMessage(type: string, data: any) {
    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
      return true;
    }
    return false;
  }

  ping() {
    return this.sendMessage('ping', { timestamp: Date.now() });
  }

  requestNodeStatus(nodeId: string) {
    return this.sendMessage('node_status', { nodeId });
  }

  getConnectionStatus() {
    return {
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      currentWorkflowId: this.currentWorkflowId
    };
  }

  disconnect() {
    this.isIntentionalDisconnect = true;
    this.ws?.close();
    this.ws = null;
    this.isConnected = false;
    this.messageHandlers = [];
    this.connectionHandlers = [];
    this.currentWorkflowId = null;
    console.log('🔌 WebSocket intentionally disconnected');
  }
}

export const websocketService = new WebSocketService();
