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
 let isDragging = false;
 let dragStartX = 0;
 let dragStartY = 0;
 let canvasStartX = 0;
 let canvasStartY = 0;

 // Connection state
 let isConnecting = false;
 let connectionStart: string | null = null;

 onMount(() => {
  // Center the canvas so (2500, 2500) is in the middle of the viewport
  const containerRect = canvasElement.parentElement?.getBoundingClientRect();
  if (containerRect) {
   offsetX = containerRect.width / 2 - 2500 * scale;
   offsetY = containerRect.height / 2 - 2500 * scale;
  }
  updateCanvasTransform();
 });

 function updateCanvasTransform() {
  if (canvasElement) {
   canvasElement.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
  }
 }

 function handleMouseDown(e: MouseEvent) {
  if (e.target === canvasElement || (e.target as Element)?.id === 'canvas-container') {
   isDragging = true;
   dragStartX = e.clientX;
   dragStartY = e.clientY;
   canvasStartX = offsetX;
   canvasStartY = offsetY;
  }
 }

 function handleMouseMove(e: MouseEvent) {
  if (isDragging) {
   const deltaX = e.clientX - dragStartX;
   const deltaY = e.clientY - dragStartY;
   offsetX = canvasStartX + deltaX;
   offsetY = canvasStartY + deltaY;
   updateCanvasTransform();
  }
 }

 function handleMouseUp() {
  isDragging = false;
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
  // Keyboard support for panning and zooming
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

 function handleNodeSelect(nodeId: string) {
  selectedNodeId = nodeId;
  dispatch('nodeSelect', { nodeId });
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
 <div 
  class="canvas"
  role="application"
  aria-label="Zoomable and pannable workflow canvas"
  bind:this={canvasElement}
  tabindex="0"
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
     <line
      x1={fromNode.position.x + 60}
      y1={fromNode.position.y + 40}
      x2={toNode.position.x}
      y2={toNode.position.y + 40}
      stroke="#666"
      stroke-width="2"
      marker-end="url(#arrowhead)"
     />
    {/if}
   {/each}
   <!-- Arrow marker definition -->
   <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" 
      refX="9" refY="3.5" orient="auto">
     <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
    </marker>
   </defs>
  </svg>

  <!-- Render nodes -->
  {#each nodesArray as node}
   <WorkflowNode
    {node}
    selected={selectedNodeId === node.id}
    on:select={() => handleNodeSelect(node.id)}
    on:connectionStart={() => handleConnectionStart(node.id)}
    on:connectionEnd={() => handleConnectionEnd(node.id)}
   />
  {/each}
 </div>

 <!-- Controls -->
 <div class="controls">
  <div class="zoom-level">{Math.round(scale * 100)}%</div>
  <button class="control-btn" on:click={() => zoom(1.2)}>+</button>
  <button class="control-btn" on:click={() => zoom(0.8)}>-</button>
  <button class="control-btn" on:click={resetView}>↺</button>
 </div>
</div>

<style>
 .canvas-container {
  position: relative;
  width: 100%;
  height: 100vh;
  background-color: #1e1e1e;
  overflow: hidden;
  cursor: grab;
 }

 .canvas-container:active {
  cursor: grabbing;
 }

 .canvas {
  position: absolute;
  width: 5000px;
  height: 5000px;
  background-color: #1e1e1e;
  background-image: 
   linear-gradient(rgba(80, 80, 80, 0.3) 1px, transparent 1px),
   linear-gradient(90deg, rgba(80, 80, 80, 0.3) 1px, transparent 1px);
  background-size: 20px 20px;
  transform-origin: 0 0;
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

 .controls {
  position: absolute;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 10;
 }

 .control-btn {
  background-color: #2d2d2d;
  border: 1px solid #404040;
  color: #e0e0e0;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
 }

 .control-btn:hover {
  background-color: #3d3d3d;
 }

 .zoom-level {
  background-color: #2d2d2d;
  border: 1px solid #404040;
  color: #e0e0e0;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
 }
</style>
