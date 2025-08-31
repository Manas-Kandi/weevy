<script lang="ts">
 import { onMount, createEventDispatcher } from 'svelte';
 import type { Node, Connection } from './types';
 import WorkflowNode from './WorkflowNode.svelte';

 export let nodes: Map<string, Node> = new Map();
 export let connections: Map<string, Connection> = new Map();
 export let selectedNodeId: string | null = null;
 let selectedConnectionId: string | null = null;
 let hoveredConnectionId: string | null = null;

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
 let connectionStartPort: string | null = null;
 let connectionPreview: { startX: number; startY: number; endX: number; endY: number } | null = null;
 let dragConnectionPreview: { startX: number; startY: number; endX: number; endY: number } | null = null;

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
   // Clear selections when clicking canvas
   selectedNodeId = null;
   selectedConnectionId = null;
   
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
  else if (e.key === 'Delete' || e.key === 'Backspace') {
   if (selectedConnectionId) {
    connections.delete(selectedConnectionId);
    connections = connections; // Trigger reactivity
    selectedConnectionId = null;
    e.preventDefault();
   }
  }
  else if (e.key === 'Escape') {
   selectedConnectionId = null;
   selectedNodeId = null;
   e.preventDefault();
  }
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

 function getPortCoordinates(nodeId: string, portType: 'input' | 'output'): { x: number; y: number } | null {
  const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
  if (!nodeElement) return null;
  
  const portElement = nodeElement.querySelector(`.${portType}-port`);
  if (!portElement) return null;
  
  const portRect = portElement.getBoundingClientRect();
  const canvasRect = canvasElement.getBoundingClientRect();
  
  // Calculate port center in canvas coordinates
  const portCenterX = portRect.left + portRect.width / 2;
  const portCenterY = portRect.top + portRect.height / 2;
  
  // Convert to canvas coordinate space
  const canvasX = (portCenterX - canvasRect.left - offsetX) / scale;
  const canvasY = (portCenterY - canvasRect.top - offsetY) / scale;
  
  return { x: canvasX, y: canvasY };
 }

 function handleConnectionStart(event: CustomEvent<{ nodeId: string; port: string; startPoint: { x: number; y: number } }>) {
 const { nodeId, port, startPoint } = event.detail;
 isConnecting = true;
 connectionStart = nodeId;
 connectionStartPort = port;
 
 // Convert screen coordinates to canvas coordinates
 const rect = canvasElement.getBoundingClientRect();
 const canvasX = (startPoint.x - rect.left - offsetX) / scale;
 const canvasY = (startPoint.y - rect.top - offsetY) / scale;
 
 // Get the actual node position for better connection points
 const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
 if (nodeElement) {
  const nodeRect = nodeElement.getBoundingClientRect();
  const portX = port === 'output' ? nodeRect.right : nodeRect.left;
  const portY = nodeRect.top + nodeRect.height / 2;
  
  const portCanvasX = (portX - rect.left - offsetX) / scale;
  const portCanvasY = (portY - rect.top - offsetY) / scale;
  
  dragConnectionPreview = {
   startX: portCanvasX,
   startY: portCanvasY,
   endX: portCanvasX,
   endY: portCanvasY
  };
  return;
 }
 
 // Fallback to click position if node not found
 dragConnectionPreview = {
  startX: canvasX,
  startY: canvasY,
  endX: canvasX,
  endY: canvasY
 };
}

function handleConnectionDrag(event: CustomEvent<{ nodeId: string; startPoint: { x: number; y: number }; currentPoint: { x: number; y: number } }>) {
 if (!isConnecting || !dragConnectionPreview) return;
 
 const { currentPoint } = event.detail;
 const rect = canvasElement.getBoundingClientRect();
 
 // Convert to canvas coordinates
 const canvasX = (currentPoint.x - rect.left - offsetX) / scale;
 const canvasY = (currentPoint.y - rect.top - offsetY) / scale;
 
 // Update the preview line
 dragConnectionPreview.endX = canvasX;
 dragConnectionPreview.endY = canvasY;
 
 // Trigger reactivity with a new object
 dragConnectionPreview = { ...dragConnectionPreview };
 
 // Highlight potential drop targets
 const elements = document.elementsFromPoint(currentPoint.x, currentPoint.y);
 const targetPort = elements.find(el => el.classList?.contains('input-port'));
 const targetNode = targetPort?.closest('.pocket-note');
 
 // Update hover state for visual feedback
 document.querySelectorAll('.pocket-note').forEach(node => {
  node.classList.toggle('connection-target', node === targetNode);
 });
}

function handleConnectionComplete(event: CustomEvent<{ 
 fromNodeId: string; 
 toNodeId: string; 
 fromPort: string; 
 toPort: string;
 startPoint?: { x: number; y: number };
 endPoint?: { x: number; y: number };
}>) {
 const { fromNodeId, toNodeId, fromPort, toPort, startPoint, endPoint } = event.detail;
 
 // Prevent self-connections
 if (fromNodeId === toNodeId) {
  handleConnectionCancel({ detail: { nodeId: fromNodeId } });
  return;
 }
 
 // Check for duplicate connections
 const connectionId = `${fromNodeId}-${toNodeId}`;
 if (connections.has(connectionId)) {
  handleConnectionCancel({ detail: { nodeId: fromNodeId } });
  return;
 }
 
 // Get the actual node positions for the connection points
 const fromNode = document.querySelector(`[data-node-id="${fromNodeId}"]`);
 const toNode = document.querySelector(`[data-node-id="${toNodeId}"]`);
 
 if (!fromNode || !toNode) {
  handleConnectionCancel({ detail: { nodeId: fromNodeId } });
  return;
 }
 
 // Create connection between nodes with port references
 connections.set(connectionId, {
  id: connectionId,
  from: fromNodeId,
  to: toNodeId,
  fromPort: fromPort,
  toPort: toPort
 });
 
 // Trigger reactivity
 connections = new Map(connections);
 
 // Clean up
 resetConnectionState();
}

function resetConnectionState() {
 // Reset all connection-related state
 isConnecting = false;
 connectionStart = null;
 connectionStartPort = null;
 dragConnectionPreview = null;
 
 // Remove any hover states
 document.querySelectorAll('.pocket-note').forEach(node => {
  node.classList.remove('connection-target');
 });
}

function handleConnectionCancel(event: CustomEvent<{ nodeId: string }>) {
 resetConnectionState();
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
  class:connecting={isConnecting}
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
      {@const startCoords = getPortCoordinates(connection.from, 'output')}
      {@const endCoords = getPortCoordinates(connection.to, 'input')}
      {#if startCoords && endCoords}
        {@const distance = Math.abs(endCoords.x - startCoords.x)}
        {@const controlOffset = Math.min(60, distance * 0.3)}
        {@const isSelected = selectedConnectionId === connection.id}
        {@const isHovered = hoveredConnectionId === connection.id}
        <path 
          class="edge" 
          class:selected={isSelected}
          class:hovered={isHovered}
          stroke={isSelected ? "var(--acc-input)" : "var(--acc-input)"}
          stroke-width={isSelected || isHovered ? 3 : 2}
          opacity={isSelected ? 1 : 0.7}
          d={`M ${startCoords.x} ${startCoords.y} 
               C ${startCoords.x + controlOffset} ${startCoords.y}, 
                 ${endCoords.x - controlOffset} ${endCoords.y}, 
                 ${endCoords.x} ${endCoords.y}`}
          on:click|stopPropagation={() => {
            selectedConnectionId = connection.id;
            selectedNodeId = null; // Deselect any selected node
          }}
          on:mouseenter={() => hoveredConnectionId = connection.id}
          on:mouseleave={() => hoveredConnectionId = null}
          style="pointer-events: stroke; cursor: pointer;"
          marker-end="url(#arrowhead)"
        />
      {/if}
    {/if}
   {/each}
   {#if dragConnectionPreview}
    <path 
      class="connection-preview" 
      stroke="var(--acc-input)" 
      stroke-width="3" 
      stroke-dasharray="8,4" 
      fill="none" 
      opacity="0.8"
      d={`M ${dragConnectionPreview.startX} ${dragConnectionPreview.startY} 
           C ${dragConnectionPreview.startX + 60} ${dragConnectionPreview.startY}, 
             ${dragConnectionPreview.endX - 60} ${dragConnectionPreview.endY}, 
             ${dragConnectionPreview.endX} ${dragConnectionPreview.endY}`} 
      marker-end="url(#arrowhead)"
    />
   {/if}
   <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="8" refY="3.5" orient="auto" markerUnits="strokeWidth">
      <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" />
    </marker>
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
    on:connectionDrag={handleConnectionDrag}
    on:connectionComplete={handleConnectionComplete}
    on:connectionCancel={handleConnectionCancel}
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
.canvas.connecting { cursor: crosshair; }
 
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
  stroke-linecap: round;
  stroke-linejoin: round;
  pointer-events: stroke;
  transition: all 0.2s ease;
}

.edge:hover, .edge.hovered {
  stroke-width: 3;
  stroke-opacity: 1;
  filter: drop-shadow(0 0 4px rgba(59, 130, 246, 0.5));
}

.edge.selected {
  stroke-width: 3;
  stroke-opacity: 1;
  stroke: var(--acc-input);
  filter: drop-shadow(0 0 6px rgba(59, 130, 246, 0.6));
}

.connection-preview {
  stroke: var(--acc-input);
  stroke-width: 2;
  stroke-dasharray: 5, 3;
  fill: none;
  pointer-events: none;
  opacity: 0.8;
}

.connection-target {
  outline: 2px dashed rgba(59, 130, 246, 0.5);
  outline-offset: 2px;
  border-radius: 24px;
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

/* Enhanced connection feedback while connecting */
:global(.canvas.connecting .pocket-note) {
  outline: 2px dashed rgba(59, 130, 246, 0.2);
  outline-offset: 4px;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
  border-color: rgba(59, 130, 246, 0.15);
}

:global(.canvas.connecting .pocket-note:hover) {
  outline-color: rgba(59, 130, 246, 0.5);
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 
    0 8px 32px rgba(59, 130, 246, 0.15),
    0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px) scale(1.005);
}

:global(.canvas.connecting .pocket-note .input-port) {
  opacity: 1 !important;
  transform: translateY(-50%) scale(1.2);
  box-shadow: 
    0 0 0 3px rgba(255,255,255,1),
    0 0 20px rgba(16, 185, 129, 0.6),
    0 6px 20px rgba(0, 0, 0, 0.25);
  animation: pulsePort 1.5s ease-in-out infinite;
}

:global(.canvas.connecting .pocket-note:hover .input-port) {
  transform: translateY(-50%) scale(1.4);
  animation: fastPulsePort 0.8s ease-in-out infinite;
}

@keyframes pulsePort {
  0%, 100% { 
    box-shadow: 
      0 0 0 3px rgba(255,255,255,1),
      0 0 20px rgba(16, 185, 129, 0.6),
      0 6px 20px rgba(0, 0, 0, 0.25);
  }
  50% { 
    box-shadow: 
      0 0 0 3px rgba(255,255,255,1),
      0 0 25px rgba(16, 185, 129, 0.8),
      0 6px 20px rgba(0, 0, 0, 0.25);
  }
}

@keyframes fastPulsePort {
  0%, 100% { 
    box-shadow: 
      0 0 0 4px rgba(255,255,255,1),
      0 0 30px rgba(16, 185, 129, 0.9),
      0 8px 24px rgba(0, 0, 0, 0.3);
  }
  50% { 
    box-shadow: 
      0 0 0 4px rgba(255,255,255,1),
      0 0 35px rgba(16, 185, 129, 1),
      0 8px 24px rgba(0, 0, 0, 0.3);
  }
}

/* Controls and minimap styles removed */
</style>
