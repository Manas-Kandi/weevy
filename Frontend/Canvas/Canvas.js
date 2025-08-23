export class Canvas {
    constructor(containerId) {
        this.nodes = [];
        this.connections = [];
        console.log(`Canvas initialized with container: ${containerId}`);
    }
    addNode(type, position, configuration) {
        const nodeId = `node_${Date.now()}`;
        const node = {
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
    getNodes() {
        return this.nodes;
    }
    getNode(nodeId) {
        return this.nodes.find(node => node.id === nodeId);
    }
    updateNode(node) {
        const index = this.nodes.findIndex(n => n.id === node.id);
        if (index !== -1) {
            this.nodes[index] = node;
        }
    }
    deleteNode(nodeId) {
        this.nodes = this.nodes.filter(node => node.id !== nodeId);
        this.connections = this.connections.filter(conn => conn.source !== nodeId && conn.target !== nodeId);
    }
    getSelectedNodes() {
        return this.nodes.filter(node => node.selected);
    }
    getConnections() {
        return this.connections;
    }
    serialize() {
        return {
            nodes: this.nodes,
            connections: this.connections
        };
    }
    deserialize(data) {
        this.nodes = data.nodes || [];
        this.connections = data.connections || [];
    }
    clearCanvas() {
        this.nodes = [];
        this.connections = [];
        console.log('Canvas cleared');
    }
}
