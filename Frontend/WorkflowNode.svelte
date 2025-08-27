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
	let titleEl: HTMLTextAreaElement;
	let descEl: HTMLTextAreaElement;

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

	function handleOutputPortClick(e: MouseEvent) {
		e.stopPropagation();
		dispatch('connectionStart');
	}

	function handleInputPortClick(e: MouseEvent) {
		e.stopPropagation();
		dispatch('connectionEnd');
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
	on:mouseenter={() => hovering = true}
	on:mouseleave={() => hovering = false}
	role="button"
	aria-pressed={selected}
	aria-label={`${nodeTypeLabels[node.type]} ${node.data.label}`}
	tabindex="0"
	on:keydown={(e) => handleKeyActivate(e, () => dispatch('select'))}
	in:scale={{ duration: 600, easing: elasticOut, start: 0.8 }}
>
	<!-- Input Port -->
	<div 
		class="connection-port input-port"
		on:click={handleInputPortClick}
		title="Connect to this node"
		role="button"
		aria-label="Connect to this node"
		tabindex="0"
		on:keydown={(e) => handleKeyActivate(e, () => dispatch('connectionEnd'))}
	></div>

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

	<!-- Output Port -->
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

	.connection-port {
		position: absolute;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		cursor: pointer;
		top: 50%;
		transform: translateY(-50%);
		z-index: 10;
		box-shadow: 
			0 4px 16px rgba(0, 0, 0, 0.12),
			0 0 0 3px rgba(255, 255, 255, 0.95) inset;
		backdrop-filter: blur(8px);
		transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
	}

	.input-port {
		left: -10px;
		background: linear-gradient(135deg, #10B981 0%, #34D399 100%);
	}

	.output-port {
		right: -10px;
		background: var(--accent-color);
	}

	.connection-port:hover {
		transform: translateY(-50%) scale(1.3);
		box-shadow: 
			0 8px 24px rgba(0, 0, 0, 0.2),
			0 0 0 4px rgba(255, 255, 255, 1) inset,
			0 0 20px rgba(255, 255, 255, 0.9);
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
</style>
