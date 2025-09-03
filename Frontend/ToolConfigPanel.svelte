<script lang="ts">
  import type { Node } from './types';
  import { createEventDispatcher, onMount } from 'svelte';
  import { inputManager } from './InputManager';
  import type { NodeInputSchema } from './InputManager';

  export let node: Node;
  export let workflowId: string = 'current-workflow';
  
  const dispatch = createEventDispatcher<{ 
    updateConfig: { configuration: Record<string, any> } 
  }>();

  const TOOL_ACTIONS: Record<string, string[]> = {
    calendar: ['create_event', 'find_free_slots', 'list_events', 'update_event', 'cancel_event'],
    email: ['draft', 'send', 'search', 'read', 'summarize'],
    slack: ['post_message', 'fetch_history', 'reply_thread', 'summarize'],
    web_search: ['search', 'deep_search', 'news_search'],
    web_crawl: ['fetch', 'summarize', 'extract'],
    writer: ['outline', 'draft', 'revise', 'proofread'],
    notion: ['create_page', 'update_page', 'query_database', 'search'],
    jira: ['create_issue', 'update_issue', 'search', 'assign'],
    github: ['create_issue', 'summarize_pr', 'propose_changes', 'review_code'],
    sheets: ['append_rows', 'read_range', 'analyze', 'create_chart'],
    sql: ['query', 'explain', 'optimize'],
    translator: ['translate', 'detect_language'],
    summarizer: ['summarize', 'extract_key_points'],
    sentiment: ['analyze', 'track_changes'],
    data_analyzer: ['analyze', 'visualize', 'predict'],
    api_calling: ['get', 'post', 'put', 'delete']
  };

  const TOOLS = Object.keys(TOOL_ACTIONS);

  // Enhanced configuration state
  let tool = (node.data.configuration?.tool as string) || 'email';
  let action = (node.data.configuration?.action as string) || TOOL_ACTIONS[tool][0];
  let paramsText = JSON.stringify(node.data.configuration?.params || {}, null, 2);
  let mock = Boolean(node.data.configuration?.mock ?? true);

  // Dynamic input schema based on node type
  let inputSchema: NodeInputSchema = {};
  let configValues: Record<string, any> = {};
  let errors: Record<string, string> = {};

  onMount(() => {
    // Load input schema for this node type
    inputSchema = inputManager.getNodeInputSchema(node.type);
    
    // Load existing inputs from InputManager
    const existingInputs = inputManager.getNodeInputs(workflowId, node.id);
    existingInputs.forEach(input => {
      if (input.inputType === 'config' && input.label) {
        configValues[input.label] = input.value;
      }
    });

    // Initialize with current configuration if no stored inputs
    if (Object.keys(configValues).length === 0) {
      configValues = { ...node.data.configuration };
    }
  });

  function emitUpdate() {
    let params: Record<string, any> = {};
    try {
      params = paramsText.trim() ? JSON.parse(paramsText) : {};
    } catch (e) {
      errors.params = 'Invalid JSON format';
      return;
    }
    
    const configuration = { tool, action, params, mock, ...configValues };
    
    // Save to InputManager
    inputManager.updateNodeConfiguration(workflowId, node.id, configuration);
    
    // Emit to parent
    dispatch('updateConfig', { configuration });
  }

  function handleInputChange(key: string, value: any) {
    configValues[key] = value;
    delete errors[key];
    
    // Update InputManager
    inputManager.updateNodeInput(workflowId, node.id, {
      nodeId: node.id,
      inputType: 'config',
      value,
      label: key
    });
    
    emitUpdate();
  }

  function validateInput(key: string, value: any): boolean {
    const fieldSchema = inputSchema[key];
    if (!fieldSchema) return true;

    if (fieldSchema.required && (value === null || value === undefined || value === '')) {
      errors[key] = `${fieldSchema.label || key} is required`;
      return false;
    }

    if (fieldSchema.type === 'number' && isNaN(Number(value))) {
      errors[key] = `${fieldSchema.label || key} must be a number`;
      return false;
    }

    if (fieldSchema.min !== undefined && Number(value) < fieldSchema.min) {
      errors[key] = `${fieldSchema.label || key} must be at least ${fieldSchema.min}`;
      return false;
    }

    if (fieldSchema.max !== undefined && Number(value) > fieldSchema.max) {
      errors[key] = `${fieldSchema.label || key} must be at most ${fieldSchema.max}`;
      return false;
    }

    delete errors[key];
    return true;
  }

  function getValidationClass(key: string): string {
    return errors[key] ? 'error' : '';
  }

  $: if (!TOOL_ACTIONS[tool].includes(action)) {
    action = TOOL_ACTIONS[tool][0];
    emitUpdate();
  }

  // Get example configurations for different tools
  function getExampleParams(selectedTool: string, selectedAction: string): Record<string, any> {
    const examples: Record<string, Record<string, any>> = {
      email: {
        draft: { to: ['user@example.com'], subject: 'Hello', body: 'Draft email content' },
        send: { to: ['user@example.com'], subject: 'Hello', body: 'Email content', cc: [] },
        search: { query: 'important emails', limit: 10 }
      },
      slack: {
        post_message: { channel: '#general', message: 'Hello team!' },
        fetch_history: { channel: '#general', limit: 50 }
      },
      web_search: {
        search: { query: 'AI trends 2024', max_results: 5 },
        deep_search: { query: 'machine learning research', depth: 3 }
      },
      calendar: {
        create_event: { title: 'Meeting', start: '2024-03-15T14:00:00Z', duration: 60 },
        find_free_slots: { duration: 60, date: '2024-03-15' }
      }
    };
    
    return examples[selectedTool]?.[selectedAction] || {};
  }

  function loadExampleParams() {
    const example = getExampleParams(tool, action);
    paramsText = JSON.stringify(example, null, 2);
    emitUpdate();
  }
</script>

<div class="tool-config">
  <div class="config-header">
    <h3>Configure {node.type === 'tool' ? 'Tool' : node.type.charAt(0).toUpperCase() + node.type.slice(1)} Node</h3>
    <div class="node-id">ID: {node.id}</div>
  </div>

  {#if node.type === 'tool'}
    <!-- Tool-specific configuration -->
    <div class="config-section">
      <label>
        <span class="label">Tool</span>
        <select bind:value={tool} on:change={emitUpdate} class="select">
          {#each TOOLS as t}
            <option value={t}>{t.replace('_', ' ').toUpperCase()}</option>
          {/each}
        </select>
      </label>

      <label>
        <span class="label">Action</span>
        <select bind:value={action} on:change={emitUpdate} class="select">
          {#each TOOL_ACTIONS[tool] as a}
            <option value={a}>{a.replace('_', ' ').toUpperCase()}</option>
          {/each}
        </select>
      </label>

      <div class="params-section">
        <div class="params-header">
          <span class="label">Parameters (JSON)</span>
          <button type="button" class="example-btn" on:click={loadExampleParams}>
            Load Example
          </button>
        </div>
        <textarea 
          bind:value={paramsText} 
          rows="8" 
          on:input={emitUpdate} 
          on:blur={() => validateInput('params', paramsText)}
          spellcheck={false} 
          class="params-textarea {getValidationClass('params')}"
          placeholder="Enter tool parameters as JSON..."
        />
        {#if errors.params}
          <div class="error-message">{errors.params}</div>
        {/if}
      </div>

      <label class="checkbox">
        <input type="checkbox" bind:checked={mock} on:change={emitUpdate} />
        <span>Mock mode (simulated responses for testing)</span>
      </label>
    </div>
  {/if}

  <!-- Dynamic configuration fields based on node type -->
  {#if Object.keys(inputSchema).length > 0}
    <div class="config-section dynamic-fields">
      <h4>Node Configuration</h4>
      {#each Object.entries(inputSchema) as [key, fieldSchema]}
        <div class="field-group">
          <label class="field-label">
            <span class="label">
              {fieldSchema.label || key}
              {#if fieldSchema.required}<span class="required">*</span>{/if}
            </span>
            
            {#if fieldSchema.type === 'select'}
              <select 
                bind:value={configValues[key]}
                on:change={() => handleInputChange(key, configValues[key])}
                class="select {getValidationClass(key)}"
                required={fieldSchema.required}
              >
                {#if fieldSchema.options}
                  {#each fieldSchema.options as option}
                    <option value={option}>{option}</option>
                  {/each}
                {/if}
              </select>
            {:else if fieldSchema.type === 'textarea'}
              <textarea
                bind:value={configValues[key]}
                on:input={() => handleInputChange(key, configValues[key])}
                on:blur={() => validateInput(key, configValues[key])}
                class="textarea {getValidationClass(key)}"
                placeholder={fieldSchema.description}
                rows="4"
                required={fieldSchema.required}
              />
            {:else if fieldSchema.type === 'number'}
              <input
                type="number"
                bind:value={configValues[key]}
                on:input={() => handleInputChange(key, configValues[key])}
                on:blur={() => validateInput(key, configValues[key])}
                class="input {getValidationClass(key)}"
                placeholder={fieldSchema.description}
                min={fieldSchema.min}
                max={fieldSchema.max}
                required={fieldSchema.required}
              />
            {:else if fieldSchema.type === 'boolean'}
              <label class="checkbox-field">
                <input 
                  type="checkbox" 
                  bind:checked={configValues[key]}
                  on:change={() => handleInputChange(key, configValues[key])}
                />
                <span>{fieldSchema.description}</span>
              </label>
            {:else if fieldSchema.type === 'json'}
              <textarea
                bind:value={configValues[key]}
                on:input={() => handleInputChange(key, configValues[key])}
                on:blur={() => validateInput(key, configValues[key])}
                class="textarea json-input {getValidationClass(key)}"
                placeholder={fieldSchema.description || 'Enter JSON data...'}
                rows="6"
                spellcheck={false}
                required={fieldSchema.required}
              />
            {:else}
              <input
                type="text"
                bind:value={configValues[key]}
                on:input={() => handleInputChange(key, configValues[key])}
                on:blur={() => validateInput(key, configValues[key])}
                class="input {getValidationClass(key)}"
                placeholder={fieldSchema.description}
                required={fieldSchema.required}
              />
            {/if}
            
            {#if fieldSchema.description && fieldSchema.type !== 'boolean'}
              <div class="field-description">{fieldSchema.description}</div>
            {/if}
          </label>
          
          {#if errors[key]}
            <div class="error-message">{errors[key]}</div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}

  <!-- Validation summary -->
  {#if Object.keys(errors).length > 0}
    <div class="validation-summary">
      <div class="validation-header">Configuration Issues:</div>
      {#each Object.entries(errors) as [key, error]}
        <div class="validation-error">• {error}</div>
      {/each}
    </div>
  {/if}

  <!-- Configuration preview -->
  <details class="config-preview">
    <summary>Configuration Preview</summary>
    <pre class="config-json">{JSON.stringify({ 
      type: node.type, 
      tool: node.type === 'tool' ? tool : undefined,
      action: node.type === 'tool' ? action : undefined,
      ...configValues,
      mock: node.type === 'tool' ? mock : undefined 
    }, null, 2)}</pre>
  </details>
</div>

<style>
  .tool-config {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 16px;
    padding: 24px;
    width: 420px;
    max-width: 95vw;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 
      0 20px 64px rgba(0, 0, 0, 0.1),
      0 8px 24px rgba(0, 0, 0, 0.05);
    font-family: inherit;
  }

  .config-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }

  h3 { 
    margin: 0; 
    font-size: 18px; 
    font-weight: 600; 
    color: #111827;
  }

  h4 {
    margin: 0 0 16px 0;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .node-id {
    font-size: 11px;
    color: #6B7280;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background: rgba(0, 0, 0, 0.04);
    padding: 4px 8px;
    border-radius: 6px;
  }

  .config-section {
    margin-bottom: 24px;
  }

  .field-group {
    margin-bottom: 16px;
  }

  .field-label {
    display: flex; 
    flex-direction: column; 
    gap: 6px;
  }

  .label { 
    font-size: 12px;
    font-weight: 500;
    color: #374151;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .required {
    color: #EF4444;
    font-weight: 600;
  }

  .select, .input, .textarea, .params-textarea {
    background: rgba(255, 255, 255, 0.9);
    color: #111827;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 13px;
    font-family: inherit;
    transition: all 0.2s ease;
    width: 100%;
    box-sizing: border-box;
  }

  .select:focus, .input:focus, .textarea:focus, .params-textarea:focus {
    outline: none;
    border-color: #3B82F6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    background: #FFFFFF;
  }

  .textarea, .params-textarea { 
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; 
    font-size: 12px;
    resize: vertical;
    line-height: 1.4;
  }

  .json-input {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
  }

  .params-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .params-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .example-btn {
    background: rgba(59, 130, 246, 0.1);
    color: #3B82F6;
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .example-btn:hover {
    background: rgba(59, 130, 246, 0.15);
    border-color: rgba(59, 130, 246, 0.3);
  }

  .checkbox, .checkbox-field { 
    display: flex; 
    flex-direction: row; 
    align-items: center; 
    gap: 8px;
    margin: 8px 0;
  }

  .checkbox input[type="checkbox"], .checkbox-field input[type="checkbox"] { 
    accent-color: #3B82F6;
    width: 16px;
    height: 16px;
  }

  .checkbox span, .checkbox-field span { 
    color: #4B5563; 
    font-size: 13px; 
  }

  .field-description {
    font-size: 11px;
    color: #6B7280;
    margin-top: 4px;
    line-height: 1.3;
  }

  .error {
    border-color: #EF4444 !important;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
  }

  .error-message {
    color: #EF4444;
    font-size: 11px;
    font-weight: 500;
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .error-message::before {
    content: "⚠";
    font-size: 12px;
  }

  .validation-summary {
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.1);
    border-radius: 8px;
    padding: 12px;
    margin: 16px 0;
  }

  .validation-header {
    font-size: 12px;
    font-weight: 600;
    color: #DC2626;
    margin-bottom: 8px;
  }

  .validation-error {
    font-size: 11px;
    color: #EF4444;
    margin: 2px 0;
  }

  .config-preview {
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    margin-top: 16px;
  }

  .config-preview summary {
    padding: 12px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    color: #6B7280;
    border-radius: 8px;
    transition: background 0.2s ease;
  }

  .config-preview summary:hover {
    background: rgba(0, 0, 0, 0.02);
  }

  .config-preview[open] summary {
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 8px 8px 0 0;
  }

  .config-json {
    margin: 0;
    padding: 12px;
    background: rgba(0, 0, 0, 0.02);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 11px;
    color: #374151;
    overflow-x: auto;
    border-radius: 0 0 8px 8px;
    line-height: 1.4;
  }

  .dynamic-fields {
    border-top: 1px solid rgba(0, 0, 0, 0.06);
    padding-top: 20px;
  }

  /* Responsive adjustments */
  @media (max-width: 480px) {
    .tool-config {
      width: 100%;
      padding: 16px;
      border-radius: 12px;
    }

    .config-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }
  }
</style>

