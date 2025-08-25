export interface Node {
  id: string;
  type: 'brain' | 'input' | 'output' | 'knowledge' | 'tool';
  position: { x: number; y: number };
  data: {
    label: string;
    configuration: Record<string, any>;
  };
  selected?: boolean;
}

export interface Connection {
  id: string;
  from: string;
  to: string;
}

export interface WorkflowExecution {
  workflow_id: string;
  nodes: Array<{
    node_id: string;
    node_type: string;
    system_rules: string;
    user_configuration: Record<string, any>;
  }>;
  connections: Connection[];
}

export interface NodeResult {
  node_id: string;
  node_type: string;
  data: any;
  timestamp: number;
  metadata: Record<string, any>;
}

export interface ExecutionUpdate {
  type: 'execution_started' | 'execution_update' | 'node_result' | 'execution_complete' | 'execution_error';
  node_id?: string;
  content?: string;
  result?: any;
  error?: string;
  workflow_id?: string;
}
