/**
 * main.ts - Main Application Integration
 * 
 * Integrates all components and manages the overall application state.
 * Handles communication between frontend components and backend services.
 */

import { Canvas, CanvasNode, CanvasConnection } from './Canvas/Canvas';
import { ComponentsPanel } from './Canvas/Components-Panel';
import { NodeDesign } from './Canvas/Node-Design';
import { TestingPanel } from './Canvas/Testing-Panel';

interface AppConfig {
  backendUrl: string;
  websocketUrl: string;
  canvasContainerId: string;
  enableAutoSave: boolean;
  maxExecutionHistory: number;
}

class WeevApp {
  private canvas!: Canvas;
  private componentsPanel!: ComponentsPanel;
  private nodeDesign!: NodeDesign;
  private testingPanel!: TestingPanel;
  private websocket: WebSocket | null = null;
  private config: AppConfig;
  private currentWorkflowId: string | null = null;
  private isConnected = false;

  constructor(config: Partial<AppConfig> = {}) {
    this.config = {
      backendUrl: 'http://localhost:8000',
      websocketUrl: 'ws://localhost:8000/ws',
      canvasContainerId: 'canvas-container',
      enableAutoSave: true,
      maxExecutionHistory: 50,
      ...config
    };
    this.initializeApp();
  }

  private async initializeApp(): Promise<void> {
    try {
      // Initialize components
      this.canvas = new Canvas(this.config.canvasContainerId);
      this.componentsPanel = new ComponentsPanel('components-panel');
      this.nodeDesign = new NodeDesign();
      this.testingPanel = new TestingPanel('testing-panel');

      // Setup WebSocket
      await this.initializeWebSocket();

      // Setup event listeners
      this.setupGlobalEventListeners();

      // Load saved workflow
      await this.loadSavedWorkflow();

      console.log('Weev App initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Weev App:', error);
      this.showNotification('Failed to initialize app. Please refresh.', 'error');
    }
  }

  private async initializeWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.websocket = new WebSocket(this.config.websocketUrl);
        
        this.websocket.onopen = () => {
          console.log('WebSocket connected');
          this.isConnected = true;
          this.showNotification('Connected to backend', 'success');
          resolve();
        };

        this.websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.websocket.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.isConnected = false;
          this.showNotification('Disconnected from backend', 'warning');
          
          // Auto-reconnect after 3 seconds
          setTimeout(() => {
            if (!this.isConnected) {
              this.initializeWebSocket();
            }
          }, 3000);
        };

        this.websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.showNotification('Connection error', 'error');
          reject(error);
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        reject(error);
      }
    });
  }

  private handleWebSocketMessage(message: any): void {
    switch (message.type) {
      case 'execution_started':
        this.showNotification('Workflow execution started', 'info');
        break;
      case 'execution_update':
        this.showNotification(message.content, 'info');
        break;
      case 'execution_complete':
        this.showNotification('Workflow execution completed', 'success');
        break;
      case 'execution_error':
        this.showNotification(`Execution error: ${message.error}`, 'error');
        break;
      case 'node_result':
        this.handleNodeResult(message);
        break;
      case 'pong':
        // Keep-alive response
        break;
      default:
        console.log('Unknown WebSocket message:', message);
    }
  }

  private handleNodeResult(message: any): void {
    const node = this.canvas.getNode(message.node_id);
    if (node) {
      node.data = message.result;
      node.metadata = message.metadata;
      this.canvas.updateNode(node);
    }
  }

  public async executeWorkflow(): Promise<void> {
    if (!this.isConnected) {
      this.showNotification('Not connected to backend', 'error');
      return;
    }

    try {
      const workflow = this.canvas.serialize();
      const workflowId = this.currentWorkflowId || `workflow_${Date.now()}`;
      
      const message = {
        type: 'execute_workflow',
        data: {
          workflow_id: workflowId,
          nodes: workflow.nodes,
          connections: workflow.connections
        }
      };

      this.websocket!.send(JSON.stringify(message));
      this.showNotification('Executing workflow...', 'info');
    } catch (error) {
      console.error('Error executing workflow:', error);
      this.showNotification('Failed to execute workflow', 'error');
    }
  }

  private setupGlobalEventListeners(): void {
    // Fix event listener casting
    window.addEventListener('openNodeConfig', ((event: CustomEvent) => {
      this.componentsPanel.openNodeConfiguration(event.detail);
    }) as EventListener);
    
    window.addEventListener('duplicateNode', ((event: CustomEvent) => {
      this.duplicateNode(event.detail);
    }) as EventListener);
    
    window.addEventListener('deleteNode', ((event: CustomEvent) => {
      this.deleteNode(event.detail);
    }) as EventListener);

    document.addEventListener('keydown', (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey) {
        switch (event.key) {
          case 's':
            event.preventDefault();
            this.saveWorkflow();
            break;
          case 'Enter':
            event.preventDefault();
            this.executeWorkflow();
            break;
          case 'z':
            if (event.shiftKey) {
              this.redo();
            } else {
              this.undo();
            }
            break;
          case 'Delete':
            this.deleteSelectedNodes();
            break;
        }
      }
    });

    window.addEventListener('beforeunload', (event: BeforeUnloadEvent) => {
      if (this.hasUnsavedChanges()) {
        event.preventDefault();
        return 'You have unsaved changes. Are you sure you want to leave?';
      }
    });
  }

  private deleteSelectedNodes(): void {
    const selectedNodes = this.canvas.getSelectedNodes();
    selectedNodes.forEach((node: any) => this.deleteNode(node.id));
  }

  private getSelectedNodes(): any[] {
    return this.canvas.getNodes().filter((node: any) => node.selected);
  }

  private hasUnsavedChanges(): boolean {
    return true; // Simplified for now
  }

  private async saveWorkflow(): Promise<void> {
    try {
      const workflow = this.canvas.serialize();
      const workflowId = this.currentWorkflowId || `workflow_${Date.now()}`;
      
      localStorage.setItem(`workflow_${workflowId}`, JSON.stringify(workflow));
      this.currentWorkflowId = workflowId;
      
      this.showNotification('Workflow saved', 'success');
    } catch (error) {
      console.error('Error saving workflow:', error);
      this.showNotification('Failed to save workflow', 'error');
    }
  }

  private async loadSavedWorkflow(): Promise<void> {
    try {
      const savedWorkflows = Object.keys(localStorage).filter(key => key.startsWith('workflow_'));
      if (savedWorkflows.length > 0) {
        const latestWorkflow = savedWorkflows[savedWorkflows.length - 1];
        const workflowData = JSON.parse(localStorage.getItem(latestWorkflow)!);
        
        this.canvas.deserialize(workflowData);
        this.currentWorkflowId = latestWorkflow.replace('workflow_', '');
        
        this.showNotification('Workflow loaded', 'success');
      }
    } catch (error) {
      console.error('Error loading workflow:', error);
    }
  }

  private showNotification(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  // Placeholder methods for undo/redo
  private undo(): void {
    console.log('Undo not implemented yet');
  }

  private redo(): void {
    console.log('Redo not implemented yet');
  }

  private duplicateNode(nodeId: string): void {
    console.log('Duplicate node not implemented yet:', nodeId);
  }

  private deleteNode(nodeId: string): void {
    this.canvas.deleteNode(nodeId);
    this.showNotification('Node deleted', 'info');
  }
}

// CSS animations for notifications
const notificationStyles = `
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  @keyframes slideOutRight {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100%);
      opacity: 0;
    }
  }
`;

// Inject notification styles
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Create the main canvas container if it doesn't exist
  if (!document.getElementById('canvas-container')) {
    const canvasContainer = document.createElement('div');
    canvasContainer.id = 'canvas-container';
    canvasContainer.style.cssText = `
      position: absolute;
      top: 0;
      left: 320px; /* Components panel width */
      right: 400px; /* Testing panel width */
      bottom: 0;
      background: #f8fafc;
    `;
    document.body.appendChild(canvasContainer);
  }
  
  // Initialize the main application
  const app = new WeevApp({
    backendUrl: 'http://localhost:8000',
    websocketUrl: 'ws://localhost:8000/ws',
    enableAutoSave: true
  });
  
  // Make app globally available for debugging
  (window as any).weevApp = app;
});

export { WeevApp };
