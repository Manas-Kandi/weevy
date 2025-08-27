<script lang="ts">
	import { createEventDispatcher } from 'svelte';
    import type { Node } from './types';
    import { Brain, ArrowRightCircle, FileOutput, BookOpen, Wrench } from 'lucide-svelte';
    import InputNode from './InputNode.svelte';

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
        input: ArrowRightCircle,
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
    class:input-variant={node.type === 'input'}
    data-type={node.type}
    style="transform: translate({node.position.x}px, {node.position.y}px); border-color: {nodeColors[node.type]}"
    on:mousedown={(event) => {
        event.stopPropagation();
        dispatch('nodestartdrag', { nodeId: node.id, event });
    }}
    role="group"
    aria-label={`Workflow node ${node.data.label}`}
>
    {#if node.type !== 'input'}
    <!-- Input Port (Green) -->
    <div 
        class="connection-port input-port"
        on:click={handleInputPortClick}
        title="Connect to this node"
    ></div>
    {/if}

    <!-- Node Content -->
    {#if node.type === 'input'}
      <InputNode {node} />
    {:else}
      <div class="node-icon" style="color: {nodeColors[node.type]}">
          <svelte:component this={nodeIcons[node.type]} size={24} />
      </div>
      <div class="node-label">{node.data.label}</div>
    {/if}

    <!-- Output Port (Blue) -->
    <div 
        class="connection-port output-port" 
        class:outside={node.type === 'input'}
        on:click={handleOutputPortClick}
        title={node.type === 'input' ? 'Connect to AI Brain or Tool' : 'Create connection from this node'}
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
    transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    z-index: 2;
    backdrop-filter: blur(10px) saturate(120%);
    font-size: calc(14px * clamp(0.8, 1 / var(--scale, 1), 1.2));
  }

  /* Input variant adopts larger rounded style, neutralizing base flex centering */
  .workflow-node.input-variant {
    width: 200px;
    min-height: 120px;
    border-radius: 8px;
    background: transparent; /* child paints its own full card */
    border-color: transparent;
    box-shadow: none;
    display: block;
  }

  .workflow-node:hover {
    border-color: rgba(255,255,255,0.22);
    box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    transform: scale(1.01);
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
    font-size: calc(16px * clamp(0.8, 1 / var(--scale, 1), 1.2));
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
    background: #10B981; /* green input */
    box-shadow: 0 0 8px rgba(16,185,129,0.5);
  }

  .output-port {
    right: -8px;
    background: #2196F3; /* blue data flow */
    box-shadow: 0 0 8px rgba(33,150,243,0.55);
  }
  .output-port.outside { right: -28px; }
  .output-port.outside::before {
    content: '';
    position: absolute;
    top: 50%;
    left: -20px;
    width: 20px;
    height: 2px;
    background: rgba(33,150,243,0.6);
    transform: translateY(-50%);
    opacity: 0;
    transition: opacity 160ms ease;
  }
  .output-port.outside:hover::before { opacity: 1; }
  .output-port:hover { animation: pulse 1.2s ease-out infinite; }

    .connection-port:hover {
        transform: translateY(-50%) scale(1.2);
    }

  /* Pulse animation for active/hover states */
  
  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(33,150,243, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(33,150,243, 0); }
    100% { box-shadow: 0 0 0 0 rgba(33,150,243, 0); }
  }
  /* Soften selection styling for input variant to avoid thick cyan border */
  .workflow-node.input-variant.selected {
    border-color: transparent;
    box-shadow: 0 8px 20px rgba(0,0,0,0.3);
  }
</style>
