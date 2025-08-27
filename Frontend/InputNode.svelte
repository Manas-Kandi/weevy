<script lang="ts">
  import type { Node } from './types';
  import { FileInput, Sparkles } from 'lucide-svelte';
  import { tick, onMount } from 'svelte';
  import { scale, fly } from 'svelte/transition';
  import { elasticOut, cubicInOut } from 'svelte/easing';

  export let node: Node;
  let focused = false;
  let hovering = false;
  const defaultTitle = 'Descriptive title of the thing';
  const defaultDescription = 'In the realm of creativity, the essence of innovation flows like a river, weaving through the landscapes of imagination and possibility.';

  // Simplified natural language configuration
  const conf = (node.data.configuration ||= {} as any);
  conf.description ||= defaultDescription;
  
  let titleEl: HTMLTextAreaElement;
  let descEl: HTMLTextAreaElement;

  function autoresize(el: HTMLTextAreaElement) {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.max(el.scrollHeight, 48)}px`;
  }

  function handleResize(event: Event) {
    const el = event.currentTarget as HTMLTextAreaElement;
    if (el) autoresize(el);
  }

  async function initResize() {
    await tick();
    if (titleEl) autoresize(titleEl);
    if (descEl) autoresize(descEl);
  }

  onMount(() => {
    initResize();
  });

  function handleTitleFocus() {
    focused = true;
    if (!node.data.label || node.data.label.trim() === '') {
      node.data.label = '';
    }
  }

  function handleDescriptionFocus() {
    focused = true;
    if (conf.description === defaultDescription) {
      conf.description = '';
    }
  }
</script>

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<div 
  class="pocket-note" 
  class:focused
  class:hovering
  on:mousedown|stopPropagation 
  on:mouseenter={() => hovering = true}
  on:mouseleave={() => hovering = false}
  role="group" 
  aria-label="Input node editor"
  in:scale={{ duration: 600, easing: elasticOut, start: 0.8 }}
>
  <!-- Floating sparkle animation -->
  {#if hovering}
    <div class="sparkle" in:fly={{ y: -20, duration: 400, easing: cubicInOut }}>
      <Sparkles size={16} />
    </div>
  {/if}
  
  <div class="node-type">
    <FileInput size={14} /> Input Node
  </div>
  
  <textarea
    bind:this={titleEl}
    class="title"
    placeholder={defaultTitle}
    bind:value={node.data.label}
    on:mousedown|stopPropagation
    on:focus={handleTitleFocus}
    on:blur={() => focused = false}
    on:input={handleResize}
    rows="1"
  />
  
  <textarea
    bind:this={descEl}
    class="description"
    placeholder="Describe what this input handles in natural language..."
    bind:value={conf.description}
    on:mousedown|stopPropagation
    on:focus={handleDescriptionFocus}
    on:blur={() => focused = false}
    on:input={handleResize}
    rows="3"
  />
</div>

<style>
  .pocket-note {
    width: 320px;
    min-height: 240px;
    background: linear-gradient(135deg, #FFFFFF 0%, #FEFEFE 100%);
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 24px;
    padding: 32px;
    box-shadow: 
      0 4px 32px rgba(0, 0, 0, 0.04),
      0 1px 2px rgba(0, 0, 0, 0.02);
    position: relative;
    transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
    cursor: text;
    overflow: hidden;
  }

  .pocket-note:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 
      0 16px 64px rgba(0, 0, 0, 0.08),
      0 4px 16px rgba(0, 0, 0, 0.04);
    border-color: rgba(59, 130, 246, 0.15);
  }

  .pocket-note.focused {
    transform: translateY(-4px) scale(1.01);
    box-shadow: 
      0 12px 48px rgba(59, 130, 246, 0.08),
      0 0 0 3px rgba(59, 130, 246, 0.1);
    border-color: rgba(59, 130, 246, 0.2);
  }

  .sparkle {
    position: absolute;
    top: 16px;
    right: 16px;
    color: #3B82F6;
    opacity: 0.6;
    animation: sparkleFloat 2s ease-in-out infinite;
  }

  @keyframes sparkleFloat {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-4px) rotate(5deg); }
  }

  .node-type {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #3B82F6;
    margin-bottom: 20px;
    letter-spacing: 0.2px;
    opacity: 0.8;
  }

  .title {
    width: 100%;
    background: transparent;
    border: none;
    outline: none;
    font-size: 36px;
    font-weight: 300;
    color: #E5E5E5;
    line-height: 1.2;
    margin-bottom: 20px;
    resize: none;
    overflow: hidden;
    font-family: inherit;
    transition: all 0.3s ease;
  }

  .title:focus,
  .title:not(:placeholder-shown) {
    color: #1F2937;
  }

  .title::placeholder {
    color: #E5E5E5;
  }

  .description {
    width: 100%;
    background: transparent;
    border: none;
    outline: none;
    font-size: 16px;
    font-weight: 400;
    color: #6B7280;
    line-height: 1.6;
    resize: none;
    overflow: hidden;
    font-family: inherit;
    min-height: 80px;
    transition: all 0.3s ease;
  }

  .description:focus {
    color: #374151;
  }

  .description::placeholder {
    color: #D1D5DB;
  }

  /* Subtle animation for content */
  .pocket-note.hovering .title {
    transform: translateY(-2px);
  }

  .pocket-note.hovering .description {
    transform: translateY(-1px);
  }

  /* Floating animation keyframes */
  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
  }

  .pocket-note.focused {
    animation: none;
  }
</style>
