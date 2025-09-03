import type { Node, Connection, WorkflowExecution } from './types';

export interface NodeInput {
  nodeId: string;
  inputType: 'text' | 'file' | 'config' | 'prompt' | 'json';
  value: any;
  label?: string;
  metadata?: Record<string, any>;
  timestamp: number;
}

export interface WorkflowInputs {
  workflowId: string;
  nodeInputs: Map<string, NodeInput[]>;
  globalConfig: Record<string, any>;
  metadata: {
    createdAt: number;
    updatedAt: number;
    version: string;
  };
}

export interface NodeInputSchema {
  [key: string]: {
    type: 'text' | 'number' | 'boolean' | 'select' | 'json' | 'textarea';
    required?: boolean;
    label?: string;
    description?: string;
    options?: string[];
    min?: number;
    max?: number;
    default?: any;
  };
}

export class InputManager {
  private inputs: Map<string, WorkflowInputs> = new Map();
  private static instance: InputManager;

  constructor() {
    this.loadFromStorage();
  }

  static getInstance(): InputManager {
    if (!InputManager.instance) {
      InputManager.instance = new InputManager();
    }
    return InputManager.instance;
  }

  private loadFromStorage() {
    try {
      const stored = localStorage.getItem('weev-workflow-inputs');
      if (stored) {
        const data = JSON.parse(stored);
        Object.entries(data).forEach(([workflowId, inputs]: [string, any]) => {
          this.inputs.set(workflowId, {
            ...inputs,
            nodeInputs: new Map(Object.entries(inputs.nodeInputs || {}))
          });
        });
      }
    } catch (error) {
      console.warn('Failed to load workflow inputs from storage:', error);
    }
  }

  private saveToStorage() {
    try {
      const data: Record<string, any> = {};
      this.inputs.forEach((inputs, workflowId) => {
        data[workflowId] = {
          ...inputs,
          nodeInputs: Object.fromEntries(inputs.nodeInputs)
        };
      });
      localStorage.setItem('weev-workflow-inputs', JSON.stringify(data));
    } catch (error) {
      console.warn('Failed to save workflow inputs to storage:', error);
    }
  }

  initializeWorkflow(workflowId: string): WorkflowInputs {
    if (!this.inputs.has(workflowId)) {
      const workflowInputs: WorkflowInputs = {
        workflowId,
        nodeInputs: new Map(),
        globalConfig: {},
        metadata: {
          createdAt: Date.now(),
          updatedAt: Date.now(),
          version: '1.0.0'
        }
      };
      this.inputs.set(workflowId, workflowInputs);
      this.saveToStorage();
    }
    return this.inputs.get(workflowId)!;
  }

  updateNodeInput(workflowId: string, nodeId: string, input: Omit<NodeInput, 'timestamp'>): void {
    const workflowInputs = this.initializeWorkflow(workflowId);
    
    if (!workflowInputs.nodeInputs.has(nodeId)) {
      workflowInputs.nodeInputs.set(nodeId, []);
    }

    const nodeInputs = workflowInputs.nodeInputs.get(nodeId)!;
    const fullInput: NodeInput = {
      ...input,
      timestamp: Date.now()
    };

    // Replace or add input based on inputType and label
    const existingIndex = nodeInputs.findIndex(
      existing => existing.inputType === input.inputType && existing.label === input.label
    );

    if (existingIndex >= 0) {
      nodeInputs[existingIndex] = fullInput;
    } else {
      nodeInputs.push(fullInput);
    }

    workflowInputs.metadata.updatedAt = Date.now();
    this.saveToStorage();
  }

  updateNodeConfiguration(workflowId: string, nodeId: string, configuration: Record<string, any>): void {
    const workflowInputs = this.initializeWorkflow(workflowId);
    
    // Convert configuration object to NodeInput entries
    Object.entries(configuration).forEach(([key, value]) => {
      this.updateNodeInput(workflowId, nodeId, {
        nodeId,
        inputType: 'config',
        value,
        label: key,
        metadata: { configKey: key }
      });
    });
  }

  getNodeInputs(workflowId: string, nodeId: string): NodeInput[] {
    const workflowInputs = this.inputs.get(workflowId);
    return workflowInputs?.nodeInputs.get(nodeId) || [];
  }

  getWorkflowInputs(workflowId: string): WorkflowInputs | null {
    return this.inputs.get(workflowId) || null;
  }

  clearNodeInputs(workflowId: string, nodeId: string): void {
    const workflowInputs = this.inputs.get(workflowId);
    if (workflowInputs) {
      workflowInputs.nodeInputs.delete(nodeId);
      workflowInputs.metadata.updatedAt = Date.now();
      this.saveToStorage();
    }
  }

  deleteWorkflowInputs(workflowId: string): void {
    this.inputs.delete(workflowId);
    this.saveToStorage();
  }

  getNodeInputSchema(nodeType: string): NodeInputSchema {
    const schemas: Record<string, NodeInputSchema> = {
      input: {
        prompt: {
          type: 'textarea',
          required: true,
          label: 'User Prompt',
          description: 'The main input prompt or question for this workflow'
        },
        context: {
          type: 'textarea',
          required: false,
          label: 'Additional Context',
          description: 'Optional context or background information'
        },
        inputType: {
          type: 'select',
          required: true,
          label: 'Input Type',
          description: 'Type of input data',
          options: ['text', 'file', 'api', 'database'],
          default: 'text'
        }
      },
      brain: {
        systemInstructions: {
          type: 'textarea',
          required: true,
          label: 'System Instructions',
          description: 'Core instructions that define how this AI brain should behave'
        },
        temperature: {
          type: 'number',
          required: false,
          label: 'Temperature',
          description: 'Controls randomness (0.0 = deterministic, 1.0 = very creative)',
          min: 0,
          max: 1,
          default: 0.7
        },
        maxTokens: {
          type: 'number',
          required: false,
          label: 'Max Tokens',
          description: 'Maximum length of response',
          min: 1,
          max: 4096,
          default: 2048
        },
        mode: {
          type: 'select',
          required: true,
          label: 'Execution Mode',
          description: 'How the brain node should operate',
          options: ['reasoning', 'creative', 'analytical', 'conversational'],
          default: 'reasoning'
        }
      },
      tool: {
        toolName: {
          type: 'select',
          required: true,
          label: 'Tool',
          description: 'Select which tool to use',
          options: ['web_search', 'email', 'calendar', 'notion', 'slack', 'github', 'data_analyzer']
        },
        action: {
          type: 'select',
          required: true,
          label: 'Action',
          description: 'What action should this tool perform',
          options: ['execute', 'query', 'create', 'update', 'delete', 'search']
        },
        parameters: {
          type: 'json',
          required: true,
          label: 'Parameters',
          description: 'Tool-specific parameters as JSON'
        },
        mock: {
          type: 'boolean',
          required: false,
          label: 'Mock Mode',
          description: 'Use simulated responses for testing',
          default: true
        }
      },
      knowledge: {
        query: {
          type: 'text',
          required: false,
          label: 'Search Query',
          description: 'Query to search the knowledge base'
        },
        sources: {
          type: 'json',
          required: false,
          label: 'Knowledge Sources',
          description: 'Specific knowledge sources to query (as JSON array)'
        },
        maxResults: {
          type: 'number',
          required: false,
          label: 'Max Results',
          description: 'Maximum number of knowledge entries to retrieve',
          min: 1,
          max: 50,
          default: 10
        }
      },
      output: {
        format: {
          type: 'select',
          required: true,
          label: 'Output Format',
          description: 'How should the final output be formatted',
          options: ['text', 'json', 'markdown', 'html'],
          default: 'text'
        },
        template: {
          type: 'textarea',
          required: false,
          label: 'Output Template',
          description: 'Optional template for formatting the output'
        },
        includeMetadata: {
          type: 'boolean',
          required: false,
          label: 'Include Metadata',
          description: 'Include execution metadata in the output',
          default: false
        }
      }
    };

    return schemas[nodeType] || {};
  }

  translateToBackendFormat(workflowId: string, nodes: Node[], connections: Connection[]): WorkflowExecution {
    const workflowInputs = this.getWorkflowInputs(workflowId);
    
    const processedNodes = nodes.map(node => {
      const nodeInputs = this.getNodeInputs(workflowId, node.id);
      const configuration: Record<string, any> = { ...node.data.configuration };
      
      // Merge stored inputs into configuration
      nodeInputs.forEach(input => {
        if (input.inputType === 'config' && input.label) {
          configuration[input.label] = input.value;
        } else if (input.inputType === 'prompt') {
          configuration.prompt = input.value;
        } else if (input.inputType === 'text') {
          configuration.input_text = input.value;
        }
      });

      return {
        node_id: node.id,
        node_type: node.type,
        system_rules: this._generateSystemRules(node.type, configuration),
        user_configuration: configuration
      };
    });

    return {
      workflow_id: workflowId,
      nodes: processedNodes,
      connections: connections.map(conn => ({
        id: conn.id,
        from: conn.from,
        to: conn.to,
        fromPort: conn.fromPort,
        toPort: conn.toPort
      }))
    };
  }

  private _generateSystemRules(nodeType: string, configuration: Record<string, any>): string {
    const baseRules = {
      input: 'Process and validate user input, preparing it for downstream workflow execution.',
      brain: configuration.systemInstructions || 'Analyze the input and provide intelligent reasoning and decision-making.',
      tool: `Execute the ${configuration.toolName || 'specified'} tool with the provided parameters.`,
      knowledge: 'Search and retrieve relevant information from the knowledge base.',
      output: `Format and present the final result in ${configuration.format || 'text'} format.`
    };

    return baseRules[nodeType as keyof typeof baseRules] || `Execute ${nodeType} node functionality.`;
  }

  // Validation methods
  validateNodeInputs(workflowId: string, nodeId: string, nodeType: string): { valid: boolean; errors: string[] } {
    const schema = this.getNodeInputSchema(nodeType);
    const nodeInputs = this.getNodeInputs(workflowId, nodeId);
    const errors: string[] = [];

    Object.entries(schema).forEach(([key, fieldSchema]) => {
      if (fieldSchema.required) {
        const hasInput = nodeInputs.some(input => 
          input.label === key && input.value !== null && input.value !== undefined && input.value !== ''
        );
        
        if (!hasInput) {
          errors.push(`Required field "${fieldSchema.label || key}" is missing`);
        }
      }
    });

    return { valid: errors.length === 0, errors };
  }

  validateWorkflow(workflowId: string, nodes: Node[]): { valid: boolean; nodeErrors: Record<string, string[]> } {
    const nodeErrors: Record<string, string[]> = {};
    let valid = true;

    nodes.forEach(node => {
      const validation = this.validateNodeInputs(workflowId, node.id, node.type);
      if (!validation.valid) {
        nodeErrors[node.id] = validation.errors;
        valid = false;
      }
    });

    return { valid, nodeErrors };
  }
}

export const inputManager = InputManager.getInstance();