"""
Workflow Input Processor

Translates frontend node configurations and user inputs into backend execution context.
Provides intelligent processing of node inputs, system rules generation, and configuration validation.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Supported node types in the workflow system"""
    BRAIN = "brain"
    INPUT = "input" 
    OUTPUT = "output"
    KNOWLEDGE = "knowledge"
    TOOL = "tool"
    EXTERNAL_APP = "externalApp"


class ProcessingMode(Enum):
    """Processing modes for workflow execution"""
    DEVELOPMENT = "development"  # More verbose, includes debug info
    PRODUCTION = "production"    # Optimized for performance
    TESTING = "testing"         # Includes validation and mock responses


@dataclass
class ProcessedNodeInput:
    """Processed input for a single node with all necessary execution context"""
    node_id: str
    node_type: str
    system_instructions: str
    user_prompts: List[str]
    configuration: Dict[str, Any]
    input_data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    processing_timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass 
class WorkflowProcessingResult:
    """Result of processing an entire workflow"""
    workflow_id: str
    processed_nodes: Dict[str, ProcessedNodeInput]
    connection_graph: Dict[str, List[str]]  # node_id -> [connected_node_ids]
    execution_order: List[str]
    global_context: Dict[str, Any]
    validation_summary: Dict[str, List[str]]
    processing_mode: ProcessingMode


class WorkflowInputProcessor:
    """
    Main processor for translating frontend workflow data into backend execution context.
    
    Handles:
    - Node configuration processing
    - System rules generation
    - Input validation
    - Execution order optimization
    - Tool configuration validation
    """
    
    def __init__(self, processing_mode: ProcessingMode = ProcessingMode.PRODUCTION):
        self.processing_mode = processing_mode
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # System rule templates for different node types
        self.system_rule_templates = {
            NodeType.INPUT: self._get_input_system_rules,
            NodeType.BRAIN: self._get_brain_system_rules,
            NodeType.TOOL: self._get_tool_system_rules,
            NodeType.KNOWLEDGE: self._get_knowledge_system_rules,
            NodeType.OUTPUT: self._get_output_system_rules,
            NodeType.EXTERNAL_APP: self._get_external_app_system_rules,
        }
        
        # Configuration validators for each node type
        self.config_validators = {
            NodeType.INPUT: self._validate_input_config,
            NodeType.BRAIN: self._validate_brain_config,
            NodeType.TOOL: self._validate_tool_config,
            NodeType.KNOWLEDGE: self._validate_knowledge_config,
            NodeType.OUTPUT: self._validate_output_config,
            NodeType.EXTERNAL_APP: self._validate_external_app_config,
        }

    def process_workflow(self, workflow_data: Dict[str, Any]) -> WorkflowProcessingResult:
        """
        Process complete workflow data from frontend into backend execution format.
        
        Args:
            workflow_data: Raw workflow data from frontend containing nodes and connections
            
        Returns:
            WorkflowProcessingResult with processed nodes and execution metadata
        """
        workflow_id = workflow_data.get('workflow_id', 'unknown')
        nodes = workflow_data.get('nodes', [])
        connections = workflow_data.get('connections', [])
        
        self.logger.info(f"Processing workflow {workflow_id} with {len(nodes)} nodes, {len(connections)} connections")
        
        # Process individual nodes
        processed_nodes = {}
        validation_summary = {}
        
        for node_data in nodes:
            try:
                processed_node = self._process_single_node(node_data)
                processed_nodes[processed_node.node_id] = processed_node
                
                if processed_node.validation_errors:
                    validation_summary[processed_node.node_id] = processed_node.validation_errors
                    
            except Exception as e:
                error_msg = f"Failed to process node {node_data.get('node_id', 'unknown')}: {str(e)}"
                self.logger.error(error_msg)
                validation_summary[node_data.get('node_id', 'unknown')] = [error_msg]
        
        # Build connection graph and execution order
        connection_graph = self._build_connection_graph(connections)
        execution_order = self._calculate_execution_order(processed_nodes, connection_graph)
        
        # Create global context
        global_context = self._build_global_context(workflow_data, processed_nodes)
        
        result = WorkflowProcessingResult(
            workflow_id=workflow_id,
            processed_nodes=processed_nodes,
            connection_graph=connection_graph,
            execution_order=execution_order,
            global_context=global_context,
            validation_summary=validation_summary,
            processing_mode=self.processing_mode
        )
        
        self.logger.info(f"Workflow processing complete. {len(processed_nodes)} nodes processed, "
                        f"{len(validation_summary)} nodes with validation issues")
        
        return result

    def _process_single_node(self, node_data: Dict[str, Any]) -> ProcessedNodeInput:
        """Process a single node's configuration and inputs"""
        node_id = node_data.get('node_id')
        node_type_str = node_data.get('node_type', 'brain')
        user_configuration = node_data.get('user_configuration', {})
        
        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            self.logger.warning(f"Unknown node type '{node_type_str}', defaulting to brain")
            node_type = NodeType.BRAIN
        
        # Generate system instructions
        system_instructions = self._generate_system_instructions(node_type, user_configuration)
        
        # Extract user prompts
        user_prompts = self._extract_user_prompts(node_type, user_configuration)
        
        # Process input data
        input_data = self._process_input_data(node_type, user_configuration)
        
        # Validate configuration
        validation_errors = self._validate_node_configuration(node_type, user_configuration)
        
        # Build metadata
        metadata = {
            'original_node_type': node_type_str,
            'processing_mode': self.processing_mode.value,
            'has_user_prompts': len(user_prompts) > 0,
            'config_keys': list(user_configuration.keys())
        }
        
        return ProcessedNodeInput(
            node_id=node_id,
            node_type=node_type_str,
            system_instructions=system_instructions,
            user_prompts=user_prompts,
            configuration=user_configuration,
            input_data=input_data,
            metadata=metadata,
            validation_errors=validation_errors
        )

    def _generate_system_instructions(self, node_type: NodeType, config: Dict[str, Any]) -> str:
        """Generate system instructions based on node type and configuration"""
        if node_type in self.system_rule_templates:
            return self.system_rule_templates[node_type](config)
        else:
            return f"Execute {node_type.value} node functionality with provided configuration."

    def _extract_user_prompts(self, node_type: NodeType, config: Dict[str, Any]) -> List[str]:
        """Extract user prompts from configuration based on node type"""
        prompts = []
        
        # Common prompt fields
        if 'prompt' in config and config['prompt']:
            prompts.append(str(config['prompt']))
        
        if 'user_prompt' in config and config['user_prompt']:
            prompts.append(str(config['user_prompt']))
        
        # Node-specific prompt extraction
        if node_type == NodeType.INPUT:
            if 'input_text' in config and config['input_text']:
                prompts.append(str(config['input_text']))
        
        elif node_type == NodeType.BRAIN:
            if 'reasoning_prompt' in config and config['reasoning_prompt']:
                prompts.append(str(config['reasoning_prompt']))
        
        elif node_type == NodeType.TOOL:
            if 'tool_prompt' in config and config['tool_prompt']:
                prompts.append(str(config['tool_prompt']))
        
        return prompts

    def _process_input_data(self, node_type: NodeType, config: Dict[str, Any]) -> Any:
        """Process input data based on node type"""
        if node_type == NodeType.INPUT:
            return config.get('testData') or config.get('value')
        elif node_type == NodeType.TOOL:
            return config.get('params', {})
        elif node_type == NodeType.KNOWLEDGE:
            return config.get('query') or config.get('sources')
        else:
            return config.get('input_data')

    def _validate_node_configuration(self, node_type: NodeType, config: Dict[str, Any]) -> List[str]:
        """Validate node configuration and return list of errors"""
        if node_type in self.config_validators:
            return self.config_validators[node_type](config)
        return []

    def _build_connection_graph(self, connections: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build connection graph from connection data"""
        graph = {}
        
        for conn in connections:
            from_node = conn.get('from')
            to_node = conn.get('to')
            
            if from_node and to_node:
                if from_node not in graph:
                    graph[from_node] = []
                graph[from_node].append(to_node)
        
        return graph

    def _calculate_execution_order(self, processed_nodes: Dict[str, ProcessedNodeInput], 
                                  connection_graph: Dict[str, List[str]]) -> List[str]:
        """Calculate optimal execution order using topological sort"""
        # Build in-degree count
        in_degree = {node_id: 0 for node_id in processed_nodes.keys()}
        
        for from_node, to_nodes in connection_graph.items():
            for to_node in to_nodes:
                if to_node in in_degree:
                    in_degree[to_node] += 1
        
        # Topological sort
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        execution_order = []
        
        while queue:
            current = queue.pop(0)
            execution_order.append(current)
            
            # Reduce in-degree for connected nodes
            for connected in connection_graph.get(current, []):
                if connected in in_degree:
                    in_degree[connected] -= 1
                    if in_degree[connected] == 0:
                        queue.append(connected)
        
        return execution_order

    def _build_global_context(self, workflow_data: Dict[str, Any], 
                             processed_nodes: Dict[str, ProcessedNodeInput]) -> Dict[str, Any]:
        """Build global context for workflow execution"""
        return {
            'workflow_id': workflow_data.get('workflow_id'),
            'processing_timestamp': datetime.now().isoformat(),
            'processing_mode': self.processing_mode.value,
            'node_count': len(processed_nodes),
            'tool_nodes': [n.node_id for n in processed_nodes.values() if n.node_type == 'tool'],
            'brain_nodes': [n.node_id for n in processed_nodes.values() if n.node_type == 'brain'],
            'input_nodes': [n.node_id for n in processed_nodes.values() if n.node_type == 'input'],
            'output_nodes': [n.node_id for n in processed_nodes.values() if n.node_type == 'output'],
            'execution_metadata': {
                'total_prompts': sum(len(n.user_prompts) for n in processed_nodes.values()),
                'configured_nodes': sum(1 for n in processed_nodes.values() if n.configuration),
                'nodes_with_errors': sum(1 for n in processed_nodes.values() if n.validation_errors)
            }
        }

    # System rule generators for different node types
    def _get_input_system_rules(self, config: Dict[str, Any]) -> str:
        """Generate system rules for input nodes"""
        input_type = config.get('inputType', 'text')
        
        base_rules = "ROLE: Input Processing Node\n\n"
        base_rules += "OBJECTIVE: Process and validate user input, preparing it for downstream workflow execution.\n\n"
        
        if input_type == 'text':
            base_rules += "INPUT TYPE: Text input\n"
            base_rules += "PROCESSING: Validate text format, check for required fields, sanitize content.\n"
        elif input_type == 'file':
            base_rules += "INPUT TYPE: File input\n" 
            base_rules += "PROCESSING: Validate file format, extract metadata, prepare file content for processing.\n"
        elif input_type == 'form':
            base_rules += "INPUT TYPE: Form data\n"
            base_rules += "PROCESSING: Validate form fields, check required inputs, structure data for workflow.\n"
        
        base_rules += "\nOUTPUT FORMAT: Structured data object ready for downstream processing.\n"
        base_rules += "ERROR HANDLING: Report validation errors with specific field information."
        
        return base_rules

    def _get_brain_system_rules(self, config: Dict[str, Any]) -> str:
        """Generate system rules for brain nodes"""
        system_instructions = config.get('systemInstructions', '')
        mode = config.get('mode', 'reasoning')
        temperature = config.get('temperature', 0.7)
        
        if system_instructions:
            # User provided custom instructions - use those as primary
            rules = f"CORE INSTRUCTIONS: {system_instructions}\n\n"
        else:
            # Generate default instructions based on mode
            rules = "ROLE: AI Brain Node\n\n"
            rules += "OBJECTIVE: Analyze input and provide intelligent reasoning and decision-making.\n\n"
        
        rules += f"EXECUTION MODE: {mode.upper()}\n"
        
        if mode == 'reasoning':
            rules += "APPROACH: Use logical analysis, break down complex problems, provide step-by-step reasoning.\n"
        elif mode == 'creative':
            rules += "APPROACH: Generate creative solutions, think outside the box, explore innovative approaches.\n"
        elif mode == 'analytical':
            rules += "APPROACH: Deep data analysis, pattern recognition, statistical insights.\n"
        elif mode == 'conversational':
            rules += "APPROACH: Natural conversation, context awareness, human-like interaction.\n"
        
        rules += f"\nCREATIVITY LEVEL: {temperature} (0.0 = deterministic, 1.0 = highly creative)\n"
        
        # Add tool selection instructions if this brain is connected to tools
        rules += "\nTOOL SELECTION: When multiple tools are available:\n"
        rules += "1. Analyze the user's request and context\n"
        rules += "2. Identify the most appropriate tool(s) based on capabilities and requirements\n"
        rules += "3. Consider tool dependencies and execution order\n"
        rules += "4. Select tools that best fulfill the user's intent\n"
        
        rules += "\nOUTPUT FORMAT: Clear reasoning with selected tools and parameters if applicable."
        
        return rules

    def _get_tool_system_rules(self, config: Dict[str, Any]) -> str:
        """Generate system rules for tool nodes"""
        tool_name = config.get('tool', 'unknown')
        action = config.get('action', 'execute')
        mock = config.get('mock', False)
        
        rules = f"ROLE: Tool Execution Node - {tool_name.upper()}\n\n"
        rules += f"TOOL: {tool_name}\n"
        rules += f"ACTION: {action}\n"
        rules += f"MODE: {'MOCK' if mock else 'LIVE'}\n\n"
        
        rules += f"OBJECTIVE: Execute {tool_name} {action} with provided parameters.\n\n"
        
        if mock:
            rules += "EXECUTION: Simulate tool execution with realistic mock responses for testing.\n"
        else:
            rules += "EXECUTION: Perform actual tool operation with external services.\n"
        
        rules += "ERROR HANDLING: Gracefully handle tool failures, provide actionable error messages.\n"
        rules += "OUTPUT FORMAT: Structured result with execution status and tool response data."
        
        return rules

    def _get_knowledge_system_rules(self, config: Dict[str, Any]) -> str:
        """Generate system rules for knowledge nodes"""
        max_results = config.get('maxResults', 10)
        
        rules = "ROLE: Knowledge Base Node\n\n"
        rules += "OBJECTIVE: Search and retrieve relevant information from knowledge base.\n\n"
        rules += f"SEARCH PARAMETERS: Maximum {max_results} results\n"
        rules += "PROCESSING: Semantic search, relevance ranking, context extraction.\n"
        rules += "OUTPUT FORMAT: Ranked list of relevant knowledge entries with context."
        
        return rules

    def _get_output_system_rules(self, config: Dict[str, Any]) -> str:
        """Generate system rules for output nodes"""
        output_format = config.get('format', 'text')
        include_metadata = config.get('includeMetadata', False)
        
        rules = "ROLE: Output Formatting Node\n\n"
        rules += "OBJECTIVE: Format and present final workflow results.\n\n"
        rules += f"OUTPUT FORMAT: {output_format.upper()}\n"
        rules += f"METADATA: {'Include' if include_metadata else 'Exclude'} execution metadata\n\n"
        
        if output_format == 'json':
            rules += "FORMATTING: Structure data as valid JSON with proper escaping.\n"
        elif output_format == 'markdown':
            rules += "FORMATTING: Format as readable Markdown with proper headers and structure.\n"
        elif output_format == 'html':
            rules += "FORMATTING: Generate clean HTML with semantic markup.\n"
        else:
            rules += "FORMATTING: Present as clear, readable text.\n"
        
        rules += "QUALITY: Ensure output is well-formatted, complete, and user-friendly."
        
        return rules

    def _get_external_app_system_rules(self, config: Dict[str, Any]) -> str:
        """Generate system rules for external app nodes"""
        app = config.get('app', 'unknown')
        
        rules = f"ROLE: External App Integration - {app.upper()}\n\n"
        rules += f"APPLICATION: {app}\n"
        rules += "OBJECTIVE: Integrate with external application for automated workflows.\n\n"
        
        # Add app-specific instructions
        app_instructions = {
            'gmail': 'EMAIL OPERATIONS: Handle email composition, sending, and inbox management.',
            'slack': 'MESSAGING OPERATIONS: Manage Slack channels, messages, and team communication.',
            'jira': 'ISSUE MANAGEMENT: Create, update, and track JIRA issues and projects.',
            'notion': 'KNOWLEDGE MANAGEMENT: Manage Notion pages, databases, and team wikis.',
            'github': 'CODE COLLABORATION: Handle GitHub issues, pull requests, and repository management.'
        }
        
        if app in app_instructions:
            rules += f"FUNCTIONALITY: {app_instructions[app]}\n"
        
        rules += "ERROR HANDLING: Handle API errors, rate limits, and authentication issues.\n"
        rules += "OUTPUT FORMAT: Structured response with operation status and result data."
        
        return rules

    # Configuration validators
    def _validate_input_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate input node configuration"""
        errors = []
        
        input_type = config.get('inputType')
        if not input_type:
            errors.append("Input type is required")
        elif input_type not in ['text', 'file', 'form', 'button', 'multiple-choice']:
            errors.append(f"Invalid input type: {input_type}")
        
        return errors

    def _validate_brain_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate brain node configuration"""
        errors = []
        
        temperature = config.get('temperature')
        if temperature is not None:
            try:
                temp_float = float(temperature)
                if not 0.0 <= temp_float <= 1.0:
                    errors.append("Temperature must be between 0.0 and 1.0")
            except (ValueError, TypeError):
                errors.append("Temperature must be a number")
        
        max_tokens = config.get('maxTokens')
        if max_tokens is not None:
            try:
                tokens_int = int(max_tokens)
                if not 1 <= tokens_int <= 4096:
                    errors.append("Max tokens must be between 1 and 4096")
            except (ValueError, TypeError):
                errors.append("Max tokens must be an integer")
        
        return errors

    def _validate_tool_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate tool node configuration"""
        errors = []
        
        tool = config.get('tool')
        if not tool:
            errors.append("Tool selection is required")
        
        action = config.get('action')
        if not action:
            errors.append("Tool action is required")
        
        # Validate params JSON if present
        params = config.get('params')
        if params and isinstance(params, str):
            try:
                json.loads(params)
            except json.JSONDecodeError:
                errors.append("Tool parameters must be valid JSON")
        
        return errors

    def _validate_knowledge_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate knowledge node configuration"""
        errors = []
        
        max_results = config.get('maxResults')
        if max_results is not None:
            try:
                results_int = int(max_results)
                if not 1 <= results_int <= 50:
                    errors.append("Max results must be between 1 and 50")
            except (ValueError, TypeError):
                errors.append("Max results must be an integer")
        
        return errors

    def _validate_output_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate output node configuration"""
        errors = []
        
        output_format = config.get('format', 'text')
        if output_format not in ['text', 'json', 'markdown', 'html']:
            errors.append(f"Invalid output format: {output_format}")
        
        return errors

    def _validate_external_app_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate external app node configuration"""
        errors = []
        
        app = config.get('app')
        if not app:
            errors.append("External app selection is required")
        
        return errors