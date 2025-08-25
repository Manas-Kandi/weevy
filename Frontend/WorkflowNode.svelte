<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Node } from '../types.js';
	import { Brain, FileInput, FileOutput, BookOpen } from 'lucide-svelte';

	export let node: Node;
	export let selected: boolean = false;

	const dispatch = createEventDispatcher<{
		select: void;
		connectionStart: void;
		connectionEnd: void;
	}>();

	const nodeIcons = {
		brain: Brain,
		input: FileInput,
		output: FileOutput,
		knowledge: BookOpen
	};

	const nodeColors = {
		brain: '#8B5CF6',
		input: '#3B82F6', 
		output: '#10B981',
		knowledge: '#F59E0B'
	};

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		dispatch('select');
	}

	function handleOutputPortClick(e: MouseEvent) {
		e.stopPropagation();
		dispatch('connectionStart');
	}

	function handleInputPortClick(e: MouseEvent) {
		e.stopPropagation();
		dispatch('connectionEnd');
	}
</script>

<div 
	class="workflow-node"
	class:selected
	style="left: {node.position.x}px; top: {node.position.y}px; border-color: {nodeColors[node.type]}"
	on:click={handleClick}
	role="group"
	aria-label={`Workflow node ${node.data.label}`}
>
	<!-- Input Port (Green) -->
	<div 
		class="connection-port input-port"
		on:click={handleInputPortClick}
		title="Connect to this node"
	></div>

	<!-- Node Content -->
	<div class="node-icon" style="color: {nodeColors[node.type]}">
		<svelte:component this={nodeIcons[node.type]} size={24} />
	</div>
	<div class="node-label">{node.data.label}</div>

	<!-- Output Port (Blue) -->
	<div 
		class="connection-port output-port" 
		on:click={handleOutputPortClick}
		title="Create connection from this node"
	></div>
</div>

<style>
	.workflow-node {
		position: absolute;
		width: 120px;
		height: 80px;
		background-color: #2d2d2d;
		border: 2px solid #404040;
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.2s;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
		z-index: 2;
	}

	.workflow-node:hover {
		border-color: #606060;
		transform: scale(1.05);
	}

	.workflow-node.selected {
		border-color: #6b8cff;
		box-shadow: 0 0 0 2px rgba(107, 140, 255, 0.3);
	}

	.node-icon {
		margin-bottom: 8px;
	}

	.node-label {
		font-size: 14px;
		font-weight: 500;
		color: #e0e0e0;
		text-align: center;
	}

	.connection-port {
		position: absolute;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		cursor: pointer;
		top: 50%;
		transform: translateY(-50%);
		z-index: 3;
	}

	.input-port {
		left: -8px;
		background-color: #4CAF50;
	}

	.output-port {
		right: -8px;
		background-color: #2196F3;
	}

	.connection-port:hover {
		transform: translateY(-50%) scale(1.2);
	}
</style>
