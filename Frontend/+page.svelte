<script lang="ts">
 import { onMount } from 'svelte';
 import Canvas from './Canvas.svelte';
import ComponentsPanel from './ComponentsPanel.svelte';
 import { websocketService } from './websocket';
 import type { Node, Connection, ExecutionUpdate } from './types';
 import ToolConfigPanel from './ToolConfigPanel.svelte';

let nodes: Map<string, Node> = new Map();
let connections: Map<string, Connection> = new Map();
let selectedNodeId: string | null = null;
let executionResults: ExecutionUpdate[] = [];

type Project = {
  id: string;
  name: string;
  updatedAt: string;
  data: {
    nodes: Node[];
    connections: Connection[];
  };
};

let projects: Project[] = [];
let currentProjectId: string = 'new';
let sidebarCollapsed: boolean = false;

function saveProjects() {
  localStorage.setItem('weev-projects', JSON.stringify(projects));
}

function loadProjects() {
  const raw = localStorage.getItem('weev-projects');
  if (raw) {
    try {
      const parsed: Project[] = JSON.parse(raw);
      projects = parsed;
      if (projects.length > 0) {
        currentProjectId = projects[0].id;
        loadProjectIntoCanvas(projects[0]);
        return;
      }
    } catch {}
  }
  // initialize first project if none
  const first: Project = {
    id: `proj_${Date.now()}`,
    name: 'Untitled',
    updatedAt: new Date().toISOString(),
    data: { nodes: [], connections: [] }
  };
  projects = [first];
  currentProjectId = first.id;
  saveProjects();
  loadProjectIntoCanvas(first);
}

function loadProjectIntoCanvas(p: Project) {
  nodes = new Map(p.data.nodes.map(n => [n.id, structuredClone(n)]));
  connections = new Map(p.data.connections.map(c => [c.id, structuredClone(c)]));
  selectedNodeId = null;
}

function persistCurrentProject() {
  const idx = projects.findIndex(p => p.id === currentProjectId);
  if (idx === -1) return;
  projects[idx] = {
    ...projects[idx],
    updatedAt: new Date().toISOString(),
    data: {
      nodes: Array.from(nodes.values()),
      connections: Array.from(connections.values())
    }
  };
  saveProjects();
}

onMount(() => {
 // Load projects
 loadProjects();

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
   knowledge: 'Knowledge',
   tool: 'Tool'
  };
  
  const newNode: Node = {
   id: nodeId,
   type: event.detail.type as any,
   position: { 
    x: 2400 + Math.random() * 100, // Center-ish with slight randomness
    y: 2400 + Math.random() * 100 
   },
   data: {
    label: (event.detail.type === 'input') ? '' : nodeTypes[event.detail.type as keyof typeof nodeTypes],
    configuration: event.detail.type === 'tool' 
      ? { tool: 'email', action: 'draft', params: { to: ['user@example.com'], subject: 'Hello' }, mock: true }
      : {}
   }
  };

  nodes.set(nodeId, newNode);
  nodes = nodes; // Trigger reactivity
  selectedNodeId = nodeId;
  persistCurrentProject();
}

 function handleCanvasNodeAdd(event: CustomEvent<{ type: string; position: { x: number; y: number } }>) {
  const nodeId = `node_${Date.now()}`;
  const nodeTypes = {
   brain: 'AI Brain',
   input: 'Input',
   output: 'Output', 
   knowledge: 'Knowledge',
   tool: 'Tool'
  };
  
  const newNode: Node = {
   id: nodeId,
   type: event.detail.type as any,
   position: event.detail.position,
   data: {
    label: (event.detail.type === 'input') ? '' : nodeTypes[event.detail.type as keyof typeof nodeTypes],
    configuration: event.detail.type === 'tool' 
      ? { tool: 'email', action: 'draft', params: { to: ['user@example.com'], subject: 'Hello' }, mock: true }
      : {}
   }
  };

  nodes.set(nodeId, newNode);
  nodes = nodes; // Trigger reactivity
  selectedNodeId = nodeId;
  persistCurrentProject();
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
  persistCurrentProject();
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

function handleToolConfigUpdate(event: CustomEvent<{ configuration: Record<string, any> }>) {
  if (!selectedNodeId) return;
  const node = nodes.get(selectedNodeId);
  if (!node) return;
  node.data.configuration = event.detail.configuration;
  nodes = nodes; // trigger reactivity
  persistCurrentProject();
}

function handleNewProject() {
  const p: Project = {
    id: `proj_${Date.now()}`,
    name: 'Untitled',
    updatedAt: new Date().toISOString(),
    data: { nodes: [], connections: [] }
  };
  projects = [p, ...projects];
  currentProjectId = p.id;
  saveProjects();
  loadProjectIntoCanvas(p);
}

function handleSelectProject(id: string) {
  const p = projects.find(pp => pp.id === id);
  if (!p) return;
  currentProjectId = id;
  loadProjectIntoCanvas(p);
}

function handleDeleteProject(id: string) {
  const idx = projects.findIndex(p => p.id === id);
  if (idx === -1) return;
  const deletingCurrent = projects[idx].id === currentProjectId;
  projects.splice(idx, 1);
  saveProjects();
  if (projects.length === 0) {
    // create a fresh project
    handleNewProject();
    return;
  }
  if (deletingCurrent) {
    const next = projects[0];
    currentProjectId = next.id;
    loadProjectIntoCanvas(next);
  }
}
</script>

<svelte:head>
 <title>Weev - AI Agent Workflow Builder</title>
  <!-- Light mode font: Inter -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
</svelte:head>

<div class="app">
  
  <main class="main">
    <Canvas 
      bind:nodes
      bind:connections
      bind:selectedNodeId
      on:nodeAdd={handleCanvasNodeAdd}
      on:nodeSelect={handleNodeSelect}
      on:connectionCreate={handleConnectionCreate}
    />
    <ComponentsPanel 
      projects={projects}
      currentProjectId={currentProjectId}
      collapsed={sidebarCollapsed}
      on:toggleCollapse={() => (sidebarCollapsed = !sidebarCollapsed)}
      on:newProject={handleNewProject}
      on:selectProject={(e) => handleSelectProject(e.detail.id)}
      on:deleteProject={(e) => handleDeleteProject(e.detail.id)}
      on:nodeAdd={handleNodeAdd}
      on:run={executeWorkflow}
    />
  </main>
</div>

<style>
  /* Premium AI Environment Theme */
  :global(:root) {
    --canvas-bg: #FAFAF9;
    --canvas-grid: #E5E5E5;
    --app-bg: linear-gradient(135deg, #FAFAF9 0%, #F8F8F7 100%);
    
    /* Premium glassmorphism system */
    --glass: rgba(255, 255, 255, 0.75);
    --glass-border: rgba(255, 255, 255, 0.2);
    --panel-float: rgba(255, 255, 255, 0.85);
    --node-glass: rgba(255, 255, 255, 0.9);
    
    --border: rgba(0, 0, 0, 0.06);
    --border-soft: rgba(0, 0, 0, 0.03);
    --text: #1A1A1A;
    --text-secondary: #4A4A4A;
    --muted: rgba(0, 0, 0, 0.45);
    
    /* Premium shadows & effects */
    --shadow-soft: 0 2px 16px rgba(0, 0, 0, 0.04);
    --shadow-float: 0 8px 32px rgba(0, 0, 0, 0.08);
    --shadow-node: 0 4px 24px rgba(0, 0, 0, 0.06);
    --glow-subtle: 0 0 20px rgba(255, 255, 255, 0.6);
    
    /* Spring animations */
    --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
    --ease-smooth: cubic-bezier(0.25, 0.46, 0.45, 0.94);
    --ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);

    /* Premium node type gradients */
    --grad-input: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%);      /* blue to cyan */
    --grad-brain: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%);      /* purple to pink */
    --grad-output: linear-gradient(135deg, #10B981 0%, #34D399 100%);     /* emerald gradient */
    --grad-knowledge: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);  /* indigo to violet */
    --grad-tool: linear-gradient(135deg, #F59E0B 0%, #EAB308 100%);       /* amber gradient */
    
    /* Accent colors (lighter versions for UI elements) */
    --acc-input: #60A5FA;
    --acc-brain: #A78BFA;
    --acc-output: #4ADE80;
    --acc-knowledge: #818CF8;
    --acc-tool: #FBBF24;
  }

  :global(html, body) {
    height: 100%;
  }

  :global(body) {
    margin: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-weight: 400;
    color: var(--text);
    background: var(--app-bg);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  .app { display:flex; flex-direction: column; height: 100vh; }

  /* Removed unused topbar styles */

  .main {
    flex: 1;
    position: relative;
    overflow: hidden;
  }

  /* Selection */
  :global(::selection) {
    background: rgba(165, 180, 252, 0.35);
  }
</style>
