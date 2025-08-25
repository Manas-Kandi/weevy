<script lang="ts">
 import { onMount } from 'svelte';
 import Canvas from '$lib/components/Canvas.svelte';
 import ComponentsPanel from '$lib/components/ComponentsPanel.svelte';
 import { websocketService } from '$lib/websocket.js';
 import type { Node, Connection, ExecutionUpdate } from '$lib/types.js';

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
    node_type: ({ brain: 'BrainNode', input: 'InputNode', output: 'OutputNode', knowledge: 'KnowledgeBaseNode' } as Record<string,string>)[node.type],
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
  background-color: #1a1a1a;
  color: #e0e0e0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
 }

 .header {
  background-color: #2d2d2d;
  padding: 16px;
  border-bottom: 1px solid #404040;
  display: flex;
  justify-content: space-between;
  align-items: center;
 }

 .header h1 {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
 }

 .execute-btn {
  background-color: #10B981;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
 }

 .execute-btn:hover {
  background-color: #059669;
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
  width: 300px;
  max-height: 400px;
  background-color: #2d2d2d;
  border: 1px solid #404040;
  border-radius: 8px;
  padding: 16px;
  z-index: 10;
  overflow-y: auto;
 }

 .results-panel h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
 }

 .result-item {
  margin-bottom: 12px;
  padding: 8px;
  background-color: #3d3d3d;
  border-radius: 4px;
  border-left: 3px solid #10B981;
 }

 .result-item.error {
  border-left-color: #EF4444;
 }

 .result-item strong {
  color: #10B981;
  text-transform: uppercase;
  font-size: 12px;
 }

 .result-item.error strong {
  color: #EF4444;
 }

 .result-item p {
  margin: 4px 0;
  font-size: 14px;
 }

 .result-item pre {
  background-color: #1a1a1a;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  margin: 8px 0;
 }

 .error-text {
  color: #EF4444;
 }
</style>
