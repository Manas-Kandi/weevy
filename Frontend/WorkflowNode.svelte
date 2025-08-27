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
	}>();

	const nodeIcons = {
		brain: Brain,
		input: FileInput,
		output: FileOutput,
		knowledge: BookOpen,
		tool: Wrench
	};

	// Use CSS variables defined globally for consistent theming
	const nodeColors: Record<string, string> = {
		brain: 'var(--acc-brain)',
		input: 'var(--acc-input)', 
		output: 'var(--acc-output)',
		knowledge: 'var(--acc-knowledge)',
		tool: 'var(--acc-tool)'
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

	function handleKeyActivate(e: KeyboardEvent, action: () => void) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			action();
		}
	}
</script>

<div 
	class="workflow-node {node.type}"
	class:selected
	style="left: {node.position.x}px; top: {node.position.y}px; --accent: {nodeColors[node.type]};"
	on:click={handleClick}
	role="button"
	aria-pressed={selected}
	aria-label={`Workflow node ${node.data.label}`}
	tabindex="0"
	on:keydown={(e) => handleKeyActivate(e, () => dispatch('select'))}
>
	<!-- Input Port (Green) -->
	<div 
		class="connection-port input-port"
		on:click={handleInputPortClick}
		title="Connect to this node"
		role="button"
		aria-label="Connect to this node"
		tabindex="0"
		on:keydown={(e) => handleKeyActivate(e, () => dispatch('connectionEnd'))}
	></div>

	<!-- Node Content -->
	<div class="node-icon">
		<svelte:component this={nodeIcons[node.type]} size={24} />
	</div>
	<div class="node-label">{node.data.label}</div>

	<!-- Output Port (Blue) -->
	<div 
		class="connection-port output-port" 
		on:click={handleOutputPortClick}
		title="Create connection from this node"
		role="button"
		aria-label="Create connection from this node"
		tabindex="0"
		on:keydown={(e) => handleKeyActivate(e, () => dispatch('connectionStart'))}
	></div>
</div>

<style>
	.workflow-node {
		position: absolute;
		width: 160px;
		height: 88px;
		background: var(--node-glass);
		border: 1px solid var(--glass-border);
		border-radius: 20px;
		box-shadow: var(--shadow-node);
		backdrop-filter: blur(20px) saturate(180%);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.3s var(--ease-spring);
		overflow: hidden;
	}

	.workflow-node:hover {
		transform: translateY(-4px) scale(1.02);
		box-shadow: 
			var(--shadow-float),
			var(--glow-subtle);
	}

	.workflow-node.selected {
		border-color: rgba(255, 255, 255, 0.4);
		transform: translateY(-2px) scale(1.01);
		box-shadow: 
			0 0 0 3px rgba(255, 255, 255, 0.2),
			var(--shadow-float),
			var(--glow-subtle);
	}

	/* Input nodes are wider to match Canvas connection calculations */
	.workflow-node.input {
		width: 200px;
		height: 120px;
	}

	.node-icon {
		color: var(--text);
		margin-bottom: 8px;
		filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
	}

	.node-label {
		font-size: 12px;
		font-weight: 600;
		color: var(--text);
		text-align: center;
		letter-spacing: 0.2px;
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
		box-shadow: 
			0 4px 12px rgba(0, 0, 0, 0.15),
			0 0 0 2px rgba(255, 255, 255, 0.9) inset;
		backdrop-filter: blur(8px);
		transition: all 0.2s var(--ease-bounce);
	}

	.input-port {
		left: -8px;
		background: var(--grad-input);
	}

	.output-port {
		right: -8px;
		background: var(--accent);
	}

	/* Type-specific output port colors */
	.workflow-node.input .output-port {
		background: var(--grad-input);
	}

	.workflow-node.brain .output-port {
		background: var(--grad-brain);
	}

	.workflow-node.output .output-port {
		background: var(--grad-output);
	}

	.workflow-node.knowledge .output-port {
		background: var(--grad-knowledge);
	}

	.workflow-node.tool .output-port {
		background: var(--grad-tool);
	}

	.connection-port:hover {
		transform: translateY(-50%) scale(1.2);
		box-shadow: 
			0 6px 20px rgba(0, 0, 0, 0.2),
			0 0 0 3px rgba(255, 255, 255, 1) inset,
			0 0 20px rgba(255, 255, 255, 0.8);
	}
</style>
