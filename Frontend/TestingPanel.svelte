<script lang="ts">
  import type { ExecutionUpdate } from './types';
  export let open: boolean = true;
  export let compact: boolean = false;
  export let results: ExecutionUpdate[] = [];
  export let onRun: () => void;
  export let onReset: () => void;
</script>

{#if open}
  <aside class="panel" class:compact aria-label="Testing Panel">
    <header>
      <div class="title">Testing</div>
      <div class="actions">
        <button class="btn" on:click={onRun}>Run</button>
        <button class="btn ghost" on:click={onReset}>Reset</button>
      </div>
    </header>
    {#if !compact}
      <section class="content">
        {#if results.length === 0}
          <div class="muted">No results yet. Run a scenario.</div>
        {:else}
          {#each results as r}
            <div class="card" class:error={r.type === 'execution_error'}>
              <div class="row"><span class="badge">{r.type}</span><span class="muted">{r.message}</span></div>
              {#if r.node_id}
                <div class="sub">node: {r.node_id}</div>
              {/if}
              {#if r.result}
                <pre>{JSON.stringify(r.result, null, 2)}</pre>
              {/if}
              {#if r.error}
                <div class="error-text">{r.error}</div>
              {/if}
            </div>
          {/each}
        {/if}
      </section>
    {/if}
  </aside>
{/if}

<style>
  .panel {
    position: absolute;
    top: 0;
    right: 420px;
    width: 420px;
    height: 100vh;
    background: var(--glass);
    border: 1px solid var(--border);
    border-radius: 0;
    backdrop-filter: blur(16px) saturate(120%);
    box-shadow: none;
    overflow: hidden;
    z-index: 19;
    display: flex;
    flex-direction: column;
  }
  .compact { width: 72px; padding: 0; }
  header { padding: 14px 16px; border-bottom: 1px solid var(--border); display:flex; align-items:center; justify-content: space-between; }
  .title { font-weight: 600; }
  .actions { display:flex; gap:8px; }
  .btn { background: var(--running); color: white; border: 1px solid transparent; border-radius: 10px; padding: 6px 10px; cursor: pointer; }
  .btn.ghost { background: transparent; color: var(--text); border-color: var(--border); }
  .content { padding: 12px; overflow-y:auto; display: grid; gap: 10px; }
  .card { background: rgba(255,255,255,0.05); border:1px solid var(--border); border-radius: 0; padding: 10px; }
  .card.error { border-color: var(--error); }
  .badge { background: rgba(255,255,255,0.08); border:1px solid var(--border); border-radius: 0; padding: 2px 8px; font-size: 11px; margin-right: 8px; }
  .row { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
  .sub { color: var(--muted); font-size: 12px; margin-bottom: 6px; }
  pre { margin: 0; font-size: 12px; background: transparent; color: var(--text); }
  .muted, .error-text { color: var(--muted); font-size: 13px; }
</style>
