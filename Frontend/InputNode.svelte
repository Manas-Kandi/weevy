<script lang="ts">
  import type { Node } from './types';
  import { ArrowRightCircle } from 'lucide-svelte';
  import { tick } from 'svelte';
  import { slide, fade } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';

  export let node: Node;
  let expanded = false;
  const defaultTitle = 'Email Support Intake';

  // Minimal, non-technical fields
  const conf = (node.data.configuration ||= {} as any);
  conf.description ||= '';
  conf.testCases ||= [
    { level: 'Critical', text: 'Production down, 500 users affected', from: 'enterprise@bigclient.com' },
    { level: 'Standard', text: 'Password reset not working', from: 'user@startup.co' },
    { level: 'Low', text: 'Feature request for dark mode', from: 'feedback@company.com' }
  ];

  let descEl: HTMLTextAreaElement;
  let exEl: HTMLTextAreaElement;

  function autoresize(el: HTMLTextAreaElement) {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }

  function handleResize(event: Event) {
    const el = event.currentTarget as HTMLTextAreaElement;
    if (el) autoresize(el);
  }

  async function initResize() {
    await tick();
    if (descEl) autoresize(descEl);
  }

  initResize();

  function handleTitleFocus() {
    if (!node.data.label || node.data.label.trim() === '') {
      node.data.label = defaultTitle;
    }
  }
</script>

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<div class="input-node" on:mousedown|stopPropagation role="group" aria-label="Input node editor">
  <div class="header">
    <div class="meta"><ArrowRightCircle size={12} /> <span>Input Node</span></div>
    <input
      class="title"
      placeholder={defaultTitle}
      bind:value={node.data.label}
      on:mousedown|stopPropagation
      on:focus={handleTitleFocus}
    />
  </div>

  <div class="content">
    <div class="prompt">What kind of input will this handle?</div>
    <textarea
      bind:this={descEl}
      class="note"
      placeholder="Describe in plain language..."
      bind:value={conf.description}
      rows="1"
      on:input={handleResize}
      on:mousedown|stopPropagation
    />

    <button class="expand" type="button" on:click={() => (expanded = !expanded)} aria-expanded={expanded}>
      {expanded ? 'Hide test cases' : 'Show test cases'}
    </button>

    {#if expanded}
      <div class="cases" transition:slide={{ duration: 400, easing: cubicOut }}>
        <div class="cases-title">Test Cases</div>
        <ul>
          {#each conf.testCases as tc, i}
            <li transition:fade={{ duration: 300, delay: i * 80 }}>
              <div class="case">
                <div class="case-header">{tc.level}</div>
                <div class="case-body">
                  <input class="text" bind:value={tc.text} on:mousedown|stopPropagation />
                </div>
                <div class="from">From: <input class="fromInput" bind:value={tc.from} on:mousedown|stopPropagation /></div>
              </div>
            </li>
          {/each}
        </ul>
        <button class="add" type="button" on:click={() => (conf.testCases = [...conf.testCases, { level: 'New', text: 'Describe...', from: 'user@example.com' }])}>+ Add test case</button>
      </div>
    {/if}
  </div>
</div>

<style>
  .input-node {
    width: 200px;
    min-height: 120px;
    border-radius: 20px;
    background: var(--node-glass);
    color: var(--text);
    border: 1px solid var(--glass-border);
    box-shadow: var(--shadow-node);
    backdrop-filter: blur(20px) saturate(180%);
    display: grid;
    grid-template-rows: auto 1fr;
    overflow: hidden;
    transition: all 0.3s var(--ease-spring);
  }
  .input-node:hover { 
    box-shadow: var(--shadow-float), var(--glow-subtle);
    transform: translateY(-2px) scale(1.01);
  }

  .header { display: grid; gap: 8px; padding: 16px 16px 10px 16px; }
  .meta { display: inline-flex; align-items: center; gap: 6px; color: var(--acc-input); font-size: 12px; opacity: 0.9; }

  .title {
    background: transparent;
    border: none;
    outline: none;
    color: #111827;
    font-weight: 700;
    font-size: calc(18px * clamp(0.8, 1 / var(--scale, 1), 1.15));
  }
  .title::placeholder { color: var(--muted); }

  .content { padding: 0 16px 16px 16px; display: grid; gap: 12px; }

  .prompt { font-size: 12px; color: var(--acc-input); letter-spacing: 0.2px; }
  /* .mt helper removed (unused) */

  .note {
    width: 100%;
    min-height: 24px;
    resize: none;
    overflow: hidden;
    background: rgba(255,255,255,0.6);
    border: 1px solid var(--border);
    border-radius: 12px;
    color: #334155; /* slate-700 */
    padding: 10px 12px;
    font-size: calc(14px * clamp(0.85, 1 / var(--scale, 1), 1.15));
    line-height: 1.35;
    outline: none;
  }
  .note::placeholder { color: var(--muted); }

  .expand { background: transparent; border: none; color: var(--acc-input); font-size: 12px; text-align: left; padding: 0; cursor: pointer; }
  .expand:hover { text-decoration: underline; }

  .cases { display: grid; gap: 12px; }
  .cases-title { font-size: 12px; color: #334155; font-weight: 600; }
  ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
  li { color: #0f172a; }
  .case { background: rgba(255,255,255,0.55); border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; display: grid; gap: 8px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08); }
  .case:hover { box-shadow: 0 0 0 1px color-mix(in oklab, var(--acc-input) 20%, transparent), 0 8px 18px rgba(0,0,0,0.10); }
  .case-header { font-weight: 600; font-size: calc(16px * clamp(0.85, 1 / var(--scale, 1), 1.05)); color: #111827; letter-spacing: 0.1px; }
  .case-body { color: #334155; font-size: calc(14px * clamp(0.9, 1 / var(--scale, 1), 1.05)); }
  .from { color: #475569; font-size: 12px; }
  .text, .fromInput { background: transparent; border: none; outline: none; color: inherit; font-size: inherit; font-weight: inherit; }
  .add { background: transparent; border: none; color: var(--acc-input); font-size: 12px; text-align: left; padding: 0; cursor: pointer; }
  .add:hover { text-decoration: underline; }
</style>
