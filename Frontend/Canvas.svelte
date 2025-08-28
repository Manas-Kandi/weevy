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
 let isAnimating = false;

 let draggedNodeId: string | null = null;
 let initialNodePosition: { x: number; y: number } = { x: 0, y: 0 };
 let initialMouseX = 0;
 let initialMouseY = 0;

 // Connection state
 let isConnecting = false;
 let connectionStart: string | null = null;
 let connectionPreview: { startX: number; startY: number; endX: number; endY: number } | null = null;

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
   // No transitions for instant, responsive feel
   canvasElement.style.transition = 'none';
   canvasElement.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
  }
 }

 function handleMouseDown(e: MouseEvent) {
  if (e.target === canvasElement) {
   // Clear node selection when clicking canvas
   selectedNodeId = null;
   
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
  } else if (isConnecting && connectionPreview) {
   // Update connection preview end position
   const rect = canvasElement.getBoundingClientRect();
   connectionPreview.endX = (e.clientX - rect.left - offsetX) / scale;
   connectionPreview.endY = (e.clientY - rect.top - offsetY) / scale;
   connectionPreview = { ...connectionPreview }; // Trigger reactivity
  }
}

function handleMouseUp() {
  isDraggingCanvas = false;
  draggedNodeId = null;
  
  // End connection if we're connecting
  if (isConnecting) {
   isConnecting = false;
   connectionStart = null;
   connectionPreview = null;
  }
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
  
  const containerRect = canvasElement.parentElement?.getBoundingClientRect();
  if (!containerRect) return;

  const mouseX = e.clientX - containerRect.left;
  const mouseY = e.clientY - containerRect.top;
  
  // Handle pinch-to-zoom (detected by ctrlKey on macOS)
  if (e.ctrlKey) {
   const canvasX = (mouseX - offsetX) / scale;
   const canvasY = (mouseY - offsetY) / scale;
   
   // Natural zoom like macOS - responsive but smooth
   const zoomSpeed = 0.01; // More responsive
   const zoomFactor = 1 + (e.deltaY > 0 ? -zoomSpeed : zoomSpeed);
   const newScale = scale * zoomFactor;
   
   scale = Math.min(Math.max(0.1, newScale), 5);
   
   offsetX = mouseX - canvasX * scale;
   offsetY = mouseY - canvasY * scale;
  } else {
   // Two-finger scroll for panning
   offsetX -= e.deltaX;
   offsetY -= e.deltaY;
  }
  
  updateCanvasTransform();
 }

 function handleKeyDown(e: KeyboardEvent) {
  const panStep = 50;
  
  if (e.key === 'ArrowLeft') { offsetX += panStep; updateCanvasTransform(); e.preventDefault(); }
  else if (e.key === 'ArrowRight') { offsetX -= panStep; updateCanvasTransform(); e.preventDefault(); }
  else if (e.key === 'ArrowUp') { offsetY += panStep; updateCanvasTransform(); e.preventDefault(); }
  else if (e.key === 'ArrowDown') { offsetY -= panStep; updateCanvasTransform(); e.preventDefault(); }
  else if (e.key === '+' || e.key === '=') { smoothZoom(1.2); e.preventDefault(); }
  else if (e.key === '-' || e.key === '_') { smoothZoom(0.8); e.preventDefault(); }
 }

 function zoom(factor: number) {
  scale *= factor;
  scale = Math.min(Math.max(0.1, scale), 5);
  updateCanvasTransform();
 }

 function smoothZoom(factor: number) {
  const containerRect = canvasElement.parentElement?.getBoundingClientRect();
  if (!containerRect) return;
  
  // Zoom towards center of viewport
  const centerX = containerRect.width / 2;
  const centerY = containerRect.height / 2;
  
  const canvasX = (centerX - offsetX) / scale;
  const canvasY = (centerY - offsetY) / scale;
  
  scale *= factor;
  scale = Math.min(Math.max(0.1, scale), 5);
  
  offsetX = centerX - canvasX * scale;
  offsetY = centerY - canvasY * scale;
  
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

 function handleConnectionStart(event: CustomEvent<{ nodeId: string; port: string }>) {
 const { nodeId, port } = event.detail;
 isConnecting = true;
 connectionStart = nodeId;
 
 // Calculate start position for preview based on port
 const node = nodes.get(nodeId);
 if (node) {
  const startX = port === 'output' ? node.position.x + 320 : node.position.x;
  const startY = node.position.y + 120; // Center of node
  
  connectionPreview = {
   startX,
   startY,
   endX: startX,
   endY: startY
  };
 }
}

function handleConnectionEnd(event: CustomEvent<{ nodeId: string; port: string }>) {
 const { nodeId, port } = event.detail;
 if (isConnecting && connectionStart && connectionStart !== nodeId && port === 'input') {
  // Create connection from output to input
  const connectionId = `${connectionStart}-${nodeId}`;
  connections.set(connectionId, {
   id: connectionId,
   from: connectionStart,
   to: nodeId
  });
  connections = connections; // Trigger reactivity
 }
 isConnecting = false;
 connectionStart = null;
 connectionPreview = null;
}

function handleNodeDelete(event: CustomEvent<{ nodeId: string }>) {
 const { nodeId } = event.detail;
 nodes.delete(nodeId);
 nodes = nodes; // Trigger reactivity
 if (selectedNodeId === nodeId) {
  selectedNodeId = null;
 }
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
      {@const fromW = 320}
      {@const fromH = 240}
      {@const outOff = 0}
      {@const toH = 240}
      {@const x1 = fromNode.position.x + fromW + outOff}
      {@const y1 = fromNode.position.y + fromH / 2}
      {@const x2 = toNode.position.x}
      {@const y2 = toNode.position.y + toH / 2}
      {@const dx = Math.max(40, Math.abs(x2 - x1) * 0.35)}
      <path class="edge" style={`--edge-color: ${typeColorVar(fromNode.type)}`} d={`M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`} />
    {/if}
   {/each}
   {#if connectionPreview}
    <path class="edge preview" stroke="#3B82F6" stroke-width="3" stroke-dasharray="8,4" fill="none" opacity="0.7" d={`M ${connectionPreview.startX} ${connectionPreview.startY} C ${connectionPreview.startX + 100} ${connectionPreview.startY}, ${connectionPreview.endX - 100} ${connectionPreview.endY}, ${connectionPreview.endX} ${connectionPreview.endY}`} />
   {/if}
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
    on:connectionStart={handleConnectionStart}
    on:connectionEnd={handleConnectionEnd}
    on:nodestartdrag={handleNodeStartDrag}
    on:delete={handleNodeDelete}
    on:select={() => selectedNodeId = node.id}
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
    /* Dense random dot pattern - multiple layers for organic feel */
    radial-gradient(circle at 0.3px 0.3px, rgba(0, 0, 0, 0.08) 0.3px, transparent 0),
    radial-gradient(circle at 2.1px 3.7px, rgba(0, 0, 0, 0.06) 0.3px, transparent 0),
    radial-gradient(circle at 4.8px 1.2px, rgba(0, 0, 0, 0.05) 0.3px, transparent 0),
    radial-gradient(circle at 1.7px 2.9px, rgba(0, 0, 0, 0.07) 0.3px, transparent 0),
    radial-gradient(circle at 3.4px 4.1px, rgba(0, 0, 0, 0.04) 0.3px, transparent 0),
    radial-gradient(circle at 0.9px 4.6px, rgba(0, 0, 0, 0.06) 0.3px, transparent 0),
    /* Ambient lighting - darker edges, lighter center */
    radial-gradient(ellipse 2000px 1500px at 50% 45%, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0.1) 40%, rgba(0, 0, 0, 0.02) 100%),
    /* Subtle color zones for visual interest */
    radial-gradient(ellipse 1200px 800px at 20% 30%, rgba(59, 130, 246, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse 1000px 600px at 80% 70%, rgba(139, 92, 246, 0.03) 0%, transparent 50%);
  background-size: 6px 6px, 6px 6px, 6px 6px, 6px 6px, 6px 6px, 6px 6px, 100% 100%, 100% 100%, 100% 100%;
  cursor: grab;
  will-change: transform;
 }
 .canvas:active { cursor: grabbing; }
 
 /* Ultra-smooth trackpad interactions */
 .canvas {
  transform-origin: 0 0;
  transition: none; /* No transitions for instant feedback */
 }

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
