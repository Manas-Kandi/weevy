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

<div class="input-node" on:mousedown|stopPropagation>
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
    border-radius: 16px; /* generous */
    background: #000;
    color: #e6e8eb;
    border: none; /* no border, floating via shadow */
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: grid;
    grid-template-rows: auto 1fr;
    overflow: hidden;
  }
  .input-node:hover { box-shadow: 0 6px 18px rgba(0,0,0,0.18); transform: scale(1.01); }

  .header { display: grid; gap: 8px; padding: 16px 16px 10px 16px; }
  .meta { display: inline-flex; align-items: center; gap: 6px; color: #67E8F9; font-size: 12px; opacity: 0.9; }

  .title {
    background: transparent;
    border: none;
    outline: none;
    color: #eaf2ff;
    font-weight: 700;
    font-size: calc(18px * clamp(0.8, 1 / var(--scale, 1), 1.15));
  }
  .title::placeholder { color: rgba(255,255,255,0.35); }

  .content { padding: 0 16px 16px 16px; display: grid; gap: 12px; }

  .prompt { font-size: 12px; color: #67E8F9; letter-spacing: 0.2px; }
  .mt { margin-top: 4px; }

  .note {
    width: 100%;
    min-height: 24px;
    resize: none;
    overflow: hidden;
    background: #0b0b0b;
    border: none;
    border-radius: 12px;
    color: #bfbfbf; /* light gray for description */
    padding: 10px 12px;
    font-size: calc(14px * clamp(0.85, 1 / var(--scale, 1), 1.15));
    line-height: 1.35;
    outline: none;
  }
  .note::placeholder { color: #888; }

  .expand { background: transparent; border: none; color: #67E8F9; font-size: 12px; text-align: left; padding: 0; cursor: pointer; }
  .expand:hover { text-decoration: underline; }

  .cases { display: grid; gap: 12px; }
  .cases-title { font-size: 12px; color: rgba(217,231,255,0.7); font-weight: 600; }
  ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
  li { color: #e6e8eb; }
  .case { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 12px 14px; display: grid; gap: 8px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
  .case:hover { box-shadow: 0 0 0 1px rgba(103,232,249,0.1), 0 8px 20px rgba(0,0,0,0.25); }
  .case-header { font-weight: 600; font-size: calc(16px * clamp(0.85, 1 / var(--scale, 1), 1.05)); color: #ffffff; letter-spacing: 0.1px; }
  .case-body { color: #cfd3da; font-size: calc(14px * clamp(0.9, 1 / var(--scale, 1), 1.05)); }
  .from { color: rgba(200,205,215,0.75); font-size: 12px; }
  .level, .text, .fromInput { background: transparent; border: none; outline: none; color: inherit; font-size: inherit; font-weight: inherit; }
  .add { background: transparent; border: none; color: #9CC9FF; font-size: 12px; text-align: left; padding: 0; cursor: pointer; }
  .add:hover { text-decoration: underline; }
</style>
