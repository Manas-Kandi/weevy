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
</svelte:head>

<div class="app">
  
  <main class="main" style={`margin-left: ${sidebarCollapsed ? '56px' : '200px'}` }>
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
    <Canvas 
      bind:nodes
      bind:connections
      bind:selectedNodeId
      on:nodeAdd={handleCanvasNodeAdd}
      on:nodeSelect={handleNodeSelect}
      on:connectionCreate={handleConnectionCreate}
    />
    
  </main>
</div>

<style>
.app { display:flex; flex-direction: column; height: 100vh; }
.topbar { height: 56px; display:flex; align-items:center; padding: 0 16px; gap: 12px; }
.topbar.minimal { background: transparent; box-shadow: none; border: none; }
.brand { font-weight: 600; letter-spacing: 0.2px; font-size: 14px; }
.spacer { flex: 1; }
.actions { display:flex; gap:10px; }
.btn { background: rgba(255,255,255,0.06); color: var(--text); border: none; border-radius: 0; padding: 6px 12px; cursor: pointer; transition: background 160ms ease; }
.btn:hover { background: rgba(255,255,255,0.1); }
.btn.ghost { background: transparent; }

.main {
  flex: 1;
  position: relative;
  overflow: hidden;
 }
</style>
