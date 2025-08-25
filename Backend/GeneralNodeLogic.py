"""
General Node Logic Module - Enhanced for Weev Platform

This module contains the base class and common functionality for all node types in the system.
Designed for the "Figma for AI Agents" vision with zero-setup testing and intelligent workflows.
"""

import os
import uuid
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import asyncio
import logging
from openai import OpenAI

# Enhanced data structures for holistic workflow management
@dataclass
class PreviousNodeOutput:
    node_id: str
    node_type: str
    data: Any
    timestamp: float
    connection_type: str  # 'direct' or 'conditional'
    success: bool = True
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None

@dataclass
class WorkflowMemory:
    """Maintains context across the entire workflow"""
    workflow_id: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    global_context: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    execution_path: List[str] = field(default_factory=list)
    
    def add_to_history(self, node_id: str, node_type: str, input_data: Any, output_data: Any):
        """Add node execution to conversation history"""
        self.conversation_history.append({
            'node_id': node_id,
            'node_type': node_type,
            'input': input_data,
            'output': output_data,
            'timestamp': datetime.now().isoformat()
        })
        self.execution_path.append(node_id)
    
    def get_relevant_context(self, max_history: int = 5) -> str:
        """Get recent conversation context for LLM"""
        recent_history = self.conversation_history[-max_history:]
        context_lines = []
        
        for entry in recent_history:
            context_lines.append(f"Previous {entry['node_type']}: {entry['output']}")
        
        return "\n".join(context_lines)

@dataclass
class NodeInputs:
    # Core 3 inputs as specified
    system_rules: str
    user_configuration: Dict[str, Any]
    previous_node_data: List[PreviousNodeOutput]
    
    # Enhanced holistic inputs
    workflow_memory: WorkflowMemory
    execution_context: Dict[str, Any] = field(default_factory=dict)
    streaming_callback: Optional[Callable[[str], None]] = None

@dataclass
class NodeOutput:
    node_id: str
    node_type: str
    data: Any
    timestamp: float
    metadata: Dict[str, Any]
    
    # Enhanced outputs for workflow intelligence
    next_suggested_nodes: List[str] = field(default_factory=list)
    confidence_score: Optional[float] = None
    tool_calls_made: List[str] = field(default_factory=list)
    memory_updates: Dict[str, Any] = field(default_factory=dict)
    debug_info: Dict[str, Any] = field(default_factory=dict)

class NodeExecutionMode(Enum):
    """Different execution modes for different use cases"""
    PROTOTYPE = "prototype"  # Fast, cost-effective for testing
    PRODUCTION = "production"  # Full featured, reliable
    DEBUG = "debug"  # Detailed logging and inspection

class GeneralNodeLogic:
    """
    Enhanced General Node Logic for Weev's AI Agent Workflow Platform
    
    Key enhancements for holistic operation:
    1. Workflow memory and context management
    2. Intelligent agent-first design
    3. Real-time streaming with debugging
    4. Multi-model support and optimization
    5. Production-ready error handling
    """
    
    def __init__(self, execution_mode: NodeExecutionMode = NodeExecutionMode.PROTOTYPE):
        self.execution_mode = execution_mode
        self.logger = self._setup_logging()
        
        # Initialize LLM provider with error handling
        try:
            api_key = os.environ.get('NVIDIA_API_KEY')
            if not api_key:
                raise ValueError("NVIDIA_API_KEY environment variable not set")
            
            self.llm_provider = OpenAI(
                api_key=api_key,
                base_url='https://integrate.api.nvidia.com/v1',
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM provider: {str(e)}")
            raise
        
        # Model selection based on execution mode
        self.model_config = self._get_model_config()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging based on execution mode"""
        logger = logging.getLogger(f"weev_node_{self.execution_mode.value}")
        
        if self.execution_mode == NodeExecutionMode.DEBUG:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
            
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _get_model_config(self) -> Dict[str, Any]:
        """Get model configuration based on execution mode"""
        configs = {
            NodeExecutionMode.PROTOTYPE: {
                'model': 'moonshotai/kimi-k2-instruct',
                'temperature': 0.7,
                'max_tokens': 2048,
                'top_p': 0.9
            },
            NodeExecutionMode.PRODUCTION: {
                'model': 'moonshotai/kimi-k2-instruct',
                'temperature': 0.6,
                'max_tokens': 4096,
                'top_p': 0.9
            },
            NodeExecutionMode.DEBUG: {
                'model': 'moonshotai/kimi-k2-instruct',
                'temperature': 0.5,
                'max_tokens': 1024,
                'top_p': 0.8
            }
        }
        return configs[self.execution_mode]
    
    async def execute_node(self, inputs: NodeInputs) -> NodeOutput:
        """
        Enhanced execution method with holistic workflow management
        """
        start_time = datetime.now()
        node_id = self._generate_node_id()
        
        try:
            self.logger.info(f"Starting node execution: {node_id}")
            
            # Step 1: Build intelligent context-aware prompt
            complete_prompt = self._build_intelligent_prompt(inputs)
            
            if self.execution_mode == NodeExecutionMode.DEBUG:
                self.logger.debug(f"Complete prompt: {complete_prompt[:200]}...")
            
            # Step 2: Execute with enhanced streaming and error handling
            result = await self._execute_with_intelligent_streaming(
                complete_prompt, 
                inputs.user_configuration,
                inputs.streaming_callback
            )
            
            # Step 3: Process result with workflow intelligence
            node_output = await self._format_intelligent_output(
                result, inputs, node_id, start_time
            )
            
            # Step 4: Update workflow memory
            inputs.workflow_memory.add_to_history(
                node_id, 
                node_output.node_type,
                inputs.user_configuration,
                result
            )
            
            self.logger.info(f"Node execution completed: {node_id}")
            return node_output
            
        except Exception as e:
            self.logger.error(f"Node execution failed: {str(e)}")
            return self._create_error_output(node_id, str(e), start_time)
    
    def _build_intelligent_prompt(self, inputs: NodeInputs) -> str:
        """
        Build an intelligent, context-aware prompt that leverages workflow memory
        """
        # Get relevant conversation context
        conversation_context = inputs.workflow_memory.get_relevant_context()
        
        prompt = f"""
SYSTEM RULES (Your Core Instructions):
{inputs.system_rules}

WORKFLOW CONTEXT & MEMORY:
Workflow ID: {inputs.workflow_memory.workflow_id}
Execution Path: {' -> '.join(inputs.workflow_memory.execution_path[-5:])}
Recent Conversation:
{conversation_context}

Global Context: {json.dumps(inputs.workflow_memory.global_context, indent=2)}

USER CONFIGURATION:
{self._format_user_configuration(inputs.user_configuration)}

IMMEDIATE PREVIOUS NODE DATA:
{self._format_previous_node_data(inputs.previous_node_data)}

IMPORTANT: You are part of an intelligent AI agent workflow. Consider the entire conversation context, not just immediate inputs. Make decisions that advance the workflow toward the user's ultimate goal.

Execute your node function now:
"""
        return prompt.strip()
    
    async def _execute_with_intelligent_streaming(
        self, 
        prompt: str, 
        user_config: Dict[str, Any],
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Execute with intelligent streaming, error recovery, and real-time feedback
        """
        try:
            # Merge user config with model defaults
            model_params = {**self.model_config, **user_config}
            
            completion = self.llm_provider.chat.completions.create(
                model=model_params['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=model_params.get('temperature', 0.6),
                top_p=model_params.get('top_p', 0.9),
                max_tokens=model_params.get('max_tokens', 4096),
                stream=True
            )
            
            full_response = ""
            chunk_count = 0
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    chunk_count += 1
                    
                    # Enhanced streaming with callbacks
                    if streaming_callback:
                        streaming_callback(content)
                    else:
                        await self._stream_to_frontend(content)
                    
                    # Debug mode: log streaming progress
                    if self.execution_mode == NodeExecutionMode.DEBUG and chunk_count % 10 == 0:
                        self.logger.debug(f"Streamed {chunk_count} chunks, {len(full_response)} chars")
            
            self.logger.info(f"Streaming completed: {chunk_count} chunks, {len(full_response)} characters")
            return full_response
            
        except Exception as e:
            self.logger.error(f"Error in LLM execution: {str(e)}")
            
            # Intelligent error recovery
            if "rate_limit" in str(e).lower():
                await asyncio.sleep(1)
                return await self._execute_with_intelligent_streaming(prompt, user_config, streaming_callback)
            
            return f"Error: {str(e)}"
    
    async def _format_intelligent_output(
        self, 
        response: str, 
        inputs: NodeInputs, 
        node_id: str,
        start_time: datetime
    ) -> NodeOutput:
        """
        Format output with intelligent analysis and workflow suggestions
        """
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Analyze response for workflow intelligence
        next_nodes = self._analyze_next_nodes(response, inputs)
        confidence = self._calculate_confidence(response, inputs)
        memory_updates = self._extract_memory_updates(response, inputs)
        
        return NodeOutput(
            node_id=node_id,
            node_type="general",  # Will be overridden by specific nodes
            data=response,
            timestamp=datetime.now().timestamp(),
            next_suggested_nodes=next_nodes,
            confidence_score=confidence,
            memory_updates=memory_updates,
            metadata={
                'execution_mode': self.execution_mode.value,
                'execution_time_ms': execution_time,
                'model_used': self.model_config['model'],
                'system_rules_hash': hash(inputs.system_rules),
                'workflow_id': inputs.workflow_memory.workflow_id,
                'previous_nodes_processed': len(inputs.previous_node_data),
                'conversation_length': len(inputs.workflow_memory.conversation_history)
            },
            debug_info={
                'prompt_length': len(self._build_intelligent_prompt(inputs)),
                'response_length': len(response),
                'streaming_chunks': response.count(' ') + 1,  # Approximate
                'memory_context_used': bool(inputs.workflow_memory.conversation_history)
            } if self.execution_mode == NodeExecutionMode.DEBUG else {}
        )
    
    def _analyze_next_nodes(self, response: str, inputs: NodeInputs) -> List[str]:
        """Analyze response to suggest next nodes in workflow"""
        suggestions = []
        
        # Simple keyword-based analysis (can be enhanced with ML)
        if any(word in response.lower() for word in ['search', 'find', 'lookup', 'information']):
            suggestions.append('KnowledgeBaseNode')
        
        if any(word in response.lower() for word in ['decide', 'choose', 'analyze', 'think']):
            suggestions.append('BrainNode')
            
        if any(word in response.lower() for word in ['format', 'output', 'result', 'final']):
            suggestions.append('OutputNode')
            
        return suggestions
    
    def _calculate_confidence(self, response: str, inputs: NodeInputs) -> float:
        """Calculate confidence score based on response quality"""
        base_confidence = 0.7
        
        # Increase confidence for longer, detailed responses
        if len(response) > 200:
            base_confidence += 0.1
            
        # Increase confidence if workflow context was used
        if inputs.workflow_memory.conversation_history:
            base_confidence += 0.1
            
        # Decrease confidence for error responses
        if 'error' in response.lower() or 'sorry' in response.lower():
            base_confidence -= 0.3
            
        return min(1.0, max(0.0, base_confidence))
    
    def _extract_memory_updates(self, response: str, inputs: NodeInputs) -> Dict[str, Any]:
        """Extract information that should be stored in workflow memory"""
        updates = {}
        
        # Extract key entities or facts mentioned in response
        # This is a simple implementation - can be enhanced with NLP
        if 'user wants' in response.lower():
            updates['user_intent'] = response
        
        if any(word in response.lower() for word in ['remember', 'important', 'key']):
            updates['important_info'] = response[:200]
            
        return updates
    
    def _create_error_output(self, node_id: str, error_message: str, start_time: datetime) -> NodeOutput:
        """Create standardized error output"""
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return NodeOutput(
            node_id=node_id,
            node_type="error",
            data=f"Node execution failed: {error_message}",
            timestamp=datetime.now().timestamp(),
            confidence_score=0.0,
            metadata={
                'execution_mode': self.execution_mode.value,
                'execution_time_ms': execution_time,
                'error': True,
                'error_message': error_message
            }
        )
    
    # Keep existing helper methods with minor enhancements
    def _format_user_configuration(self, config: Dict[str, Any]) -> str:
        """Format user configuration into readable text"""
        if not config:
            return "No user configuration provided"
            
        formatted_lines = []
        for key, value in config.items():
            if key not in ['temperature', 'max_tokens', 'top_p']:  # Skip internal params
                formatted_lines.append(f"{key}: {json.dumps(value)}")
        
        return "\n".join(formatted_lines) if formatted_lines else "No user-specific configuration"
    
    def _format_previous_node_data(self, previous_data: List[PreviousNodeOutput]) -> str:
        """Format previous node outputs into readable context"""
        if not previous_data:
            return "No immediate previous node data"
        
        formatted_nodes = []
        for node in previous_data:
            status = "✓" if node.success else "✗"
            node_info = f"""
{status} From {node.node_type} ({node.node_id}):
{json.dumps(node.data, indent=2)}
{f"Error: {node.error_message}" if node.error_message else ""}
---"""
            formatted_nodes.append(node_info)
        
        return "\n".join(formatted_nodes)
    
    async def _stream_to_frontend(self, content: str) -> None:
        """Stream content to frontend - enhanced for production"""
        if self.execution_mode == NodeExecutionMode.DEBUG:
            print(f"[STREAM] {content}", end='', flush=True)
        else:
            print(content, end='', flush=True)
    
    def _generate_node_id(self) -> str:
        """Generate a UUID-based node ID for better uniqueness"""
        return f"node_{str(uuid.uuid4())[:8]}"