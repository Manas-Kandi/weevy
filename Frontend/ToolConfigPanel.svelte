<script lang="ts">
  import type { Node } from './types';
  import { createEventDispatcher } from 'svelte';

  export let node: Node;
  const dispatch = createEventDispatcher<{ updateConfig: { configuration: Record<string, any> } }>();

  const TOOL_ACTIONS: Record<string, string[]> = {
    calendar: ['create_event', 'find_free_slots', 'list_events', 'update_event', 'cancel_event'],
    email: ['draft', 'send', 'search', 'read', 'summarize'],
    slack: ['post_message', 'fetch_history', 'reply_thread', 'summarize'],
    web_search: ['search'],
    web_crawl: ['fetch', 'summarize', 'extract'],
    writer: ['outline', 'draft', 'revise'],
    notion: ['create_page', 'update_page', 'query_database'],
    jira: ['create_issue', 'update_issue', 'search'],
    github: ['create_issue', 'summarize_pr', 'propose_changes'],
    sheets: ['append_rows', 'read_range', 'analyze'],
    sql: ['query', 'explain'],
    translator: ['translate'],
    summarizer: ['summarize'],
    sentiment: ['analyze']
  };

  const TOOLS = Object.keys(TOOL_ACTIONS);

  let tool = (node.data.configuration?.tool as string) || 'email';
  let action = (node.data.configuration?.action as string) || TOOL_ACTIONS[tool][0];
  let paramsText = JSON.stringify(node.data.configuration?.params || {}, null, 2);
  let mock = Boolean(node.data.configuration?.mock ?? true);

  function emitUpdate() {
    let params: Record<string, any> = {};
    try {
      params = paramsText.trim() ? JSON.parse(paramsText) : {};
    } catch (e) {
      // keep previous valid params if JSON invalid
    }
    dispatch('updateConfig', { configuration: { tool, action, params, mock } });
  }

  $: if (!TOOL_ACTIONS[tool].includes(action)) {
    action = TOOL_ACTIONS[tool][0];
    emitUpdate();
  }
</script>

<div class="tool-config">
  <h3>Tool Configuration</h3>
  <label>
    <span>Tool</span>
    <select bind:value={tool} on:change={emitUpdate}>
      {#each TOOLS as t}
        <option value={t}>{t}</option>
      {/each}
    </select>
  </label>

  <label>
    <span>Action</span>
    <select bind:value={action} on:change={emitUpdate}>
      {#each TOOL_ACTIONS[tool] as a}
        <option value={a}>{a}</option>
      {/each}
    </select>
  </label>

  <label>
    <span>Params (JSON)</span>
    <textarea bind:value={paramsText} rows="8" on:input={emitUpdate} spellcheck={false} />
  </label>

  <label class="checkbox">
    <input type="checkbox" bind:checked={mock} on:change={emitUpdate} />
    <span>Mock mode (no external calls)</span>
  </label>
</div>

<style>
  .tool-config {
    background: rgba(161, 6, 6, 0.55);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px;
    width: auto;
  }
  h3 { margin: 0 0 12px 0; font-size: 14px; font-weight: 600; }
  label { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
  select, textarea {
    background: rgba(255,255,255,0.6);
    color: #0f172a;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px;
  }
  textarea { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; }
  .checkbox { display: flex; flex-direction: row; align-items: center; gap: 8px; }
  input[type="checkbox"] { accent-color: var(--accent-primary); }
  span { color: #334155; font-size: 12px; }
</style>

