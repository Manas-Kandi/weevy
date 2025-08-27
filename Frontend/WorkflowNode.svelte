<script lang="ts">
	import { createEventDispatcher, tick, onMount } from 'svelte';
	import type { Node } from './types';
	import { Brain, FileInput, FileOutput, BookOpen, Wrench, Sparkles, Zap, Database } from 'lucide-svelte';
	import { scale, fly } from 'svelte/transition';
	import { elasticOut, cubicInOut } from 'svelte/easing';

	export let node: Node;
	export let selected: boolean = false;

	let focused = false;
	let hovering = false;
	let showInputPort = false;
	let showOutputPort = false;
	let titleEl: HTMLTextAreaElement;
	let descEl: HTMLTextAreaElement;

	const dispatch = createEventDispatcher<{
		select: void;
		connectionStart: { nodeId: string; port: 'output' };
		connectionEnd: { nodeId: string; port: 'input' };
		nodestartdrag: { nodeId: string; event: MouseEvent };
		delete: { nodeId: string };
	}>();

	const nodeIcons = {
		brain: Brain,
		input: FileInput,
		output: FileOutput,
		knowledge: BookOpen,
		tool: Wrench
	};

	const nodeAnimationIcons = {
		brain: Zap,
		input: Sparkles,
		output: Sparkles,
		knowledge: Database,
		tool: Wrench
	};

	const nodeColors: Record<string, string> = {
		brain: '#8B5CF6',
		input: '#3B82F6', 
		output: '#10B981',
		knowledge: '#6366F1',
		tool: '#F59E0B'
	};

	const nodeTypeLabels: Record<string, string> = {
		brain: 'AI Brain Node',
		input: 'Input Node',
		output: 'Output Node',
		knowledge: 'Knowledge Node',
		tool: 'Tool Node'
	};

	const defaultTitles: Record<string, string> = {
		brain: 'Descriptive title of the thinking',
		input: 'Descriptive title of the input',
		output: 'Descriptive title of the output',
		knowledge: 'Descriptive title of the knowledge',
		tool: 'Descriptive title of the tool'
	};

	const defaultDescriptions: Record<string, string> = {
		brain: 'In the neural pathways of artificial intelligence, thoughts crystallize into actionable insights, bridging human creativity with computational power.',
		input: 'Through the gateway of information, data flows like streams converging into rivers, carrying the essence of external reality into our digital realm.',
		output: 'At the convergence of processing and presentation, refined insights emerge, transformed and ready to impact the world beyond our computational boundaries.',
		knowledge: 'Within the repository of understanding, wisdom accumulates like sediment in an ancient library, each piece building upon centuries of collective insight.',
		tool: 'Through the mechanism of automation, human intention manifests as precise action, extending our capabilities beyond the limits of manual intervention.'
	};

	// Initialize configuration
	const conf = (node.data.configuration ||= {} as any);
	conf.description ||= defaultDescriptions[node.type] || 'Describe the purpose and function of this node in natural language...';

	function autoresize(el: HTMLTextAreaElement) {
		if (!el) return;
		el.style.height = 'auto';
		el.style.height = `${Math.max(el.scrollHeight, 48)}px`;
	}

	function handleResize(event: Event) {
		const el = event.currentTarget as HTMLTextAreaElement;
		if (el) autoresize(el);
	}

	async function initResize() {
		await tick();
		if (titleEl) autoresize(titleEl);
		if (descEl) autoresize(descEl);
	}

	onMount(() => {
		initResize();
	});

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		dispatch('select');
	}

	function handleMouseDown(e: MouseEvent) {
		// Only start drag if not clicking on input elements or connection ports
		const target = e.target as Element;
		if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' || target.closest('.connection-port')) {
			return;
		}
		
		e.stopPropagation();
		dispatch('nodestartdrag', { nodeId: node.id, event: e });
	}

	function handleOutputPortMouseDown(e: MouseEvent) {
		e.stopPropagation();
		dispatch('connectionStart', { nodeId: node.id, port: 'output' });
	}

	function handleInputPortMouseDown(e: MouseEvent) {
		e.stopPropagation();
		dispatch('connectionEnd', { nodeId: node.id, port: 'input' });
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Delete' || e.key === 'Backspace') {
			e.preventDefault();
			dispatch('delete', { nodeId: node.id });
		}
	}

	function handleTitleFocus() {
		focused = true;
		if (!node.data.label || node.data.label.trim() === '') {
			node.data.label = '';
		}
	}

	function handleDescriptionFocus() {
		focused = true;
		if (conf.description === defaultDescriptions[node.type]) {
			conf.description = '';
		}
	}

	function handleKeyActivate(e: KeyboardEvent, action: () => void) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			action();
		}
	}
</script>

<div 
	class="pocket-note {node.type}"
	class:selected
	class:focused
	class:hovering
	style="left: {node.position.x}px; top: {node.position.y}px; --accent-color: {nodeColors[node.type]};"
	on:click={handleClick}
	on:mousedown={handleMouseDown}
	on:mouseenter={() => hovering = true}
	on:mouseleave={() => hovering = false}
	role="button"
	aria-pressed={selected}
	aria-label={`${nodeTypeLabels[node.type]} ${node.data.label}`}
	tabindex="0"
	on:keydown={handleKeyDown}
	in:scale={{ duration: 600, easing: elasticOut, start: 0.8 }}
>
	<!-- Input Port Area - invisible hover zone -->
	<div 
		class="port-hover-zone input-zone"
		on:mouseenter={() => showInputPort = true}
		on:mouseleave={() => showInputPort = false}
		role="button"
		aria-label="Input connection area"
		tabindex="-1"
	>
		{#if showInputPort || hovering}
			<div 
				class="connection-port input-port"
				on:mousedown={handleInputPortMouseDown}
				title="Connect to this node"
				role="button"
				aria-label="Connect to this node"
				tabindex="0"
				in:scale={{ duration: 200, start: 0.3 }}
			></div>
		{/if}
	</div>

	<!-- Floating animation icon -->
	{#if hovering}
		<div class="animation-icon" in:fly={{ y: -20, duration: 400, easing: cubicInOut }}>
			<svelte:component this={nodeAnimationIcons[node.type]} size={16} />
		</div>
	{/if}
	
	<div class="node-type">
		<svelte:component this={nodeIcons[node.type]} size={14} /> {nodeTypeLabels[node.type]}
	</div>
	
	<textarea
		bind:this={titleEl}
		class="title"
		placeholder={defaultTitles[node.type]}
		bind:value={node.data.label}
		on:mousedown|stopPropagation
		on:focus={handleTitleFocus}
		on:blur={() => focused = false}
		on:input={handleResize}
		rows="1"
	/>
	
	<textarea
		bind:this={descEl}
		class="description"
		placeholder="Describe what this node does in natural language..."
		bind:value={conf.description}
		on:mousedown|stopPropagation
		on:focus={handleDescriptionFocus}
		on:blur={() => focused = false}
		on:input={handleResize}
		rows="3"
	/>

	<!-- Output Port Area - invisible hover zone -->
	<div 
		class="port-hover-zone output-zone"
		on:mouseenter={() => showOutputPort = true}
		on:mouseleave={() => showOutputPort = false}
		role="button"
		aria-label="Output connection area"
		tabindex="-1"
	>
		{#if showOutputPort || hovering}
			<div 
				class="connection-port output-port"
				on:mousedown={handleOutputPortMouseDown}
				title="Create connection from this node"
				role="button"
				aria-label="Create connection from this node"
				tabindex="0"
				in:scale={{ duration: 200, start: 0.3 }}
			></div>
		{/if}
	</div>
</div>

<style>
	.pocket-note {
		position: absolute;
		width: 320px;
		min-height: 240px;
		background: linear-gradient(135deg, #FFFFFF 0%, #FEFEFE 100%);
		border: 1px solid rgba(0, 0, 0, 0.06);
		border-radius: 24px;
		padding: 32px;
		box-shadow: 
			0 4px 32px rgba(0, 0, 0, 0.04),
			0 1px 2px rgba(0, 0, 0, 0.02);
		cursor: pointer;
		transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
		overflow: hidden;
	}

	.pocket-note:hover {
		transform: translateY(-8px) scale(1.02);
		box-shadow: 
			0 16px 64px rgba(0, 0, 0, 0.08),
			0 4px 16px rgba(0, 0, 0, 0.04);
		border-color: color-mix(in oklch, var(--accent-color) 15%, transparent);
	}

	.pocket-note.focused {
		transform: translateY(-4px) scale(1.01);
		box-shadow: 
			0 12px 48px color-mix(in oklch, var(--accent-color) 8%, transparent),
			0 0 0 3px color-mix(in oklch, var(--accent-color) 10%, transparent);
		border-color: color-mix(in oklch, var(--accent-color) 20%, transparent);
	}

	.pocket-note.selected {
		box-shadow: 
			0 0 0 3px color-mix(in oklch, var(--accent-color) 15%, transparent),
			0 12px 48px rgba(0, 0, 0, 0.08);
		border-color: color-mix(in oklch, var(--accent-color) 25%, transparent);
		transform: translateY(-4px) scale(1.01);
	}

	.animation-icon {
		position: absolute;
		top: 16px;
		right: 16px;
		color: var(--accent-color);
		opacity: 0.6;
		animation: float 3s ease-in-out infinite;
	}

	@keyframes float {
		0%, 100% { transform: translateY(0) rotate(0deg); }
		33% { transform: translateY(-4px) rotate(2deg); }
		66% { transform: translateY(-2px) rotate(-1deg); }
	}

	.node-type {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		font-weight: 500;
		color: var(--accent-color);
		margin-bottom: 20px;
		letter-spacing: 0.2px;
		opacity: 0.8;
	}

	.title {
		width: 100%;
		background: transparent;
		border: none;
		outline: none;
		font-size: 36px;
		font-weight: 300;
		color: #E5E5E5;
		line-height: 1.2;
		margin-bottom: 20px;
		resize: none;
		overflow: hidden;
		font-family: inherit;
		transition: all 0.3s ease;
	}

	.title:focus,
	.title:not(:placeholder-shown) {
		color: #1F2937;
	}

	.title::placeholder {
		color: #E5E5E5;
	}

	.description {
		width: 100%;
		background: transparent;
		border: none;
		outline: none;
		font-size: 16px;
		font-weight: 400;
		color: #6B7280;
		line-height: 1.6;
		resize: none;
		overflow: hidden;
		font-family: inherit;
		min-height: 80px;
		transition: all 0.3s ease;
	}

	.description:focus {
		color: #374151;
	}

	.description::placeholder {
		color: #D1D5DB;
	}

	.port-hover-zone {
		position: absolute;
		width: 60px;
		height: 80px;
		top: 50%;
		transform: translateY(-50%);
		z-index: 5;
		/* Invisible hover zone */
	}

	.input-zone {
		left: -50px;
	}

	.output-zone {
		right: -50px;
	}

	.connection-port {
		position: absolute;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		cursor: pointer;
		top: 50%;
		transform: translateY(-50%);
		z-index: 15;
		box-shadow: 
			0 4px 12px rgba(0, 0, 0, 0.15),
			0 0 0 2px rgba(255, 255, 255, 1) inset;
		backdrop-filter: blur(8px);
		transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
	}

	.input-port {
		left: 22px;
		background: linear-gradient(135deg, #10B981 0%, #34D399 100%);
	}

	.output-port {
		right: 22px;
		background: var(--accent-color);
	}

	.connection-port:hover {
		transform: translateY(-50%) scale(1.4);
		box-shadow: 
			0 6px 20px rgba(0, 0, 0, 0.25),
			0 0 0 3px rgba(255, 255, 255, 1) inset,
			0 0 16px color-mix(in oklch, var(--accent-color) 30%, transparent);
	}

	/* Node type specific hover animations */
	.pocket-note.hovering .title {
		transform: translateY(-2px);
	}

	.pocket-note.hovering .description {
		transform: translateY(-1px);
	}

	/* Brain node pulse effect */
	.pocket-note.brain.hovering {
		animation: brainPulse 2s ease-in-out infinite;
	}

	@keyframes brainPulse {
		0%, 100% { box-shadow: 0 16px 64px rgba(0, 0, 0, 0.08), 0 4px 16px rgba(0, 0, 0, 0.04); }
		50% { box-shadow: 0 16px 64px rgba(139, 92, 246, 0.1), 0 4px 16px rgba(139, 92, 246, 0.06); }
	}

	/* Delete button area */
	.pocket-note.selected::after {
		content: '×';
		position: absolute;
		top: -8px;
		right: -8px;
		width: 24px;
		height: 24px;
		background: #EF4444;
		color: white;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 16px;
		font-weight: 600;
		cursor: pointer;
		box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
		transition: all 0.2s ease;
		z-index: 20;
	}

	.pocket-note.selected:hover::after {
		transform: scale(1.1);
		box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
	}
</style>
