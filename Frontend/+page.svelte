<script lang="ts">
 import { onMount } from 'svelte';
 import Canvas from './Canvas.svelte';
 import ComponentsPanel from './ComponentsPanel.svelte';
 import { websocketService } from './websocket';
 import type { Node, Connection, ExecutionUpdate } from './types';

 let nodes: Map<string, Node> = new Map();
 let connections: Map<string, Connection> = new Map();
 let selectedNodeId: string | null = null;
 let executionResults: ExecutionUpdate[] = [];

 onMount(() => {
  // Connect to WebSocket
  websocketService.connect();
  websocketService.onMessage((data: ExecutionUpdate) => {
   executionResults = [...executionResults, data];
   console.log('📨 Execution update:', data);
  });

  return () => {
   websocketService.disconnect();
  };
 });

 function handleNodeAdd(event: CustomEvent<{ type: string }>) {
  const nodeId = `node_${Date.now()}`;
  const nodeTypes = {
   brain: 'AI Brain',
   input: 'Input', 
   output: 'Output',
   knowledge: 'Knowledge'
  };
  
  const newNode: Node = {
   id: nodeId,
   type: event.detail.type as any,
   position: { 
    x: 2400 + Math.random() * 100, // Center-ish with slight randomness
    y: 2400 + Math.random() * 100 
   },
   data: {
    label: nodeTypes[event.detail.type as keyof typeof nodeTypes],
    configuration: {}
   }
  };

  nodes.set(nodeId, newNode);
  nodes = nodes; // Trigger reactivity
  selectedNodeId = nodeId;
 }

 function handleCanvasNodeAdd(event: CustomEvent<{ type: string; position: { x: number; y: number } }>) {
  const nodeId = `node_${Date.now()}`;
  const nodeTypes = {
   brain: 'AI Brain',
   input: 'Input',
   output: 'Output', 
   knowledge: 'Knowledge'
  };
  
  const newNode: Node = {
   id: nodeId,
   type: event.detail.type as any,
   position: event.detail.position,
   data: {
    label: nodeTypes[event.detail.type as keyof typeof nodeTypes],
    configuration: {}
   }
  };

  nodes.set(nodeId, newNode);
  nodes = nodes; // Trigger reactivity
  selectedNodeId = nodeId;
 }

 function handleNodeSelect(event: CustomEvent<{ nodeId: string }>) {
  selectedNodeId = event.detail.nodeId;
 }

 function handleConnectionCreate(event: CustomEvent<{ from: string; to: string }>) {
  const connectionId = `${event.detail.from}-${event.detail.to}`;
  connections.set(connectionId, {
   id: connectionId,
   from: event.detail.from,
   to: event.detail.to
  });
  connections = connections; // Trigger reactivity
 }

 function executeWorkflow() {
  if (nodes.size === 0) {
   alert('Add some nodes to execute a workflow!');
   return;
  }

  const workflow = {
   workflow_id: `workflow_${Date.now()}`,
   nodes: Array.from(nodes.values()).map(node => ({
    node_id: node.id,
    node_type: node.type,
    system_rules: `Execute ${node.type} node`,
    user_configuration: node.data.configuration
   })),
   connections: Array.from(connections.values())
  };

  executionResults = []; // Clear previous results
  websocketService.executeWorkflow(workflow);
 }
</script>

<svelte:head>
 <title>Weev - AI Agent Workflow Builder</title>
</svelte:head>

<div class="app">
 <!-- Header -->
 <header class="header">
  <h1>Weev AI Agent Workflow Builder</h1>
  <button class="execute-btn" on:click={executeWorkflow}>
   ▶ Execute Workflow
  </button>
 </header>

 <!-- Main Canvas Area -->
 <main class="main">
  <ComponentsPanel on:nodeAdd={handleNodeAdd} />
  
  <Canvas 
   bind:nodes
   bind:connections
   bind:selectedNodeId
   on:nodeAdd={handleCanvasNodeAdd}
   on:nodeSelect={handleNodeSelect}
   on:connectionCreate={handleConnectionCreate}
  />

  <!-- Execution Results Panel -->
  {#if executionResults.length > 0}
   <div class="results-panel">
    <h3>Execution Results</h3>
    <div class="results-content">
     {#each executionResults as result}
      <div class="result-item" class:error={result.type === 'execution_error'}>
       <strong>{result.type}</strong>
       {#if result.content}
        <p>{result.content}</p>
       {/if}
       {#if result.result}
        <pre>{JSON.stringify(result.result, null, 2)}</pre>
       {/if}
       {#if result.error}
        <p class="error-text">{result.error}</p>
       {/if}
      </div>
     {/each}
    </div>
   </div>
  {/if}
 </main>
</div>

<style>
 .app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #181818;
  color: #e0e0e0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
 }

 .header {
  background-color: #202020;
  padding: 16px;
  border-bottom: 1px solid #303030;
  display: flex;
  justify-content: space-between;
  align-items: center;
 }

 .header h1 {
  font-size: 20px;
  font-weight: 500;
  margin: 0;
 }

 .execute-btn {
  background-color: #3B82F6;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
 }

 .execute-btn:hover {
  background-color: #2563EB;
 }

 .main {
  flex: 1;
  position: relative;
  overflow: hidden;
 }

 .results-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 350px;
  max-height: 500px;
  background-color: #202020;
  border: 1px solid #303030;
  border-radius: 8px;
  padding: 16px;
  z-index: 10;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
 }

 .results-panel h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 500;
 }

 .result-item {
  margin-bottom: 12px;
  padding: 12px;
  background-color: #282828;
  border-radius: 6px;
  border-left: 3px solid #3B82F6;
 }

 .result-item.error {
  border-left-color: #EF4444;
 }

 .result-item strong {
  color: #3B82F6;
  text-transform: uppercase;
  font-size: 12px;
  font-weight: 600;
 }

 .result-item.error strong {
  color: #EF4444;
 }

 .result-item p {
  margin: 8px 0;
  font-size: 14px;
 }

 .result-item pre {
  background-color: #181818;
  padding: 12px;
  border-radius: 4px;
  font-size: 13px;
  overflow-x: auto;
  margin: 8px 0;
 }

 .error-text {
  color: #EF4444;
 }
</style>
