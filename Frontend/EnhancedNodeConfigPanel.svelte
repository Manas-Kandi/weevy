<script lang="ts">
  import { onMount } from 'svelte';
  import type { Node } from './types';
  import { inputManager } from './InputManager';
  import type { NodeInputSchema } from './InputManager';

  export let node: Node;
  export let workflowId: string = 'current-workflow';
  
  const dispatch = createEventDispatcher<{
    updateConfig: { configuration: Record<string, any> }
  }>();

  // State
  let inputSchema: NodeInputSchema = {};
  let configValues: Record<string, any> = {};
  let errors: Record<string, string> = {};
  let isValid = true;

  // Load node configuration
  onMount(() => {
    loadNodeConfiguration();
  });

  function loadNodeConfiguration() {
    // Get input schema for this node type
    inputSchema = inputManager.getNodeInputSchema(node.type);
    
    // Load existing configuration
    const existingInputs = inputManager.getNodeInputs(workflowId, node.id);
    
    // Initialize with existing values or defaults
    configValues = { ...node.data.configuration };
    
    // Merge stored inputs
    existingInputs.forEach(input => {
      if (input.inputType === 'config' && input.label) {
        configValues[input.label] = input.value;
      }
    });
    
    // Set defaults for missing values
    Object.entries(inputSchema).forEach(([key, schema]) => {
      if (configValues[key] === undefined && schema.default !== undefined) {
        configValues[key] = schema.default;
      }
    });
  }

  function handleInputChange(key: string, value: any) {
    configValues[key] = value;
    validateField(key, value);
    
    // Update InputManager
    inputManager.updateNodeInput(workflowId, node.id, {
      nodeId: node.id,
      inputType: 'config',
      value,
      label: key
    });
    
    emitUpdate();
  }

  function validateField(key: string, value: any): boolean {
    const fieldSchema = inputSchema[key];
    if (!fieldSchema) return true;

    // Required field validation
    if (fieldSchema.required && (value === null || value === undefined || value === '')) {
      errors[key] = `${fieldSchema.label || key} is required`;
      return false;
    }

    // Type validation
    if (fieldSchema.type === 'number' && value !== '' && isNaN(Number(value))) {
      errors[key] = `${fieldSchema.label || key} must be a number`;
      return false;
    }

    // Range validation
    if (fieldSchema.type === 'number' && value !== '') {
      const numValue = Number(value);
      if (fieldSchema.min !== undefined && numValue < fieldSchema.min) {
        errors[key] = `${fieldSchema.label || key} must be at least ${fieldSchema.min}`;
        return false;
      }
      if (fieldSchema.max !== undefined && numValue > fieldSchema.max) {
        errors[key] = `${fieldSchema.label || key} must be at most ${fieldSchema.max}`;
        return false;
      }
    }

    // JSON validation
    if (fieldSchema.type === 'json' && value && typeof value === 'string') {
      try {
        JSON.parse(value);
      } catch (e) {
        errors[key] = `${fieldSchema.label || key} must be valid JSON`;
        return false;
      }
    }

    delete errors[key];
    return true;
  }

  function validateAll(): boolean {
    const newErrors: Record<string, string> = {};
    let valid = true;

    Object.entries(inputSchema).forEach(([key, schema]) => {
      if (!validateField(key, configValues[key])) {
        valid = false;
      }
    });

    errors = newErrors;
    isValid = valid;
    return valid;
  }

  function emitUpdate() {
    validateAll();
    dispatch('updateConfig', { configuration: configValues });
  }

  function resetToDefaults() {
    Object.entries(inputSchema).forEach(([key, schema]) => {
      if (schema.default !== undefined) {
        configValues[key] = schema.default;
      } else {
        delete configValues[key];
      }
    });
    errors = {};
    emitUpdate();
  }

  function loadExampleConfiguration() {
    // Load example based on node type
    const examples = {
      brain: {
        systemInstructions: "You are a helpful AI assistant. Analyze the input and provide thoughtful, accurate responses.",
        mode: "reasoning",
        temperature: 0.7,
        maxTokens: 2048
      },
      input: {
        prompt: "Enter your question or task here",
        inputType: "text",
        context: "Additional context for better results"
      },
      knowledge: {
        query: "Search knowledge base",
        maxResults: 10
      },
      output: {
        format: "text",
        includeMetadata: false
      }
    };

    const example = examples[node.type as keyof typeof examples];
    if (example) {
      configValues = { ...configValues, ...example };
      emitUpdate();
    }
  }

  // Reactive validation
  $: {
    if (Object.keys(configValues).length > 0) {
      validateAll();
    }
  }
</script>

<div class="config-panel">
  <div class="panel-header">
    <h3>Configure {node.type.charAt(0).toUpperCase() + node.type.slice(1)} Node</h3>
    <div class="node-info">
      <span class="node-id">ID: {node.id}</span>
      <span class="node-status" class:valid={isValid} class:invalid={!isValid}>
        {isValid ? '✓ Valid' : '⚠ Issues'}
      </span>
    </div>
  </div>

  {#if Object.keys(inputSchema).length > 0}
    <div class="config-fields">
      {#each Object.entries(inputSchema) as [key, fieldSchema]}
        <div class="field-group" class:error={errors[key]}>
          <label class="field-label">
            <span class="label-text">
              {fieldSchema.label || key}
              {#if fieldSchema.required}<span class="required">*</span>{/if}
            </span>
            
            {#if fieldSchema.type === 'select'}
              <select 
                bind:value={configValues[key]}
                on:change={() => handleInputChange(key, configValues[key])}
                class="field-input"
                required={fieldSchema.required}
              >
                <option value="">Choose...</option>
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
                class="field-input textarea"
                placeholder={fieldSchema.description}
                rows="4"
                required={fieldSchema.required}
              />
            {:else if fieldSchema.type === 'number'}
              <input
                type="number"
                bind:value={configValues[key]}
                on:input={() => handleInputChange(key, configValues[key])}
                class="field-input"
                placeholder={fieldSchema.description}
                min={fieldSchema.min}
                max={fieldSchema.max}
                step={fieldSchema.type === 'number' ? 'any' : undefined}
                required={fieldSchema.required}
              />
            {:else if fieldSchema.type === 'boolean'}
              <label class="checkbox-wrapper">
                <input 
                  type="checkbox" 
                  bind:checked={configValues[key]}
                  on:change={() => handleInputChange(key, configValues[key])}
                  class="checkbox"
                />
                <span class="checkbox-text">{fieldSchema.description || 'Enable this option'}</span>
              </label>
            {:else if fieldSchema.type === 'json'}
              <textarea
                bind:value={configValues[key]}
                on:input={() => handleInputChange(key, configValues[key])}
                class="field-input textarea json-input"
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
                class="field-input"
                placeholder={fieldSchema.description}
                required={fieldSchema.required}
              />
            {/if}
            
            {#if fieldSchema.description && fieldSchema.type !== 'boolean'}
              <div class="field-description">{fieldSchema.description}</div>
            {/if}
          </label>
          
          {#if errors[key]}
            <div class="error-message">⚠ {errors[key]}</div>
          {/if}
        </div>
      {/each}
    </div>

    <div class="panel-actions">
      <button type="button" class="action-btn secondary" on:click={resetToDefaults}>
        Reset to Defaults
      </button>
      <button type="button" class="action-btn primary" on:click={loadExampleConfiguration}>
        Load Example
      </button>
    </div>
  {:else}
    <div class="no-config">
      <div class="no-config-icon">⚙️</div>
      <div class="no-config-text">No configuration options available for this node type.</div>
    </div>
  {/if}

  <!-- Validation Summary -->
  {#if Object.keys(errors).length > 0}
    <div class="validation-summary">
      <div class="validation-header">Configuration Issues:</div>
      {#each Object.entries(errors) as [key, error]}
        <div class="validation-item">• {error}</div>
      {/each}
    </div>
  {/if}

  <!-- Configuration Preview -->
  <details class="config-preview">
    <summary>Configuration Preview</summary>
    <pre class="config-json">{JSON.stringify(configValues, null, 2)}</pre>
  </details>
</div>

<style>
  .config-panel {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 12px;
    padding: 20px;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 0 10px 32px rgba(0, 0, 0, 0.1);
  }

  .panel-header {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  }

  .panel-header h3 {
    margin: 0 0 8px 0;
    font-size: 16px;
    font-weight: 600;
    color: #111827;
  }

  .node-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
  }

  .node-id {
    color: #6B7280;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  .node-status {
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 500;
  }

  .node-status.valid {
    background: rgba(16, 185, 129, 0.1);
    color: #059669;
  }

  .node-status.invalid {
    background: rgba(239, 68, 68, 0.1);
    color: #DC2626;
  }

  .config-fields {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field-group.error .field-input {
    border-color: #EF4444;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
  }

  .field-label {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .label-text {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .required {
    color: #EF4444;
    font-weight: 600;
  }

  .field-input {
    background: rgba(255, 255, 255, 0.9);
    color: #111827;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 13px;
    transition: all 0.2s ease;
    font-family: inherit;
  }

  .field-input:focus {
    outline: none;
    border-color: #3B82F6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    background: #FFFFFF;
  }

  .textarea {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
    resize: vertical;
    line-height: 1.4;
  }

  .json-input {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  .checkbox-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
  }

  .checkbox {
    accent-color: #3B82F6;
    width: 16px;
    height: 16px;
  }

  .checkbox-text {
    font-size: 13px;
    color: #4B5563;
  }

  .field-description {
    font-size: 11px;
    color: #6B7280;
    line-height: 1.3;
  }

  .error-message {
    color: #EF4444;
    font-size: 11px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .panel-actions {
    display: flex;
    gap: 8px;
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }

  .action-btn {
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
  }

  .action-btn.primary {
    background: #3B82F6;
    color: white;
  }

  .action-btn.primary:hover {
    background: #2563EB;
  }

  .action-btn.secondary {
    background: rgba(0, 0, 0, 0.04);
    color: #374151;
  }

  .action-btn.secondary:hover {
    background: rgba(0, 0, 0, 0.08);
  }

  .no-config {
    text-align: center;
    padding: 40px 20px;
    color: #6B7280;
  }

  .no-config-icon {
    font-size: 32px;
    margin-bottom: 12px;
  }

  .validation-summary {
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.1);
    border-radius: 8px;
    padding: 12px;
    margin-top: 16px;
  }

  .validation-header {
    font-size: 12px;
    font-weight: 600;
    color: #DC2626;
    margin-bottom: 8px;
  }

  .validation-item {
    font-size: 11px;
    color: #EF4444;
    margin: 2px 0;
  }

  .config-preview {
    margin-top: 16px;
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 8px;
  }

  .config-preview summary {
    padding: 12px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    color: #6B7280;
    border-radius: 8px;
  }

  .config-preview summary:hover {
    background: rgba(0, 0, 0, 0.02);
  }

  .config-json {
    margin: 0;
    padding: 12px;
    background: rgba(0, 0, 0, 0.02);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 11px;
    color: #374151;
    overflow-x: auto;
    line-height: 1.4;
    white-space: pre-wrap;
  }
</style>