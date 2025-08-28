<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Brain, Database, Puzzle, ChevronLeft, ChevronRight, Search, Wrench, FileInput, FileOutput } from 'lucide-svelte';

	const dispatch = createEventDispatcher<{
		nodeAdd: { type: string };
		run: void;
		newProject: void;
		selectProject: { id: string };
		deleteProject: { id: string };
		toggleCollapse: void;
		updateProjectName: { id: string; name: string };
	}>();

	export let projects: Array<{ id: string; name: string; updatedAt?: string }> = [];
	export let currentProjectId: string = 'new';
	export let collapsed: boolean = false;

	let searchQuery = '';
	let editingProjectName = false;
	let editingNameValue = '';

	const nodeCategories = [
		{ title: 'REASONING', nodes: [{ type: 'brain', label: 'AI Brain', description: 'Advanced language models\nContext-aware decision making', icon: Brain }] },
		{ title: 'INPUT/OUTPUT', nodes: [
			{ type: 'input', label: 'Input', description: 'Data ingestion and preprocessing', icon: FileInput },
			{ type: 'output', label: 'Output', description: 'Results formatting and delivery', icon: FileOutput }
		]},
		{ title: 'KNOWLEDGE', nodes: [{ type: 'knowledge', label: 'Knowledge', description: 'Document parsing and retrieval\nSemantic search capabilities', icon: Database }] },
		{ title: 'UTILITIES', nodes: [
			{ type: 'tool', label: 'Tool', description: 'Custom logic and transformations', icon: Wrench },
			{ type: 'externalApp', label: 'External App', description: 'Integrate with external services\nRead/write data from apps', icon: Puzzle }
		]}
	];

	$: filteredCategories = nodeCategories
		.map(c => ({ ...c, nodes: c.nodes.filter(n =>
			n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
			n.description.toLowerCase().includes(searchQuery.toLowerCase())
		)}))
		.filter(c => c.nodes.length > 0);

	$: currentProject = projects.find(p => p.id === currentProjectId);

	function getTimeAgo(updatedAt?: string) {
		if (!updatedAt) return 'Just created';
		const diffHours = Math.floor((Date.now() - new Date(updatedAt).getTime()) / 36e5);
		if (diffHours < 1) return 'Modified now';
		if (diffHours === 1) return 'Modified 1 hour ago';
		return `Modified ${diffHours} hours ago`;
	}

	function handleNodeAdd(type: string) { dispatch('nodeAdd', { type }); }
	function handleKeyAdd(e: KeyboardEvent, type: string) {
		if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleNodeAdd(type); }
	}

	function startEditingProjectName() {
		if (currentProject) { editingProjectName = true; editingNameValue = currentProject.name; }
	}
	function saveProjectName() {
		if (currentProject && editingNameValue.trim()) {
			projects = projects.map(p => p.id === currentProject.id ? { ...p, name: editingNameValue.trim() } : p);
			dispatch('updateProjectName', { id: currentProject.id, name: editingNameValue.trim() });
		}
		editingProjectName = false;
	}
	function cancelEditingProjectName() { editingProjectName = false; editingNameValue = ''; }
	function handleProjectNameKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') { e.preventDefault(); saveProjectName(); }
		else if (e.key === 'Escape') { e.preventDefault(); cancelEditingProjectName(); }
	}
</script>

<div class="sidebar" class:collapsed={collapsed} role="navigation" aria-label="Node Library">
	<button class="collapse-btn" on:click={() => (collapsed = !collapsed)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
		{#if collapsed}<ChevronRight size={14} />{:else}<ChevronLeft size={14} />{/if}
	</button>

	{#if currentProject && !collapsed}
		<div class="project-info">
			{#if editingProjectName}
				<input
					type="text"
					class="project-title-input"
					bind:value={editingNameValue}
					on:keydown={handleProjectNameKeydown}
					on:blur={saveProjectName}
					placeholder="Project name"
					maxlength="50"
					autofocus
				/>
			{:else}
				<button class="project-title-button" on:click={startEditingProjectName} title="Click to edit project name">
					{currentProject.name}
				</button>
			{/if}
			<div class="project-meta">{getTimeAgo(currentProject.updatedAt)}</div>
		</div>

		<!-- keep search simple + non-sticky to avoid layout quirks -->
		<div class="search">
			<span aria-hidden="true"><Search size={14} class="search-icon" /></span>
			<input
				type="text"
				class="search-input"
				placeholder="Search nodes…"
				aria-label="Search nodes"
				bind:value={searchQuery}
			/>
		</div>
	{/if}

	<div class="node-library">
		{#each filteredCategories as category}
			{#if !collapsed}<div class="category-title">{category.title}</div>{/if}
			{#each category.nodes as node}
				<button
					class="node-item"
					title={node.label}
					data-node-type={node.type}
					on:click={() => handleNodeAdd(node.type)}
					on:keydown={(e) => handleKeyAdd(e, node.type)}
					aria-label={`Add ${node.label} node`}
				>
					<div class="node-icon">
						<svelte:component this={node.icon} size={16} />
					</div>
					<div class="node-label">{node.label}</div>
				</button>
			{/each}
		{/each}
	</div>
</div>

<style>
	/* system tokens */
	:root{
		--bg:#fff;
		--surface:#f8fafc;
		--ink:#111827;
		--ink-2:#4b5563;
		--ink-3:#9ca3af;
		--border:#e5e7eb;
		--accent:#2563eb; /* easy to theme later */
	}

	*,*::before,*::after{ box-sizing:border-box; }

	.sidebar{
		position:fixed; top:0; left:0;
		height:100vh; width:240px;
		background:var(--bg);
		border-right:1px solid var(--border);
		box-shadow:0 2px 16px rgba(0,0,0,.06);
		font-family:Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		overflow-y:auto; overflow-x:hidden;   /* 🔒 no horizontal scroll */
		transition:width .18s ease;
		z-index:10;
		-webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
	}

	.project-info{
		position:sticky; top:0;
		padding:16px; background:var(--bg);
		border-bottom:1px solid #f3f4f6; z-index:1;
	}

	.project-title-button{
		background:none; border:none;
		padding:4px 6px;
		font-size:16px; font-weight:700; color:var(--ink);
		width:100%; text-align:left;
		border-radius:6px;
		white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
		transition:background .15s ease, color .15s ease;
	}
	.project-title-button:hover{ background:#f3f4f6; color:var(--ink); } /* calmer hover */
	.project-title-input{
		background:#f9fbff; border:1px solid rgba(37,99,235,.25);
		border-radius:6px; padding:6px 8px; font-size:16px; font-weight:700; color:var(--ink);
		width:100%; outline:none;
	}
	.project-title-input:focus{ box-shadow:0 0 0 2px rgba(37,99,235,.18); }

	.project-meta{
		font-size:12px; color:var(--ink-3);
		font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
	}

	.search{
		display:flex; align-items:center; gap:6px;
		margin:8px 12px 6px; padding:6px 8px;
		border:1px solid var(--border); border-radius:8px; background:#fcfdff;
	}
	.search:focus-within{ border-color:#d1e0ff; box-shadow:0 0 0 2px rgba(37,99,235,.10); }
	.search-icon{ color:var(--ink-3); }
	.search-input{ flex:1; border:none; outline:none; background:transparent; font:inherit; font-size:13px; color:var(--ink); }

	.node-library{ padding:8px 0 12px; }
	.category-title{
		font-size:11px; font-weight:700; letter-spacing:.06em; color:var(--ink-3);
		padding:12px 16px 6px;
	}

	.node-item{
		width:100%;
		display:flex; align-items:center; gap:12px;
		padding:10px 12px;
		margin:2px 8px;
		background:transparent; border:none;
		border-left:3px solid transparent; border-radius:8px;
		cursor:pointer; text-align:left;
		transition:background .12s ease, border-left-color .12s ease;
	}
	/* ✨ minimal, professional hover */
	.node-item:hover{ background:#f6f7f9; border-left-color:#d1d5db; }
	.node-item:focus-visible{ outline:none; box-shadow:0 0 0 2px rgba(37,99,235,.18); }
	.node-icon{ width:16px; height:16px; display:flex; align-items:center; justify-content:center; color:var(--ink-3); }
	.node-label{ font-size:14px; font-weight:500; color:var(--ink); }

	/* remove flashy per-type animations for a calmer feel */
	/* (Intentionally no transforms/drop-shadows on hover) */

	.collapse-btn{
		position:absolute; top:8px; right:8px; width:24px; height:24px;
		background:transparent; border:1px solid var(--border); border-radius:6px;
		color:#6b7280; display:flex; align-items:center; justify-content:center;
		cursor:pointer; transition:background .12s ease, box-shadow .12s ease;
		z-index:15;
	}
	.collapse-btn:hover{ background:#f3f4f6; }
	.collapse-btn:focus-visible{ outline:none; box-shadow:0 0 0 2px rgba(37,99,235,.18); }

	.sidebar.collapsed{ width:60px; }
	.sidebar.collapsed .project-info,
	.sidebar.collapsed .node-label,
	.sidebar.collapsed .search,
	.sidebar.collapsed .category-title{ display:none; }

	.sidebar.collapsed .node-library{ margin-top:40px; }

	.sidebar.collapsed .node-item{
		justify-content:center; padding:12px 8px; margin:4px 6px;
	}

	/* 🔕 remove custom tooltip that could create horizontal overflow */
	/* (Native title= handles hints; overflow-x is hidden.) */

	@media (prefers-reduced-motion: reduce){ *{ transition:none !important; } }
</style>
