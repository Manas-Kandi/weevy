<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Brain, FileInput, FileOutput, BookOpen, Wrench, Plus, Trash2, ChevronLeft, ChevronRight, Play } from 'lucide-svelte';

const dispatch = createEventDispatcher<{
    nodeAdd: { type: string };
    run: void;
    newProject: void;
    selectProject: { id: string };
    deleteProject: { id: string };
    toggleCollapse: void;
}>();

export let projects: Array<{ id: string; name: string; updatedAt?: string }> = [];
export let currentProjectId: string = 'new';
export let collapsed: boolean = false;

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

<div class="sidebar" class:collapsed={collapsed} role="navigation" aria-label="Component Palette">
  <div class="topbar">
    <button class="collapse-btn" aria-label="Toggle sidebar" title="Toggle sidebar"
      on:click={() => dispatch('toggleCollapse')}>
      {#if collapsed}
        <ChevronRight size={16} />
      {:else}
        <ChevronLeft size={16} />
      {/if}
    </button>
  </div>
  <!-- Nodes Section at top -->
  <div class="section">
    <div class="section-title">Nodes</div>
    {#each nodeTypes as nodeType}
      <button 
        class="item" 
        on:click={() => handleNodeAdd(nodeType.type)}
        on:keydown={(e) => handleKeyAdd(e, nodeType.type)}
        aria-label={`Add ${nodeType.label} node`}
      >
        <div class="icon" style="color: {nodeType.color}">
          <svelte:component this={nodeType.icon} size={18} />
        </div>
        <span class="label">{nodeType.label}</span>
      </button>
    {/each}
  </div>
  <div class="divider"></div>
  <div class="projects-header">
    <div class="projects-title">Projects</div>
    <button class="icon-btn" aria-label="New Project" title="New Project" on:click={() => dispatch('newProject')}>
      <Plus size={14} />
    </button>
  </div>
  <div class="projects" aria-label="Projects list">
    {#each projects as p}
      <div class="project-item" on:click={() => dispatch('selectProject', { id: p.id })}>
        <div class="left">
          <span class="name">{p.name}</span>
          {#if p.updatedAt}<span class="meta">{p.updatedAt}</span>{/if}
        </div>
        <button class="del-btn" aria-label="Delete project" title="Delete"
          on:click={(e) => { e.stopPropagation(); dispatch('deleteProject', { id: p.id }); }}>
          <Trash2 size={16} />
        </button>
      </div>
    {/each}
  </div>
  <div class="bottom">
    <button class="run-btn" on:click={() => dispatch('run')}>
      <Play size={14} />
      <span class="label">Run</span>
    </button>
  </div>
</div>

<style>
.sidebar {
  position: fixed; left: 0; top: 0; bottom: 0;
  width: 200px; z-index: 14; padding: 12px;
  background: rgba(8,10,14,0.92);
  border: none; /* no outer borders to avoid double-panel feel */
  border-radius: 0;
  backdrop-filter: blur(8px) saturate(120%);
  display: flex; flex-direction: column;
}
.sidebar.collapsed { width: 56px; padding: 8px; }
.sidebar.collapsed .section-title,
.sidebar.collapsed .label,
.sidebar.collapsed .projects-header,
.sidebar.collapsed .projects,
.sidebar.collapsed .meta { display: none; }
.sidebar.collapsed .item { justify-content: center; padding: 8px; }
.topbar { display:flex; justify-content: flex-end; align-items: center; height: 28px; margin-bottom: 8px; }
.collapse-btn { background: transparent; border: none; color: var(--text); width: 22px; height: 22px; display:flex; align-items:center; justify-content:center; cursor: pointer; }
.top-fixed { display: grid; gap: 6px; padding-bottom: 6px; }
.projects-header { display:flex; align-items:center; justify-content: space-between; padding: 0; margin: 0 0 4px; }
.projects-title { color: rgba(198,204,216,0.82); font-size: 12px; letter-spacing: 0.2px; }
.icon-btn { background: transparent; color: var(--text); border: none; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; padding: 0; cursor: pointer; }
.icon-btn:hover { background: rgba(255,255,255,0.06); }
/* search removed per spec */
.bottom { margin-top: auto; display: flex; }
.run-btn { background: var(--running); color: #fff; border: none; border-radius: 0; padding: 6px 8px; cursor: pointer; font-size: 12px; width: 100%; display:flex; gap:6px; align-items:center; justify-content:center; }
.run-btn:hover { filter: brightness(1.05); }
.section { display: grid; gap: 8px; }
.section-title { color: rgba(198,204,216,0.75); font-size: 12px; letter-spacing: 0.4px; padding: 6px 12px 4px; }
.item { 
  display:flex; gap:10px; align-items:center; width:100%;
  background: rgba(255,255,255,0.02); 
  border:1px solid rgba(255,255,255,0.06);
  color: var(--text); padding:6px 12px; border-radius: 0; cursor:pointer;
}
.item:hover { border-color: rgba(255,255,255,0.18); background: rgba(255,255,255,0.05); }
.icon { width: 22px; height: 22px; display:flex; align-items:center; justify-content:center; }
.divider { margin: 10px 0; height: 1px; background: rgba(255,255,255,0.06); }
.projects { flex: 1; overflow-y: auto; display: grid; gap: 8px; align-content: start; justify-items: stretch; padding: 0 12px 0; }
.project-item { display:flex; justify-content: space-between; align-items:center; background: transparent; color: var(--text); padding: 8px 0; cursor: pointer; font-size: 12px; transition: background-color 120ms ease, color 120ms ease; }
.project-item .left { display:flex; flex-direction: column; gap: 2px; }
.project-item .name { line-height: 1.1; }
.project-item .meta { color: rgba(198,204,216,0.55); font-size: 11px; }
.project-item:hover { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.95); }
.del-btn { opacity: 0; background: transparent; color: rgba(255,255,255,0.7); border: none; width: 22px; height: 22px; display:inline-flex; align-items:center; justify-content:center; cursor: pointer; transition: opacity 120ms ease, background-color 120ms ease; }
.project-item:hover .del-btn { opacity: 1; }
.del-btn:hover { background: rgba(255,255,255,0.06); }
.project-item .meta { color: rgba(198,204,216,0.55); font-size: 11px; }
/* empty state removed: default is 'New Project' selected */
</style>
