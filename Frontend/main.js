/**
 * main.ts - Main Application Integration
 *
 * Integrates all components and manages the overall application state.
 * Handles communication between frontend components and backend services.
 */
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { Canvas } from './Canvas/Canvas';
import { ComponentsPanel } from './Canvas/Components-Panel';
import { NodeDesign } from './Canvas/Node-Design';
import { TestingPanel } from './Canvas/Testing-Panel';
class WeevApp {
    constructor(config = {}) {
        this.websocket = null;
        this.currentWorkflowId = null;
        this.isConnected = false;
        this.config = Object.assign({ backendUrl: 'http://localhost:8000', websocketUrl: 'ws://localhost:8000/ws', canvasContainerId: 'canvas-container', enableAutoSave: true, maxExecutionHistory: 50 }, config);
        this.initializeApp();
    }
    initializeApp() {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                // Initialize components
                this.canvas = new Canvas(this.config.canvasContainerId);
                this.componentsPanel = new ComponentsPanel('components-panel');
                this.nodeDesign = new NodeDesign();
                this.testingPanel = new TestingPanel('testing-panel');
                // Setup WebSocket
                yield this.initializeWebSocket();
                // Setup event listeners
                this.setupGlobalEventListeners();
                // Load saved workflow
                yield this.loadSavedWorkflow();
                console.log('Weev App initialized successfully');
            }
            catch (error) {
                console.error('Failed to initialize Weev App:', error);
                this.showNotification('Failed to initialize app. Please refresh.', 'error');
            }
        });
    }
    initializeWebSocket() {
        return __awaiter(this, void 0, void 0, function* () {
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
                        }
                        catch (error) {
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
                }
                catch (error) {
                    console.error('Failed to create WebSocket:', error);
                    reject(error);
                }
            });
        });
    }
    handleWebSocketMessage(message) {
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
    handleNodeResult(message) {
        const node = this.canvas.getNode(message.node_id);
        if (node) {
            node.data = message.result;
            node.metadata = message.metadata;
            this.canvas.updateNode(node);
        }
    }
    executeWorkflow() {
        return __awaiter(this, void 0, void 0, function* () {
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
                this.websocket.send(JSON.stringify(message));
                this.showNotification('Executing workflow...', 'info');
            }
            catch (error) {
                console.error('Error executing workflow:', error);
                this.showNotification('Failed to execute workflow', 'error');
            }
        });
    }
    setupGlobalEventListeners() {
        // Fix event listener casting
        window.addEventListener('openNodeConfig', ((event) => {
            this.componentsPanel.openNodeConfiguration(event.detail);
        }));
        window.addEventListener('duplicateNode', ((event) => {
            this.duplicateNode(event.detail);
        }));
        window.addEventListener('deleteNode', ((event) => {
            this.deleteNode(event.detail);
        }));
        document.addEventListener('keydown', (event) => {
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
                        }
                        else {
                            this.undo();
                        }
                        break;
                    case 'Delete':
                        this.deleteSelectedNodes();
                        break;
                }
            }
        });
        window.addEventListener('beforeunload', (event) => {
            if (this.hasUnsavedChanges()) {
                event.preventDefault();
                return 'You have unsaved changes. Are you sure you want to leave?';
            }
        });
    }
    deleteSelectedNodes() {
        const selectedNodes = this.canvas.getSelectedNodes();
        selectedNodes.forEach((node) => this.deleteNode(node.id));
    }
    getSelectedNodes() {
        return this.canvas.getNodes().filter((node) => node.selected);
    }
    hasUnsavedChanges() {
        return true; // Simplified for now
    }
    saveWorkflow() {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                const workflow = this.canvas.serialize();
                const workflowId = this.currentWorkflowId || `workflow_${Date.now()}`;
                localStorage.setItem(`workflow_${workflowId}`, JSON.stringify(workflow));
                this.currentWorkflowId = workflowId;
                this.showNotification('Workflow saved', 'success');
            }
            catch (error) {
                console.error('Error saving workflow:', error);
                this.showNotification('Failed to save workflow', 'error');
            }
        });
    }
    loadSavedWorkflow() {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                const savedWorkflows = Object.keys(localStorage).filter(key => key.startsWith('workflow_'));
                if (savedWorkflows.length > 0) {
                    const latestWorkflow = savedWorkflows[savedWorkflows.length - 1];
                    const workflowData = JSON.parse(localStorage.getItem(latestWorkflow));
                    this.canvas.deserialize(workflowData);
                    this.currentWorkflowId = latestWorkflow.replace('workflow_', '');
                    this.showNotification('Workflow loaded', 'success');
                }
            }
            catch (error) {
                console.error('Error loading workflow:', error);
            }
        });
    }
    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    // Placeholder methods for undo/redo
    undo() {
        console.log('Undo not implemented yet');
    }
    redo() {
        console.log('Redo not implemented yet');
    }
    duplicateNode(nodeId) {
        console.log('Duplicate node not implemented yet:', nodeId);
    }
    deleteNode(nodeId) {
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
    window.weevApp = app;
});
export { WeevApp };
