<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Brain, Database, Puzzle, ArrowRight, ArrowDown, Play, Wrench, ChevronLeft, ChevronRight, Trash2, X, Search, Zap, FileInput, FileOutput } from 'lucide-svelte';

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

let searchQuery: string = '';
let searchFocused: boolean = false;

	const nodeCategories = [
		{
			title: 'REASONING',
			nodes: [
				{ 
					type: 'brain', 
					label: 'AI Brain', 
					description: 'Advanced language models\nContext-aware decision making',
					icon: Brain
				}
			]
		},
		{
			title: 'INPUT/OUTPUT',
			nodes: [
				{ 
					type: 'input', 
					label: 'Input', 
					description: 'Data ingestion and preprocessing',
					icon: FileInput
				},
				{ 
					type: 'output', 
					label: 'Output', 
					description: 'Results formatting and delivery',
					icon: FileOutput
				}
			]
		},
		{
			title: 'KNOWLEDGE',
			nodes: [
				{ 
					type: 'knowledge', 
					label: 'Knowledge', 
					description: 'Document parsing and retrieval\nSemantic search capabilities',
					icon: Database
				}
			]
		},
		{
			title: 'UTILITIES',
			nodes: [
				{ 
					type: 'tool', 
					label: 'Tool', 
					description: 'Custom logic and transformations',
					icon: Wrench
				},
				{ 
					type: 'externalApp', 
					label: 'External App', 
					description: 'Integrate with external services\nRead/write data from apps',
					icon: Puzzle
				}
			]
		}
	];

	$: filteredCategories = nodeCategories.map(category => ({
		...category,
		nodes: category.nodes.filter(node => 
			node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
			node.description.toLowerCase().includes(searchQuery.toLowerCase())
		)
	})).filter(category => category.nodes.length > 0);

	// Helper function to get current project name
	$: currentProject = projects.find(p => p.id === currentProjectId);
	
	// Helper function to get readable time ago
	function getTimeAgo(updatedAt?: string): string {
		if (!updatedAt) return 'Just created';
		const now = new Date();
		const updated = new Date(updatedAt);
		const diffMs = now.getTime() - updated.getTime();
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		
		if (diffHours < 1) return 'Modified now';
		if (diffHours === 1) return 'Modified 1 hour ago';
		return `Modified ${diffHours} hours ago`;
	}

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

<div class="sidebar" class:collapsed={collapsed} role="navigation" aria-label="Node Library">
  <!-- Collapse Button -->
  <button class="collapse-btn" on:click={() => collapsed = !collapsed} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
    {#if collapsed}
      <ChevronRight size={14} />
    {:else}
      <ChevronLeft size={14} />
    {/if}
  </button>

  <!-- Current Project -->
  {#if currentProject && !collapsed}
    <div class="project-info">
      <div class="project-title">{currentProject.name}</div>
      <div class="project-meta">{getTimeAgo(currentProject.updatedAt)}</div>
    </div>
  {/if}

  <!-- Node Library -->
  <div class="node-library">
    {#each filteredCategories as category}
      {#each category.nodes as node}
        <button 
          class="node-item"
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
  .sidebar {
    position: fixed; left: 20px; top: 20px; bottom: 20px;
    width: 240px; z-index: 14; 
    background: white;
    border: 1px solid #E8E8E8;
    display: flex; flex-direction: column;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    transition: width 300ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }


  /* Current Project */
  .project-info {
    padding: 16px;
    border-bottom: 1px solid #F8F8F8;
  }
  
  .project-title {
    font-size: 16px; 
    font-weight: 700;
    color: #1A1A1A;
    margin-bottom: 4px;
  }
  
  .project-meta {
    font-size: 12px;
    font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
    color: #6B7280;
    opacity: 0.6;
  }


  /* Node Library */
  .node-library {
    flex: 1;
    overflow-y: auto;
    padding: 0;
    margin-top: 8px;
  }

  .sidebar.collapsed .node-library {
    margin-top: 40px;
  }


  .node-item {
    width: 100%;
    padding: 10px 16px;
    background: transparent;
    border: none;
    border-left: 4px solid transparent;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    text-align: left;
    transition: border-left-color 150ms ease;
  }

  .node-item:hover {
    border-left-color: #2563EB;
  }

  .node-item:hover .node-label {
    font-weight: 600;
  }

  .node-icon {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #9CA3AF;
    flex-shrink: 0;
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* Unique hover animations for each node type */
  .node-item[data-node-type="brain"]:hover .node-icon {
    color: #8B5CF6;
    transform: scale(1.1) rotate(5deg);
    filter: drop-shadow(0 0 8px rgba(139, 92, 246, 0.4));
  }

  .node-item[data-node-type="input"]:hover .node-icon {
    color: #10B981;
    transform: scale(1.1) translateY(-2px);
    filter: drop-shadow(0 0 8px rgba(16, 185, 129, 0.4));
  }

  .node-item[data-node-type="output"]:hover .node-icon {
    color: #F59E0B;
    transform: scale(1.1) translateX(2px);
    filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.4));
  }

  .node-item[data-node-type="database"]:hover .node-icon {
    color: #3B82F6;
    transform: scale(1.1);
    filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.4));
    animation: database-pulse 600ms ease-in-out;
  }

  .node-item[data-node-type="tool"]:hover .node-icon {
    color: #EF4444;
    transform: scale(1.1) rotate(-5deg);
    filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.4));
  }

  .node-item[data-node-type="webhook"]:hover .node-icon {
    color: #06B6D4;
    transform: scale(1.1);
    filter: drop-shadow(0 0 8px rgba(6, 182, 212, 0.4));
    animation: webhook-bounce 400ms ease-out;
  }

  .node-item[data-node-type="condition"]:hover .node-icon {
    color: #8B5CF6;
    transform: scale(1.1);
    filter: drop-shadow(0 0 8px rgba(139, 92, 246, 0.4));
    animation: condition-shake 300ms ease-in-out;
  }

  .node-item[data-node-type="loop"]:hover .node-icon {
    color: #F97316;
    transform: scale(1.1);
    filter: drop-shadow(0 0 8px rgba(249, 115, 22, 0.4));
    animation: loop-spin 500ms ease-in-out;
  }

  @keyframes database-pulse {
    0%, 100% { transform: scale(1.1); }
    50% { transform: scale(1.2); }
  }

  @keyframes webhook-bounce {
    0%, 100% { transform: scale(1.1) translateY(0); }
    50% { transform: scale(1.15) translateY(-3px); }
  }

  @keyframes condition-shake {
    0%, 100% { transform: scale(1.1) translateX(0); }
    25% { transform: scale(1.1) translateX(-1px); }
    75% { transform: scale(1.1) translateX(1px); }
  }

  @keyframes loop-spin {
    0% { transform: scale(1.1) rotate(0deg); }
    100% { transform: scale(1.1) rotate(180deg); }
  }

  /* Additional node types */
  .node-item[data-node-type="knowledge"]:hover .node-icon {
    color: #3B82F6;
    transform: scale(1.1);
    filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.4));
    animation: knowledge-glow 800ms ease-in-out;
  }

  .node-item[data-node-type="externalApp"]:hover .node-icon {
    color: #8B5CF6;
    transform: scale(1.1) rotate(10deg);
    filter: drop-shadow(0 0 8px rgba(139, 92, 246, 0.4));
    animation: apps-wiggle 500ms ease-in-out;
  }

  .node-item[data-node-type="puzzle"]:hover .node-icon {
    color: #8B5CF6;
    transform: scale(1.1) rotate(10deg);
    filter: drop-shadow(0 0 8px rgba(139, 92, 246, 0.4));
    animation: apps-wiggle 500ms ease-in-out;
  }

  @keyframes knowledge-glow {
    0%, 100% { 
      transform: scale(1.1);
      filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.4));
    }
    50% { 
      transform: scale(1.15);
      filter: drop-shadow(0 0 12px rgba(59, 130, 246, 0.6));
    }
  }

  @keyframes apps-wiggle {
    0%, 100% { transform: scale(1.1) rotate(10deg); }
    25% { transform: scale(1.1) rotate(5deg); }
    75% { transform: scale(1.1) rotate(15deg); }
  }

  .node-label {
    font-size: 14px;
    font-weight: 500;
    color: #1A1A1A;
    line-height: 1.3;
    transition: font-weight 150ms ease;
  }

  /* Collapse Button */
  .collapse-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 24px;
    height: 24px;
    background: transparent;
    border: 1px solid #E8E8E8;
    border-radius: 4px;
    color: #6B7280;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 150ms ease;
    z-index: 15;
  }

  .sidebar {
    width: 240px;
    height: 100vh;
    background: white;
    border-right: 1px solid #E8E8E8;
    padding: 0;
    flex-shrink: 0;
    overflow-y: auto;
    transition: width 200ms ease;
    font-family: 'Inter', sans-serif;
    position: fixed;
    top: 0;
    left: 0;
    z-index: 10;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  }

  .sidebar.collapsed .collapse-btn {
    top: 8px;
    right: 6px;
  }

  .collapse-btn:hover {
    background: #F8FAFC;
    color: #1A1A1A;
  }

  .sidebar.collapsed {
    width: 60px;
  }

  .sidebar.collapsed .project-info,
  .sidebar.collapsed .node-label {
    display: none;
  }

  .sidebar.collapsed .node-item {
    justify-content: center;
    padding: 12px 8px;
    position: relative;
  }

  .sidebar.collapsed .node-item:hover::after {
    content: attr(aria-label);
    position: absolute;
    left: calc(100% + 8px);
    top: 50%;
    transform: translateY(-50%);
    background: #1A1A1A;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    white-space: nowrap;
    z-index: 20;
    pointer-events: none;
  }

  @media (prefers-reduced-motion: reduce) {
    * {
      transition: none !important;
    }
  }
</style>
