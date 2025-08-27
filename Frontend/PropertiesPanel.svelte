<script lang="ts">
  import type { Node } from './types';
  import ToolConfigPanel from './ToolConfigPanel.svelte';
  export let node: Node | null = null;
  export let open: boolean = true;
  export let onUpdate: (conf: Record<string, any>) => void;

  function handleToolUpdate(e: CustomEvent<{ configuration: Record<string, any> }>) {
    onUpdate?.(e.detail.configuration);
  }
</script>

{#if open}
  <aside class="panel" aria-label="Properties Panel">
    <header>
      <div class="title">Properties</div>
    </header>
    {#if node}
      <section class="content">
        <div class="meta">
          <div class="label">{node.data.label}</div>
          <div class="sub">ID: {node.id} • Type: {node.type}</div>
        </div>
        {#if node.type === 'tool'}
          <ToolConfigPanel node={node} on:updateConfig={handleToolUpdate} />
        {:else}
          <div class="placeholder">
            <div class="heading">Configuration</div>
            <div class="muted">No editor yet for this node type.</div>
          </div>
        {/if}
      </section>
    {:else}
      <section class="empty">Select a node to edit its properties.</section>
    {/if}
  </aside>
{/if}

<style>
  .panel {
    position: absolute;
    top: 0;
    right: 20px;
    width: 380px;
    height: 100vh;
    background: var(--glass);
    border: 1px solid var(--border);
    border-radius: 0;
    backdrop-filter: blur(16px) saturate(120%);
    box-shadow: none;
    overflow: hidden;
    z-index: 20;
    display: flex;
    flex-direction: column;
  }
  header { padding: 14px 16px; border-bottom: 1px solid var(--border); }
  .title { font-weight: 600; letter-spacing: 0.2px; }
  .content { padding: 12px 12px 16px; overflow-y: auto; }
  .meta { padding: 8px 10px 12px; border: 1px solid var(--border); border-radius: 0; background: rgba(255,255,255,0.04); margin-bottom: 12px; }
  .label { font-weight: 600; }
  .sub { color: var(--muted); font-size: 12px; margin-top: 4px; }
  .placeholder { display: grid; gap: 6px; padding: 8px; }
  .heading { font-size: 13px; font-weight: 600; }
  .muted { color: var(--muted); font-size: 12px; }
  .empty { padding: 16px; color: var(--muted); }
</style>
