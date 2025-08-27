<script lang="ts">
 import { onMount, createEventDispatcher } from 'svelte';
 import type { Node, Connection } from './types';
 import WorkflowNode from './WorkflowNode.svelte';

 export let nodes: Map<string, Node> = new Map();
 export let connections: Map<string, Connection> = new Map();
 export let selectedNodeId: string | null = null;

 const dispatch = createEventDispatcher<{
  nodeSelect: { nodeId: string };
  nodeAdd: { type: string; position: { x: number; y: number } };
  connectionCreate: { from: string; to: string };
 }>();

 let canvasElement: HTMLDivElement;
 let scale = 1;
 let offsetX = 0;
 let offsetY = 0;
 let isDraggingCanvas = false;
 let dragStartX = 0;
 let dragStartY = 0;
 let canvasStartX = 0;
 let canvasStartY = 0;

 let draggedNodeId: string | null = null;
 let initialNodePosition: { x: number; y: number } = { x: 0, y: 0 };
 let initialMouseX = 0;
 let initialMouseY = 0;

 // Connection state
 let isConnecting = false;
 let connectionStart: string | null = null;

function typeColorVar(t: string): string {
  switch (t) {
    case 'brain': return 'var(--acc-brain)';
    case 'input': return 'var(--acc-input)';
    case 'output': return 'var(--acc-output)';
    case 'knowledge': return 'var(--acc-knowledge)';
    case 'tool': return 'var(--acc-tool)';
    default: return 'var(--accent-primary)';
  }
}

onMount(() => {
  const containerRect = canvasElement.parentElement?.getBoundingClientRect();
  if (containerRect) {
   offsetX = containerRect.width / 2 - 2500 * scale;
   offsetY = containerRect.height / 2 - 2500 * scale;
  }
  updateCanvasTransform();
});

 // Minimap removed; no viewport tracking needed

 function updateCanvasTransform() {
  if (canvasElement) {
   canvasElement.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
  }
 }

 function handleMouseDown(e: MouseEvent) {
  if (e.target === canvasElement) {
   isDraggingCanvas = true;
   dragStartX = e.clientX;
   dragStartY = e.clientY;
   canvasStartX = offsetX;
   canvasStartY = offsetY;
  }
 }

 function handleMouseMove(e: MouseEvent) {
  if (isDraggingCanvas) {
   const deltaX = e.clientX - dragStartX;
   const deltaY = e.clientY - dragStartY;
   offsetX = canvasStartX + deltaX;
   offsetY = canvasStartY + deltaY;
   updateCanvasTransform();
  } else if (draggedNodeId) {
   const dx = e.clientX - initialMouseX;
   const dy = e.clientY - initialMouseY;
   const node = nodes.get(draggedNodeId);
   if (node) {
    node.position.x = initialNodePosition.x + dx / scale;
    node.position.y = initialNodePosition.y + dy / scale;
    nodes = nodes; // Trigger reactivity
   }
  }
}

function handleMouseUp() {
  isDraggingCanvas = false;
  draggedNodeId = null;
}

 function handleDoubleClick(e: MouseEvent) {
  if (e.target === canvasElement) {
   const rect = canvasElement.getBoundingClientRect();
   const x = (e.clientX - rect.left) / scale;
   const y = (e.clientY - rect.top) / scale;
   
   dispatch('nodeAdd', { type: 'brain', position: { x, y } });
  }
 }

 function handleWheel(e: WheelEvent) {
  e.preventDefault();
  const zoomIntensity = 0.1;
  const containerRect = canvasElement.parentElement?.getBoundingClientRect();
  
  if (!containerRect) return;

  const mouseX = e.clientX - containerRect.left;
  const mouseY = e.clientY - containerRect.top;
  
  const canvasX = (mouseX - offsetX) / scale;
  const canvasY = (mouseY - offsetY) / scale;
  
  const wheel = e.deltaY < 0 ? 1 : -1;
  scale *= (1 + wheel * zoomIntensity);
  scale = Math.min(Math.max(0.1, scale), 5);
  
  offsetX = mouseX - canvasX * scale;
  offsetY = mouseY - canvasY * scale;
  
  updateCanvasTransform();
 }

 function handleKeyDown(e: KeyboardEvent) {
  const panStep = 40;
  if (e.key === 'ArrowLeft') { offsetX += panStep; updateCanvasTransform(); e.preventDefault(); }
  else if (e.key === 'ArrowRight') { offsetX -= panStep; updateCanvasTransform(); e.preventDefault(); }
  else if (e.key === 'ArrowUp') { offsetY += panStep; updateCanvasTransform(); e.preventDefault(); }
  else if (e.key === 'ArrowDown') { offsetY -= panStep; updateCanvasTransform(); e.preventDefault(); }
  else if (e.key === '+' || e.key === '=') { zoom(1.2); e.preventDefault(); }
  else if (e.key === '-' || e.key === '_') { zoom(0.8); e.preventDefault(); }
 }

 function zoom(factor: number) {
  scale *= factor;
  scale = Math.min(Math.max(0.1, scale), 5);
  updateCanvasTransform();
 }

 function resetView() {
  scale = 1;
  const containerRect = canvasElement.parentElement?.getBoundingClientRect();
  if (containerRect) {
   offsetX = containerRect.width / 2 - 2500;
   offsetY = containerRect.height / 2 - 2500;
  }
  updateCanvasTransform();
 }

 function handleConnectionStart(nodeId: string) {
  isConnecting = true;
  connectionStart = nodeId;
  console.log('🔗 Starting connection from:', nodeId);
 }

 function handleConnectionEnd(nodeId: string) {
  if (isConnecting && connectionStart && connectionStart !== nodeId) {
   dispatch('connectionCreate', { from: connectionStart, to: nodeId });
   console.log('✅ Connection created:', connectionStart, '->', nodeId);
  }
  isConnecting = false;
  connectionStart = null;
 }

function handleNodeStartDrag(event: CustomEvent<{ nodeId: string; event: MouseEvent }>) {
 const { nodeId, event: mouseEvent } = event.detail;
 draggedNodeId = nodeId;
 const node = nodes.get(nodeId);
 if (node) {
  initialNodePosition.x = node.position.x;
  initialNodePosition.y = node.position.y;
 }
 initialMouseX = mouseEvent.clientX;
 initialMouseY = mouseEvent.clientY;
 // ensure canvas dragging is off while dragging node
 isDraggingCanvas = false;
}

 // Reactive statement to update transform
 $: if (canvasElement) updateCanvasTransform();

 // Convert nodes Map to Array for iteration
 $: nodesArray = Array.from(nodes.values());
 $: connectionsArray = Array.from(connections.values());
</script>

<div 
 class="canvas-container"
 role="application"
 aria-label="Workflow canvas container"
>
 <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
 <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
 <div 
  class="canvas"
  role="application"
  aria-label="Zoomable and pannable workflow canvas"
  bind:this={canvasElement}
  tabindex="0"
  style={`--scale: ${scale}`}
  on:keydown={handleKeyDown}
  on:mousedown={handleMouseDown}
  on:mousemove={handleMouseMove}
  on:mouseup={handleMouseUp}
  on:mouseleave={handleMouseUp}
  on:wheel={handleWheel}
  on:dblclick={handleDoubleClick}
 >
  <!-- Render connections as SVG -->
  <svg class="connections-layer">
   {#each connectionsArray as connection}
    {@const fromNode = nodes.get(connection.from)}
    {@const toNode = nodes.get(connection.to)}
    {#if fromNode && toNode}
      {@const fromW = fromNode.type === 'input' ? 200 : 160}
      {@const fromH = fromNode.type === 'input' ? 120 : 88}
      {@const outOff = fromNode.type === 'input' ? 28 : 0}
      {@const toH = toNode.type === 'input' ? 120 : 88}
      {@const x1 = fromNode.position.x + fromW + outOff}
      {@const y1 = fromNode.position.y + fromH / 2}
      {@const x2 = toNode.position.x}
      {@const y2 = toNode.position.y + toH / 2}
      {@const dx = Math.max(40, Math.abs(x2 - x1) * 0.35)}
      <path class="edge" style={`--edge-color: ${typeColorVar(fromNode.type)}`} d={`M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`} />
    {/if}
   {/each}
   <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="coloredBlur" />
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
   </defs>
  </svg>

  <!-- Render nodes -->
  {#each nodesArray as node}
   <WorkflowNode
    {node}
    selected={selectedNodeId === node.id}
    on:connectionStart={() => handleConnectionStart(node.id)}
    on:connectionEnd={() => handleConnectionEnd(node.id)}
    on:nodestartdrag={handleNodeStartDrag}
   />
  {/each}
 </div>

 <!-- Canvas controls and minimap removed per design request -->
</div>

 <style>
 .canvas-container {
  position: relative;
  width: 100%;
  height: 100vh;
  background: transparent;
  overflow: hidden;
  cursor: grab;
 }

 .canvas-container:active {
  cursor: grabbing;
 }

 .canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 5000px;
  height: 5000px;
  background: var(--canvas-bg);
  background-image: 
    /* Dot grid pattern */
    radial-gradient(circle at 1px 1px, var(--canvas-grid) 1px, transparent 0),
    /* Ambient lighting - darker edges, lighter center */
    radial-gradient(ellipse 2000px 1500px at 50% 45%, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0.1) 40%, rgba(0, 0, 0, 0.02) 100%),
    /* Subtle color zones for visual interest */
    radial-gradient(ellipse 1200px 800px at 20% 30%, rgba(59, 130, 246, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse 1000px 600px at 80% 70%, rgba(139, 92, 246, 0.03) 0%, transparent 50%);
  background-size: 20px 20px, 100% 100%, 100% 100%, 100% 100%;
  cursor: grab;
 }
 .canvas:active { cursor: grabbing; }

.connections-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.edge {
  fill: none;
  stroke-width: 3;
  stroke: var(--acc-input);
  stroke-opacity: 0.8;
  stroke-linecap: round;
  pointer-events: none;
  filter: 
    drop-shadow(0 0 6px rgba(96, 165, 250, 0.4))
    drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  transition: all 0.3s var(--ease-smooth);
}

.edge.brain { 
  stroke: var(--acc-brain); 
  filter: 
    drop-shadow(0 0 6px rgba(167, 139, 250, 0.4))
    drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.edge.output { 
  stroke: var(--acc-output);
  filter: 
    drop-shadow(0 0 6px rgba(74, 222, 128, 0.4))
    drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.edge.knowledge { 
  stroke: var(--acc-knowledge);
  filter: 
    drop-shadow(0 0 6px rgba(129, 140, 248, 0.4))
    drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.edge.tool { 
  stroke: var(--acc-tool);
  filter: 
    drop-shadow(0 0 6px rgba(251, 191, 36, 0.4))
    drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

/* Enhanced glow on hover (when parent node is hovered) */
.workflow-node:hover ~ .connections-layer .edge,
.edge:hover {
  stroke-width: 4;
  filter: 
    drop-shadow(0 0 12px rgba(var(--glow-color, 96, 165, 250), 0.6))
    drop-shadow(0 4px 8px rgba(0, 0, 0, 0.15));
}

@keyframes flow {
  to { stroke-dashoffset: -320; }
}

@media (prefers-reduced-motion: reduce) {
  .edge { animation: none; }
}

/* Controls and minimap styles removed */
</style>
