<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Node } from './types';
	import { Brain, FileInput, FileOutput, BookOpen, Wrench } from 'lucide-svelte';

	export let node: Node;
	export let selected: boolean = false;

	const dispatch = createEventDispatcher<{
		select: void;
		connectionStart: void;
		connectionEnd: void;
		nodestartdrag: { nodeId: string; event: MouseEvent };
	}>();

	const nodeIcons = {
		brain: Brain,
		input: FileInput,
		output: FileOutput,
		knowledge: BookOpen,
		tool: Wrench
	};

	const nodeColors = {
		brain: '#8B5CF6',
		input: '#3B82F6', 
		output: '#10B981',
		knowledge: '#F59E0B',
		tool: '#EF4444'
	};

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
	style="transform: translate({node.position.x}px, {node.position.y}px); border-color: {nodeColors[node.type]}"
    on:mousedown={(event) => {
        event.stopPropagation();
        dispatch('nodestartdrag', { nodeId: node.id, event });
    }}
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
    width: 160px;
    min-height: 88px;
    background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
    border: 1px solid var(--border);
    border-radius: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    cursor: grab;
    transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
    box-shadow: 0 10px 24px rgba(0,0,0,0.25);
    z-index: 2;
    backdrop-filter: blur(10px) saturate(120%);
  }

  .workflow-node:hover {
    border-color: rgba(255,255,255,0.22);
    box-shadow: 0 16px 32px rgba(0,0,0,0.35);
  }

  .workflow-node.selected {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent), 0 10px 26px rgba(0,0,0,0.35);
    cursor: grab;
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
    background: radial-gradient(8px 8px at 50% 50%, var(--success), rgba(16,185,129,0.5));
    box-shadow: 0 0 8px rgba(16,185,129,0.6);
  }

  .output-port {
    right: -8px;
    background: radial-gradient(8px 8px at 50% 50%, var(--running), rgba(59,130,246,0.5));
    box-shadow: 0 0 8px rgba(59,130,246,0.6);
  }

	.connection-port:hover {
		transform: translateY(-50%) scale(1.2);
	}
</style>
