<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Brain, FileInput, FileOutput, BookOpen, Wrench } from 'lucide-svelte';

	const dispatch = createEventDispatcher<{
		nodeAdd: { type: string };
	}>();

	const nodeTypes = [
		{ type: 'brain', label: 'AI Brain', icon: Brain, color: '#8B5CF6' },
		{ type: 'input', label: 'Input', icon: FileInput, color: '#3B82F6' },
		{ type: 'output', label: 'Output', icon: FileOutput, color: '#10B981' },
		{ type: 'knowledge', label: 'Knowledge', icon: BookOpen, color: '#F59E0B' },
		{ type: 'tool', label: 'Tool', icon: Wrench, color: '#EF4444' }
	];

	function handleNodeAdd(type: string) {
		dispatch('nodeAdd', { type });
	}

	function handleKeyAdd(e: KeyboardEvent, type: string) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleNodeAdd(type);
		}
	}
</script>

<div class="components-panel" role="navigation" aria-label="Components panel">
	<h3>Components</h3>
	{#each nodeTypes as nodeType}
		<div 
			class="component" 
			on:click={() => handleNodeAdd(nodeType.type)}
			on:keydown={(e) => handleKeyAdd(e, nodeType.type)}
			role="button"
			aria-label={`Add ${nodeType.label} node`}
			tabindex="0"
		>
			<div class="component-icon" style="color: {nodeType.color}">
				<svelte:component this={nodeType.icon} size={20} />
			</div>
			<div class="component-label">{nodeType.label}</div>
		</div>
	{/each}
</div>

<style>
	.components-panel {
		position: absolute;
		left: 20px;
		top: 50%;
		transform: translateY(-50%);
		background-color: #2d2d2d;
		border: 1px solid #404040;
		border-radius: 8px;
		padding: 16px;
		width: 120px;
		z-index: 10;
	}

	h3 {
		color: #e0e0e0;
		margin: 0 0 12px 0;
		font-size: 16px;
		text-align: center;
	}

	.component {
		background-color: #3d3d3d;
		border: 1px solid #505050;
		border-radius: 6px;
		padding: 12px;
		margin-bottom: 8px;
		text-align: center;
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
	}

	.component:hover {
		background-color: #4d4d4d;
		border-color: #606060;
		transform: scale(1.02);
	}

	.component-label {
		font-size: 12px;
		color: #e0e0e0;
	}
</style>
