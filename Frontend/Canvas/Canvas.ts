export interface CanvasNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: any;
  metadata?: any;
  selected?: boolean;
}

export interface CanvasConnection {
  source: string;
  target: string;
}

export interface WorkflowData {
  nodes: CanvasNode[];
  connections: CanvasConnection[];
}

export class Canvas {
  private nodes: CanvasNode[] = [];
  private connections: CanvasConnection[] = [];

  constructor(containerId: string) {
    console.log(`Canvas initialized with container: ${containerId}`);
  }

  addNode(type: any, position: { x: number; y: number }, configuration?: any): string {
    const nodeId = `node_${Date.now()}`;
    const node: CanvasNode = {
      id: nodeId,
      type,
      position,
      data: configuration || {},
      selected: false
    };
    this.nodes.push(node);
    console.log(`Added node ${nodeId} of type ${type} at position`, position);
    return nodeId;
  }

  getNodes(): CanvasNode[] {
    return this.nodes;
  }

  getNode(nodeId: string): CanvasNode | undefined {
    return this.nodes.find(node => node.id === nodeId);
  }

  updateNode(node: CanvasNode): void {
    const index = this.nodes.findIndex(n => n.id === node.id);
    if (index !== -1) {
      this.nodes[index] = node;
    }
  }

  deleteNode(nodeId: string): void {
    this.nodes = this.nodes.filter(node => node.id !== nodeId);
    this.connections = this.connections.filter(conn => 
      conn.source !== nodeId && conn.target !== nodeId
    );
  }

  getSelectedNodes(): CanvasNode[] {
    return this.nodes.filter(node => node.selected);
  }

  getConnections(): CanvasConnection[] {
    return this.connections;
  }

  serialize(): WorkflowData {
    return {
      nodes: this.nodes,
      connections: this.connections
    };
  }

  deserialize(data: WorkflowData): void {
    this.nodes = data.nodes || [];
    this.connections = data.connections || [];
  }

  clearCanvas(): void {
    this.nodes = [];
    this.connections = [];
    console.log('Canvas cleared');
  }
}