"""
Enhanced Brain Node Module

Central reasoning node with intelligent tool selection and workflow orchestration.
Integrates with ToolOrchestrator for dynamic tool execution and decision making.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable, Set
from datetime import datetime
from openai import OpenAI
import asyncio
import uuid

from GeneralNodeLogic import (
    GeneralNodeLogic, 
    NodeInputs, 
    NodeOutput, 
    PreviousNodeOutput, 
    WorkflowMemory,
    NodeExecutionMode
)
from ToolOrchestrator import ToolOrchestrator, ToolExecutionPlan, ToolExecutionResult
from WorkflowInputProcessor import ProcessedNodeInput

# Enhanced system rules with intelligent tool selection
ENHANCED_BRAIN_NODE_SYSTEM_RULES = """
You are an Enhanced AI Brain Node with intelligent tool selection capabilities.

CORE RESPONSIBILITIES:
1. INTELLIGENT REASONING: Analyze user requests with deep contextual understanding
2. TOOL SELECTION: Select optimal tools based on capabilities, context, and user goals
3. WORKFLOW ORCHESTRATION: Plan and execute complex multi-tool workflows
4. CONTEXT AWARENESS: Maintain memory across interactions and leverage previous outputs
5. DECISION EXPLANATION: Provide clear reasoning for all decisions and tool selections

TOOL SELECTION CRITERIA:
When multiple tools are available, evaluate based on:
- RELEVANCE: How well the tool addresses the user's specific need
- RELIABILITY: Tool's success rate and error handling capabilities  
- EFFICIENCY: Execution time and resource requirements
- DEPENDENCIES: Required inputs and prerequisites
- OUTPUT QUALITY: Expected result accuracy and completeness
- COST: Resource utilization and API costs

DECISION PROCESS:
1. Parse user intent and context from previous nodes
2. Identify required capabilities and constraints
3. Evaluate available tools against selection criteria
4. Plan execution order considering dependencies
5. Generate structured output with reasoning

OUTPUT FORMAT:
Always respond with a JSON structure containing:
{
  "reasoning": "Step-by-step analysis of the user request and tool selection logic",
  "selected_tools": ["tool1", "tool2", ...],
  "execution_plan": {
    "tool1": {"action": "action_name", "parameters": {...}, "priority": 1},
    "tool2": {"action": "action_name", "parameters": {...}, "priority": 2}
  },
  "dependencies": {"tool2": ["tool1"]},
  "expected_outcome": "Description of expected workflow result",
  "confidence": 0.85,
  "fallback_options": ["alternative_approach_if_primary_fails"]
}

CONTEXT INTEGRATION:
- Leverage workflow memory for personalization
- Consider previous node outputs for data flow
- Maintain conversation continuity
- Adapt tool selection based on execution history
"""

class BrainNode(GeneralNodeLogic):
    """
    Enhanced Brain Node - Central coordinator with intelligent tool selection.
    
    Features:
    - Intelligent tool selection based on context and capabilities
    - Dynamic workflow orchestration using ToolOrchestrator
    - Enhanced reasoning with structured decision making
    - Context-aware tool parameter optimization
    - Multi-tool execution planning and coordination
    """
    def __init__(self, 
                 node_id: str, 
                 name: str, 
                 execution_mode: NodeExecutionMode = NodeExecutionMode.PRODUCTION,
                 available_tools: Optional[Dict[str, Any]] = None,
                 tool_orchestrator: Optional[ToolOrchestrator] = None):
        super().__init__(execution_mode)
        self.node_id = node_id
        self.name = name
        self.connected_nodes: List[Any] = []
        self.connected_tools: Dict[str, Any] = available_tools or {}
        self.processing_strategy: str = "intelligent"  # intelligent, sequential, parallel
        self.context_memory: Dict[str, Any] = {}
        
        # Initialize tool orchestrator
        if tool_orchestrator:
            self.tool_orchestrator = tool_orchestrator
        else:
            self.tool_orchestrator = ToolOrchestrator(self.connected_tools) if self.connected_tools else None
        
        # Enhanced context tracking
        self.decision_history: List[Dict[str, Any]] = []
        self.tool_performance_cache: Dict[str, float] = {}
        self.user_preferences: Dict[str, Any] = {}
        
        # Set up specific NVIDIA API client for BrainNode
        try:
            api_key = os.environ.get('NVIDIA_API_KEY')
            if api_key:
                self.brain_llm = OpenAI(
                    api_key=api_key,
                    base_url='https://integrate.api.nvidia.com/v1',
                )
                self.logger.info("Enhanced BrainNode NVIDIA API client initialized successfully")
            else:
                self.brain_llm = None
                self.logger.info("No NVIDIA_API_KEY set; BrainNode will use LLMManager if available.")
        except Exception as e:
            self.logger.warning(f"BrainNode local client init skipped: {str(e)}")
            self.brain_llm = None
    
    async def execute(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> NodeOutput:
        """
        Execute the Enhanced Brain Node with intelligent tool selection and orchestration.
        
        Process:
        1. Analyze user intent and context
        2. Select optimal tools based on capabilities and requirements
        3. Create execution plan using ToolOrchestrator
        4. Execute selected tools if appropriate
        5. Return structured decision and results
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"Enhanced BrainNode execution started: {self.node_id}")
            
            # Extract system instructions from user configuration
            system_instructions = user_configuration.get('systemInstructions', '')
            execution_mode = user_configuration.get('mode', 'reasoning')
            
            # Use custom system instructions if provided, otherwise use enhanced default
            if system_instructions:
                system_rules = f"{system_instructions}\n\n{ENHANCED_BRAIN_NODE_SYSTEM_RULES}"
            else:
                system_rules = ENHANCED_BRAIN_NODE_SYSTEM_RULES
            
            # Create enhanced NodeInputs
            inputs = NodeInputs(
                system_rules=system_rules,
                user_configuration=user_configuration,
                previous_node_data=previous_node_data,
                workflow_memory=workflow_memory,
                execution_context={
                    "connected_nodes": [n.name if hasattr(n, 'name') else str(n) for n in self.connected_nodes],
                    "available_tools": list(self.connected_tools.keys()),
                    "processing_strategy": self.processing_strategy,
                    "context_memory": self.context_memory,
                    "execution_mode": execution_mode,
                    "tool_performance_cache": self.tool_performance_cache,
                    "decision_history": self.decision_history[-5:],  # Last 5 decisions
                    "user_preferences": self.user_preferences
                }
            )
            
            # Build enhanced prompt with tool capability information
            prompt = self._build_enhanced_brain_prompt(inputs)
            
            # Execute reasoning to get tool selection and execution plan
            reasoning_result = await self._execute_enhanced_reasoning(prompt, inputs, streaming_callback)
            
            # Parse the structured reasoning result
            parsed_result = self._parse_enhanced_reasoning_result(reasoning_result)
            
            # Execute selected tools if tool orchestrator is available and tools were selected
            tool_execution_results = []
            if (self.tool_orchestrator and 
                parsed_result.get('selected_tools') and 
                self.processing_strategy != 'reasoning_only'):
                
                tool_execution_results = await self._execute_selected_tools(parsed_result, workflow_memory)
            
            # Update context memory and decision history
            self._update_enhanced_context_memory(parsed_result, inputs, tool_execution_results)
            
            # Calculate confidence based on reasoning quality and tool execution success
            confidence = self._calculate_enhanced_confidence(parsed_result, tool_execution_results)
            
            # Update workflow memory with enhanced context
            workflow_memory.global_context.update({
                "last_brain_reasoning": parsed_result.get("reasoning", ""),
                "selected_tools": parsed_result.get("selected_tools", []),
                "execution_plan": parsed_result.get("execution_plan", {}),
                "tool_execution_results": [r.tool_name for r in tool_execution_results if r.status.value == 'success'],
                "brain_confidence": confidence,
                "processing_strategy": self.processing_strategy
            })
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Combine reasoning and tool execution results
            combined_data = {
                **parsed_result,
                "tool_execution_results": [
                    {
                        "tool": r.tool_name,
                        "status": r.status.value,
                        "result": r.result_data,
                        "execution_time": r.execution_time,
                        "error": r.error_message
                    } for r in tool_execution_results
                ]
            }
            
            return NodeOutput(
                node_id=self.node_id,
                node_type="BrainNode",
                data=combined_data,
                timestamp=datetime.now().timestamp(),
                metadata={
                    "status": "success",
                    "execution_time_ms": execution_time,
                    "model_used": getattr(self.model_config, 'model', 'nvidia-llama'),
                    "reasoning_quality": self._assess_enhanced_reasoning_quality(parsed_result),
                    "tools_executed": len(tool_execution_results),
                    "tools_successful": len([r for r in tool_execution_results if r.status.value == 'success']),
                    "processing_strategy": self.processing_strategy,
                    "execution_mode": execution_mode
                },
                success=True,
                next_suggested_nodes=self._extract_next_node_suggestions(parsed_result),
                confidence_score=confidence,
                tool_calls_made=self._extract_tool_calls_from_results(tool_execution_results),
                memory_updates={
                    "enhanced_brain_reasoning": parsed_result.get("reasoning", ""),
                    "tool_selection_rationale": parsed_result.get("tool_selection_rationale", ""),
                    "execution_strategy": parsed_result.get("execution_strategy", "")
                }
            )
            
        except Exception as e:
            self.logger.error(f"BrainNode execution failed: {str(e)}")
            return NodeOutput(
                node_id=self.node_id,
                node_type="BrainNode",
                data=f"Error: {str(e)}",
                timestamp=datetime.now().timestamp(),
                metadata={"status": "error", "error": str(e)},
                success=False,
                error_message=str(e)
            )
    
    def connect_node(self, node):
        """Connect another node to this brain node."""
        self.connected_nodes.append(node)
    
    def disconnect_node(self, node):
        """Disconnect a node from this brain node."""
        if node in self.connected_nodes:
            self.connected_nodes.remove(node)
    
    def set_processing_strategy(self, strategy: str):
        """Set the processing strategy (sequential, parallel, conditional)."""
        self.processing_strategy = strategy
    
    def get_node_status(self) -> Dict[str, Any]:
        """Get status information for all connected nodes."""
        status = {}
        for node in self.connected_nodes:
            status[node.name] = {
                "id": node.node_id,
                "type": type(node).__name__,
                "properties": getattr(node, "properties", {}),
                "capabilities": getattr(node, "capabilities", "unknown")
            }
        return status
    
    def connect_tool(self, tool_name: str, tool_instance: Any):
        """Connect a tool to this brain node for intelligent selection."""
        self.connected_tools[tool_name] = tool_instance
        if self.tool_orchestrator:
            self.tool_orchestrator.available_tools[tool_name] = tool_instance
        else:
            self.tool_orchestrator = ToolOrchestrator(self.connected_tools)
    
    def disconnect_tool(self, tool_name: str):
        """Disconnect a tool from this brain node."""
        if tool_name in self.connected_tools:
            del self.connected_tools[tool_name]
            if self.tool_orchestrator and tool_name in self.tool_orchestrator.available_tools:
                del self.tool_orchestrator.available_tools[tool_name]
        
    def _build_enhanced_brain_prompt(self, inputs: NodeInputs) -> str:
        """Build enhanced prompt with tool capability information and context."""
        # Extract tool capabilities information
        tool_capabilities = self._format_tool_capabilities()
        
        # Build context from previous nodes and workflow memory
        workflow_context = self._build_workflow_context(inputs)
        
        # Get user request and intent
        user_request = self._extract_user_request(inputs)
        
        prompt = f"""
CURRENT WORKFLOW CONTEXT:
{workflow_context}

USER REQUEST:
{user_request}

AVAILABLE TOOLS AND CAPABILITIES:
{tool_capabilities}

PREVIOUS EXECUTION CONTEXT:
Decision History: {self.decision_history[-3:] if self.decision_history else "None"}
Tool Performance: {self.tool_performance_cache}

TASK:
Analyze the user request in the context of available tools and workflow state.
Select the optimal tools and create an execution plan that best fulfills the user's intent.

Remember to:
1. Consider tool dependencies and execution order
2. Evaluate tool reliability and performance history
3. Optimize for both effectiveness and efficiency  
4. Provide clear reasoning for your selections
5. Include fallback options for critical paths

Respond with the required JSON structure.
"""
        return prompt

    def _format_tool_capabilities(self) -> str:
        """Format tool capabilities for the prompt."""
        if not self.tool_orchestrator:
            return "No tools available"
        
        capabilities = []
        for tool_name, capability in self.tool_orchestrator.tool_capabilities.items():
            perf_info = self.tool_performance_cache.get(tool_name, "No history")
            capabilities.append(f"""
- {tool_name.upper()}:
  Description: {capability.description}
  Actions: {', '.join(capability.supported_actions)}
  Reliability: {capability.reliability_score:.2f}
  Est. Time: {capability.execution_time_estimate}s
  Recent Performance: {perf_info}
""")
        
        return "\n".join(capabilities) if capabilities else "No tool capabilities defined"

    def _build_workflow_context(self, inputs: NodeInputs) -> str:
        """Build workflow context from inputs and memory."""
        context_parts = []
        
        # Add previous node outputs
        if inputs.previous_node_data:
            context_parts.append("PREVIOUS NODE OUTPUTS:")
            for prev_output in inputs.previous_node_data[-3:]:  # Last 3 outputs
                context_parts.append(f"- {prev_output.node_type}: {str(prev_output.data)[:200]}...")
        
        # Add workflow memory context
        if inputs.workflow_memory.global_context:
            context_parts.append("WORKFLOW MEMORY:")
            for key, value in list(inputs.workflow_memory.global_context.items())[-5:]:
                context_parts.append(f"- {key}: {str(value)[:100]}...")
        
        return "\n".join(context_parts) if context_parts else "No previous context"

    def _extract_user_request(self, inputs: NodeInputs) -> str:
        """Extract user request from various input sources."""
        # Check user configuration for prompts
        user_config = inputs.user_configuration
        
        # Look for user prompts in various forms
        user_request_sources = [
            user_config.get('prompt', ''),
            user_config.get('user_prompt', ''),
            user_config.get('systemInstructions', ''),
            user_config.get('input_text', '')
        ]
        
        # Get from previous node data
        for prev_data in inputs.previous_node_data:
            if hasattr(prev_data, 'data') and isinstance(prev_data.data, str):
                user_request_sources.append(prev_data.data)
        
        # Return first non-empty request
        for request in user_request_sources:
            if request and request.strip():
                return request.strip()
        
        return "No specific user request found. Analyze available context and suggest appropriate actions."

    async def _execute_enhanced_reasoning(self, prompt: str, inputs: NodeInputs, streaming_callback: Optional[Callable[[str], None]] = None) -> str:
        """Execute enhanced reasoning with the LLM."""
        try:
            # Use enhanced system rules and execute with LLM
            result = await self._execute_llm_call(prompt, inputs.user_configuration)
            
            if streaming_callback:
                streaming_callback(result)
            
            return result
        except Exception as e:
            self.logger.error(f"Enhanced reasoning execution failed: {e}")
            # Return fallback response
            return json.dumps({
                "reasoning": f"Error in reasoning: {str(e)}",
                "selected_tools": [],
                "execution_plan": {},
                "dependencies": {},
                "expected_outcome": "Unable to complete reasoning due to error",
                "confidence": 0.1,
                "fallback_options": ["Manual intervention required"]
            })

    def _parse_enhanced_reasoning_result(self, result: str) -> Dict[str, Any]:
        """Parse the enhanced structured reasoning result."""
        try:
            # Try to parse as JSON first
            if result.strip().startswith('{'):
                return json.loads(result)
            
            # If not JSON, try to extract JSON from text
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # Fallback: create structure from text
            return {
                "reasoning": result,
                "selected_tools": [],
                "execution_plan": {},
                "dependencies": {},
                "expected_outcome": "Parsed from unstructured response",
                "confidence": 0.5,
                "fallback_options": []
            }
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse reasoning result as JSON: {e}")
            return {
                "reasoning": result,
                "selected_tools": [],
                "execution_plan": {},
                "dependencies": {},
                "expected_outcome": "Failed to parse structured response",
                "confidence": 0.3,
                "fallback_options": ["Retry with different approach"]
            }

    async def _execute_selected_tools(self, parsed_result: Dict[str, Any], workflow_memory: WorkflowMemory) -> List[ToolExecutionResult]:
        """Execute the selected tools using the ToolOrchestrator."""
        if not self.tool_orchestrator:
            return []
        
        selected_tools = parsed_result.get('selected_tools', [])
        execution_plan_data = parsed_result.get('execution_plan', {})
        
        if not selected_tools:
            return []
        
        try:
            # Create execution plan
            execution_plan = await self.tool_orchestrator.create_execution_plan(
                selected_tools=selected_tools,
                parameters=execution_plan_data,
                context={
                    'workflow_memory': workflow_memory.global_context,
                    'user_request': workflow_memory.global_context.get('user_request', ''),
                    'brain_reasoning': parsed_result.get('reasoning', '')
                }
            )
            
            # Execute the plan
            results = await self.tool_orchestrator.execute_tool_sequence(
                execution_plan=execution_plan,
                workflow_context=workflow_memory.global_context
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return []

    def _update_enhanced_context_memory(self, parsed_result: Dict[str, Any], inputs: NodeInputs, tool_results: List[ToolExecutionResult]):
        """Update context memory with enhanced information."""
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "reasoning": parsed_result.get("reasoning", ""),
            "selected_tools": parsed_result.get("selected_tools", []),
            "confidence": parsed_result.get("confidence", 0.0),
            "user_request": self._extract_user_request(inputs),
            "tool_results": len(tool_results),
            "successful_tools": len([r for r in tool_results if r.status.value == 'success'])
        }
        
        self.decision_history.append(decision_record)
        
        # Keep only last 10 decisions
        if len(self.decision_history) > 10:
            self.decision_history = self.decision_history[-10:]
        
        # Update tool performance cache
        for result in tool_results:
            if result.tool_name not in self.tool_performance_cache:
                self.tool_performance_cache[result.tool_name] = []
            
            self.tool_performance_cache[result.tool_name] = {
                "last_execution_time": result.execution_time,
                "last_status": result.status.value,
                "timestamp": result.timestamp
            }

    def _calculate_enhanced_confidence(self, parsed_result: Dict[str, Any], tool_results: List[ToolExecutionResult]) -> float:
        """Calculate confidence score based on reasoning quality and tool execution success."""
        base_confidence = parsed_result.get("confidence", 0.5)
        
        if tool_results:
            success_rate = len([r for r in tool_results if r.status.value == 'success']) / len(tool_results)
            # Adjust confidence based on tool execution success
            adjusted_confidence = (base_confidence + success_rate) / 2
        else:
            adjusted_confidence = base_confidence
        
        # Factor in reasoning quality
        reasoning_length = len(parsed_result.get("reasoning", ""))
        if reasoning_length > 100:  # Good detailed reasoning
            adjusted_confidence += 0.1
        elif reasoning_length < 50:  # Sparse reasoning
            adjusted_confidence -= 0.1
        
        return max(0.0, min(1.0, adjusted_confidence))

    def _assess_enhanced_reasoning_quality(self, parsed_result: Dict[str, Any]) -> str:
        """Assess the quality of enhanced reasoning."""
        reasoning = parsed_result.get("reasoning", "")
        selected_tools = parsed_result.get("selected_tools", [])
        confidence = parsed_result.get("confidence", 0.0)
        
        if len(reasoning) > 200 and len(selected_tools) > 0 and confidence > 0.7:
            return "excellent"
        elif len(reasoning) > 100 and confidence > 0.5:
            return "good"
        elif len(reasoning) > 50:
            return "fair"
        else:
            return "poor"

    def _extract_tool_calls_from_results(self, tool_results: List[ToolExecutionResult]) -> List[str]:
        """Extract tool calls from execution results."""
        return [f"{r.tool_name}:{r.status.value}" for r in tool_results]
        
    def _build_brain_prompt(self, inputs: NodeInputs) -> str:
        """
        Build a dynamic, contextually rich prompt specifically for the brain node's
        reasoning and coordination abilities.
        """
        # Extract connected node information for context
        connected_nodes_info = self._format_connected_nodes()
        workflow_state = self._analyze_workflow_state(inputs)
        decision_context = self._build_decision_context(inputs)
        
        # Format the workflow memory data for the prompt
        conversation_context = inputs.workflow_memory.get_relevant_context(max_history=10)
        global_context = json.dumps(inputs.workflow_memory.global_context, indent=2)
        execution_path = " -> ".join(inputs.workflow_memory.execution_path[-10:]) if inputs.workflow_memory.execution_path else "No previous execution"
        
        # Build the comprehensive prompt with sections
        prompt = f"""
        SYSTEM RULES (Brain Node Core Instructions):  
        {BRAIN_NODE_SYSTEM_RULES}
        
        WORKFLOW STATE ANALYSIS:
        {workflow_state}
        
        CONNECTED NODES & TOOLS:
        {connected_nodes_info}
        
        WORKFLOW CONTEXT & MEMORY:
        Workflow ID: {inputs.workflow_memory.workflow_id}
        Execution Path: {execution_path}
        
        Recent Conversation History:
        {conversation_context}
        
        Global Context: 
        {global_context}
        
        DECISION CONTEXT:
        {decision_context}
        
        USER CONFIGURATION:
        {self._format_user_configuration(inputs.user_configuration)}
        
        IMMEDIATE PREVIOUS NODE DATA:
        {self._format_previous_node_data(inputs.previous_node_data)}
        
        TASK:
        As the Brain Node, you must now:  
        1. Analyze the current workflow state and goals
        2. Consider available tools and their capabilities
        3. Reason about the best next action based on all context
        4. Determine which node(s) should be activated next and why
        5. Provide clear, structured reasoning about your decision
        
        FORMAT YOUR RESPONSE AS:
        REASONING: [Your step-by-step thought process analyzing the situation]
        
        DECISION: [Your specific decision about what should happen next]
        
        NEXT_NODE: [Name of the next node to activate, or 'COMPLETE' if workflow goal is achieved]
        
        PARAMETERS: [Any parameters to pass to the next node as JSON]
        """
        
        return prompt.strip()
        
    def _format_connected_nodes(self) -> str:
        """Format information about connected nodes for the prompt"""
        if not self.connected_nodes:
            return "No connected nodes available."
        
        node_descriptions = []
        for node in self.connected_nodes:
            capabilities = getattr(node, "capabilities", "No specific capabilities defined")
            properties = getattr(node, "properties", {})
            
            description = f"Node: {node.name} (Type: {type(node).__name__})\n"
            description += f"Capabilities: {capabilities}\n"
            
            if properties:
                description += "Properties:\n"
                for key, value in properties.items():
                    description += f"  - {key}: {value}\n"
                    
            node_descriptions.append(description)
            
        return "\n".join(node_descriptions)
        
    def _analyze_workflow_state(self, inputs: NodeInputs) -> str:
        """Analyze the current workflow state for contextual understanding"""
        # Count of previous interactions
        history_count = len(inputs.workflow_memory.conversation_history)
        
        # Get the node types that have been executed so far
        executed_nodes = []
        for history in inputs.workflow_memory.conversation_history:
            if 'node_type' in history:
                executed_nodes.append(history['node_type'])
        
        # Determine workflow progress (simple heuristic)
        if history_count == 0:
            progress = "Workflow just started. This is the first node execution."
        elif history_count < 3:
            progress = "Workflow is in its early stages."
        elif history_count < 10:
            progress = "Workflow is in progress."
        else:
            progress = "Workflow is in an advanced stage."
            
        analysis = f"""
        Workflow Progress: {progress}
        Interaction Count: {history_count}
        Executed Node Types: {', '.join(executed_nodes) if executed_nodes else 'None'}
        Context Memory Keys: {', '.join(self.context_memory.keys()) if self.context_memory else 'None'}
        Processing Strategy: {self.processing_strategy}
        """
        
        return analysis
        
    def _build_decision_context(self, inputs: NodeInputs) -> str:
        """Build context specifically for decision-making"""
        # Extract potential user intent from previous interactions
        user_intent = "Unknown"
        for history in inputs.workflow_memory.conversation_history:
            if 'input' in history and isinstance(history['input'], dict) and 'user_intent' in history['input']:
                user_intent = history['input']['user_intent']
                break
        
        # Extract goal-related information from user configuration
        goal = inputs.user_configuration.get('goal', 'No specific goal defined')
        priority = inputs.user_configuration.get('priority', 'standard')
        constraints = inputs.user_configuration.get('constraints', [])
        
        context = f"""
        User Intent: {user_intent}
        Goal: {goal}
        Priority: {priority}
        Constraints: {', '.join(constraints) if constraints else 'None specified'}
        """
        
        return context
        
    async def _execute_reasoning(self, prompt: str, inputs: NodeInputs) -> str:
        """Execute the brain's reasoning process using the LLM with streaming"""
        retry_count = 0
        max_retries = 3
        backoff_seconds = 1
        
        while retry_count <= max_retries:
            try:
                # Configure LLM parameters based on execution mode but with more focus on reasoning quality
                model_params = self.model_config.copy()
                
                # For brain node reasoning, we want more deterministic, logical outputs
                if self.execution_mode == NodeExecutionMode.PRODUCTION:
                    model_params["temperature"] = 0.4  # Lower temperature for more logical reasoning
                    model_params["top_p"] = 0.85
                
                # Check if streaming callback is provided
                streaming_callback = inputs.streaming_callback
                
                # Use streaming by default for better UX
                return await self._stream_reasoning_response(
                    prompt=prompt,
                    model_params=model_params,
                    streaming_callback=streaming_callback
                )
                
            except Exception as e:
                retry_count += 1
                error_type = type(e).__name__
                self.logger.error(f"Error in brain reasoning (attempt {retry_count}/{max_retries}): {error_type}: {str(e)}")
                
                # Check if we should retry based on error type
                if any(error_name in error_type.lower() for error_name in ['timeout', 'rate', 'connection', 'network', 'temporary']):
                    # These error types can be retried
                    if retry_count <= max_retries:
                        wait_time = backoff_seconds * (2 ** (retry_count - 1))  # Exponential backoff
                        self.logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                # If we've exhausted retries or it's a non-retryable error
                if retry_count > max_retries:
                    self.logger.error(f"Maximum retries reached. Brain reasoning failed: {str(e)}")
                else:
                    self.logger.error(f"Non-retryable error in brain reasoning: {str(e)}")
                    
                # Return a fallback response that maintains the expected format
                return self._generate_error_reasoning(str(e))
        
        # This should not be reached due to the return in the exception handler
        return self._generate_error_reasoning("Unknown error in reasoning process")
    
    async def _stream_reasoning_response(
        self, 
        prompt: str, 
        model_params: Dict[str, Any],
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Stream the LLM response with proper handling of partial outputs"""
        try:
            system_message = "You are the Brain Node responsible for reasoning and decision-making in an AI workflow system. Provide clear, logical reasoning and decisions."
            
            # Prefer centralized LLMManager if available
            llm_manager = getattr(self, "llm_manager", None)
            db_session = getattr(self, "db_session", None)
            if llm_manager and db_session:
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ]
                exec_id = getattr(self, "execution_id", None)
                user_id = getattr(self, "user_id", None)
                try:
                    if isinstance(exec_id, str):
                        exec_id = uuid.UUID(exec_id)
                except Exception:
                    exec_id = None
                try:
                    if isinstance(user_id, str):
                        user_id = uuid.UUID(user_id)
                except Exception:
                    user_id = None

                result = await llm_manager.generate(
                    db_session,
                    user_id=user_id,
                    model=model_params['model'],
                    messages=messages,
                    stream=True,
                    temperature=model_params.get('temperature', 0.4),
                    max_tokens=model_params.get('max_tokens', 4096),
                    extra={},
                    execution_id=exec_id,
                )

                content = (getattr(result, 'content', None) or "")
                if not content:
                    return ""

                full_response = ""
                reasoning_buffer = ""
                decision_buffer = ""
                next_node_buffer = ""
                parameters_buffer = ""
                current_section = None
                streaming_enabled = streaming_callback is not None

                chunk_count = 0
                section_transitions = 0
                start_time = datetime.now()

                chunk_size = 200
                for i in range(0, len(content), chunk_size):
                    delta_content = content[i:i+chunk_size]
                    try:
                        if delta_content:
                            chunk_count += 1
                            full_response += delta_content
                            if "REASONING:" in delta_content and current_section is None:
                                current_section = "reasoning"
                                section_transitions += 1
                            elif "DECISION:" in delta_content and (current_section == "reasoning" or current_section is None):
                                current_section = "decision"
                                section_transitions += 1
                            elif "NEXT_NODE:" in delta_content and (current_section == "decision" or current_section is None):
                                current_section = "next_node"
                                section_transitions += 1
                            elif "PARAMETERS:" in delta_content and (current_section == "next_node" or current_section is None):
                                current_section = "parameters"
                                section_transitions += 1

                            if current_section == "reasoning":
                                reasoning_buffer += delta_content
                            elif current_section == "decision":
                                decision_buffer += delta_content
                            elif current_section == "next_node":
                                next_node_buffer += delta_content
                            elif current_section == "parameters":
                                parameters_buffer += delta_content

                            if streaming_enabled:
                                try:
                                    streaming_callback(delta_content)
                                except Exception as callback_error:
                                    self.logger.warning(f"Streaming callback error: {str(callback_error)}")
                            else:
                                if self.execution_mode == NodeExecutionMode.DEBUG:
                                    print(delta_content, end='', flush=True)

                            if chunk_count % 50 == 0 and self.execution_mode == NodeExecutionMode.DEBUG:
                                self.logger.debug(f"Streamed {chunk_count} chunks, current section: {current_section}")
                    except Exception as chunk_error:
                        self.logger.warning(f"Error processing chunk: {str(chunk_error)}")
                        continue

                duration = (datetime.now() - start_time).total_seconds()
                self.logger.info(
                    f"Brain reasoning streaming complete: {len(full_response)} chars, "
                    f"{chunk_count} chunks, {section_transitions} sections in {duration:.2f}s"
                )

                if not full_response or "REASONING:" not in full_response:
                    self.logger.warning("Stream response may be incomplete or malformed")
                    if len(full_response) < 50:
                        return await self._fallback_non_streaming_reasoning(prompt, model_params)

                return full_response

            # Fallback: use local NVIDIA client if available
            if self.brain_llm:
                completion = self.brain_llm.chat.completions.create(
                    model=model_params['model'],
                    messages=[{"role": "system", "content": system_message}, 
                            {"role": "user", "content": prompt}],
                    temperature=model_params.get('temperature', 0.4),
                    top_p=model_params.get('top_p', 0.85),
                    max_tokens=model_params.get('max_tokens', 4096),
                    stream=True
                )

                full_response = ""
                reasoning_buffer = ""
                decision_buffer = ""
                next_node_buffer = ""
                parameters_buffer = ""
                current_section = None
                streaming_enabled = streaming_callback is not None

                chunk_count = 0
                section_transitions = 0
                start_time = datetime.now()

                for chunk in completion:
                    try:
                        delta_content = chunk.choices[0].delta.content
                        if delta_content:
                            chunk_count += 1
                            full_response += delta_content
                            if "REASONING:" in delta_content and current_section is None:
                                current_section = "reasoning"
                                section_transitions += 1
                            elif "DECISION:" in delta_content and (current_section == "reasoning" or current_section is None):
                                current_section = "decision"
                                section_transitions += 1
                            elif "NEXT_NODE:" in delta_content and (current_section == "decision" or current_section is None):
                                current_section = "next_node"
                                section_transitions += 1
                            elif "PARAMETERS:" in delta_content and (current_section == "next_node" or current_section is None):
                                current_section = "parameters"
                                section_transitions += 1

                            if current_section == "reasoning":
                                reasoning_buffer += delta_content
                            elif current_section == "decision":
                                decision_buffer += delta_content
                            elif current_section == "next_node":
                                next_node_buffer += delta_content
                            elif current_section == "parameters":
                                parameters_buffer += delta_content

                            if streaming_enabled:
                                try:
                                    streaming_callback(delta_content)
                                except Exception as callback_error:
                                    self.logger.warning(f"Streaming callback error: {str(callback_error)}")
                            else:
                                if self.execution_mode == NodeExecutionMode.DEBUG:
                                    print(delta_content, end='', flush=True)

                            if chunk_count % 50 == 0 and self.execution_mode == NodeExecutionMode.DEBUG:
                                self.logger.debug(f"Streamed {chunk_count} chunks, current section: {current_section}")
                    except Exception as chunk_error:
                        self.logger.warning(f"Error processing chunk: {str(chunk_error)}")
                        continue

                duration = (datetime.now() - start_time).total_seconds()
                self.logger.info(
                    f"Brain reasoning streaming complete: {len(full_response)} chars, "
                    f"{chunk_count} chunks, {section_transitions} sections in {duration:.2f}s"
                )

                if not full_response or "REASONING:" not in full_response:
                    self.logger.warning("Stream response may be incomplete or malformed")
                    if len(full_response) < 50:
                        return await self._fallback_non_streaming_reasoning(prompt, model_params)

                return full_response

            # If neither LLMManager nor local client is available
            return await self._fallback_non_streaming_reasoning(prompt, model_params)
        
        except Exception as e:
            self.logger.error(f"Error in streaming response: {str(e)}")
            # Fall back to non-streaming if there's an error
            return await self._fallback_non_streaming_reasoning(prompt, model_params)
    
    async def _fallback_non_streaming_reasoning(self, prompt: str, model_params: Dict[str, Any]) -> str:
        """Fallback to non-streaming mode if streaming fails"""
        self.logger.warning("Falling back to non-streaming LLM request due to streaming error")
        try:
            system_message = "You are the Brain Node responsible for reasoning and decision-making in an AI workflow system. Provide clear, logical reasoning and decisions."
            
            # Simplify the prompt for fallback to increase chances of success
            simplified_prompt = self._simplify_prompt_for_fallback(prompt)
            
            # Use a slightly higher temperature for more reliable generation in fallback mode
            model_params = model_params.copy()
            model_params["temperature"] = max(0.5, model_params.get("temperature", 0.4) + 0.1)
            
            # Prefer centralized LLMManager if available
            llm_manager = getattr(self, "llm_manager", None)
            db_session = getattr(self, "db_session", None)
            if llm_manager and db_session:
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": simplified_prompt},
                ]
                exec_id = getattr(self, "execution_id", None)
                user_id = getattr(self, "user_id", None)
                try:
                    if isinstance(exec_id, str):
                        exec_id = uuid.UUID(exec_id)
                except Exception:
                    exec_id = None
                try:
                    if isinstance(user_id, str):
                        user_id = uuid.UUID(user_id)
                except Exception:
                    user_id = None

                result = await llm_manager.generate(
                    db_session,
                    user_id=user_id,
                    model=model_params['model'],
                    messages=messages,
                    stream=False,
                    temperature=model_params.get('temperature', 0.5),
                    max_tokens=model_params.get('max_tokens', 4096),
                    extra={},
                    execution_id=exec_id,
                )
                text = getattr(result, 'content', None) or ""
                self.logger.info(f"Fallback non-streaming complete: {len(text)} chars (via LLMManager)")
                return text

            # Use the BrainNode-specific client without streaming if available
            if self.brain_llm:
                completion = self.brain_llm.chat.completions.create(
                    model=model_params['model'],
                    messages=[{"role": "system", "content": system_message}, 
                            {"role": "user", "content": simplified_prompt}],
                    temperature=model_params.get('temperature', 0.5),
                    top_p=model_params.get('top_p', 0.9),
                    max_tokens=model_params.get('max_tokens', 4096),
                    stream=False
                )
                result = completion.choices[0].message.content
                self.logger.info(f"Fallback non-streaming complete: {len(result)} chars (via local client)")
                return result

            # If no provider available at all
            self.logger.error("No LLM provider available for BrainNode fallback reasoning")
            return self._generate_error_reasoning("No LLM provider available (LLMManager or local provider)")
            
        except Exception as e:
            self.logger.error(f"Critical error in fallback reasoning: {str(e)}")
            return self._generate_error_reasoning(str(e))
    
    def _generate_error_reasoning(self, error_message: str) -> str:
        """Generate a properly formatted reasoning response for error cases"""
        return f"""REASONING: 
I encountered an error while trying to process this workflow step: {error_message}.

DECISION: 
Due to the error, I recommend pausing the workflow and checking the system configuration or input data for any issues.

NEXT_NODE: 
ErrorHandlingNode

PARAMETERS: 
{{
  "error": "{error_message}",
  "recommended_action": "debug",
  "severity": "high"
}}
"""
    
    def _simplify_prompt_for_fallback(self, prompt: str) -> str:
        """Simplify the prompt for fallback mode to increase chances of success"""
        # If prompt is already short, return it as is
        if len(prompt) < 1000:
            return prompt
            
        # Extract key sections to preserve
        sections = [
            "SYSTEM RULES", 
            "WORKFLOW STATE ANALYSIS",
            "CONNECTED NODES & TOOLS",
            "USER CONFIGURATION",
            "IMMEDIATE PREVIOUS NODE DATA",
            "TASK"
        ]
        
        simplified_parts = []
        for section in sections:
            if section in prompt:
                # Find the section and the content until the next section or end
                section_start = prompt.find(section)
                section_text = ""
                
                # Find where the next section starts, if any
                next_section_start = float('inf')
                for s in sections:
                    if s != section:
                        pos = prompt.find(s, section_start + len(section))
                        if pos > section_start and pos < next_section_start:
                            next_section_start = pos
                
                # Extract the section content with some truncation for long sections
                if next_section_start < float('inf'):
                    section_text = prompt[section_start:next_section_start]
                else:
                    section_text = prompt[section_start:]
                    
                # Truncate overly long sections
                if len(section_text) > 500 and section != "SYSTEM RULES" and section != "TASK":
                    section_text = section_text[:500] + "... [truncated for brevity]"
                    
                simplified_parts.append(section_text)
        
        # Add a note that this is a simplified prompt for fallback
        simplified_prompt = "\n\n".join(simplified_parts)
        simplified_prompt += "\n\nNOTE: This is a simplified prompt due to a previous error. Please provide the most reliable reasoning and decision possible with the information available."
        
        return simplified_prompt
    
    def _parse_reasoning_result(self, result: str) -> Dict[str, Any]:
        """Parse the LLM output into structured reasoning components"""
        parsed = {
            "reasoning": "",
            "decision": "",
            "next_node": "",
            "parameters": {}
        }
        
        # Extract the reasoning section
        if "REASONING:" in result:
            parts = result.split("DECISION:", 1)
            if len(parts) > 0:
                reasoning = parts[0].replace("REASONING:", "").strip()
                parsed["reasoning"] = reasoning
        
        # Extract the decision section
        if "DECISION:" in result:
            parts = result.split("DECISION:", 1)[1].split("NEXT_NODE:", 1)
            if len(parts) > 0:
                decision = parts[0].strip()
                parsed["decision"] = decision
                
        # Extract the next node section
        if "NEXT_NODE:" in result:
            parts = result.split("NEXT_NODE:", 1)[1].split("PARAMETERS:", 1)
            if len(parts) > 0:
                next_node = parts[0].strip()
                parsed["next_node"] = next_node
        
        # Extract parameters if present
        if "PARAMETERS:" in result:
            params_text = result.split("PARAMETERS:", 1)[1].strip()
            try:
                # Try to parse as JSON
                if params_text:
                    # Check if it's wrapped in code blocks and remove them
                    if params_text.startswith('```') and params_text.endswith('```'):
                        params_text = '\n'.join(params_text.split('\n')[1:-1])
                        
                    parsed["parameters"] = json.loads(params_text)
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse parameters as JSON: {params_text}")
                parsed["parameters"] = {"raw": params_text}
        
        return parsed
    
    def _update_context_memory(self, parsed_result: Dict[str, Any], inputs: NodeInputs) -> None:
        """Update the context memory with key information from reasoning"""
        # Store the last decision for context continuity
        self.context_memory["last_decision"] = parsed_result.get("decision", "")
        self.context_memory["last_next_node"] = parsed_result.get("next_node", "")
        
        # Track reasoning history (keep limited size)
        if "reasoning_history" not in self.context_memory:
            self.context_memory["reasoning_history"] = []
            
        history = self.context_memory["reasoning_history"]
        history.append({
            "timestamp": datetime.now().isoformat(),
            "reasoning": parsed_result.get("reasoning", "")[:100] + "..."  # Store a summary
        })
        
        # Keep only recent history (last 5 entries)
        if len(history) > 5:
            self.context_memory["reasoning_history"] = history[-5:]
    
    def _calculate_decision_confidence(self, parsed_result: Dict[str, Any]) -> float:
        """Calculate confidence score for the reasoning and decision"""
        base_confidence = 0.5  # Start with neutral confidence
        
        # More detailed reasoning increases confidence
        reasoning_length = len(parsed_result.get("reasoning", ""))
        if reasoning_length > 500:
            base_confidence += 0.2
        elif reasoning_length > 200:
            base_confidence += 0.1
            
        # Having a clear next node increases confidence
        if parsed_result.get("next_node", "") != "":
            base_confidence += 0.1
            
        # Having structured parameters increases confidence
        if isinstance(parsed_result.get("parameters", None), dict) and parsed_result["parameters"]:
            base_confidence += 0.1
            
        # Decision quality heuristics
        decision = parsed_result.get("decision", "")
        if len(decision) > 100 and not any(word in decision.lower() for word in ["uncertain", "unclear", "cannot determine"]):
            base_confidence += 0.1
        
        return min(1.0, max(0.0, base_confidence))
        
    def _extract_next_node_suggestions(self, parsed_result: Dict[str, Any]) -> List[str]:
        """Extract next node suggestions from the reasoning result"""
        next_node = parsed_result.get("next_node", "")
        suggestions = []
        
        # Add the primary next node if specified
        if next_node and next_node != "COMPLETE":
            suggestions.append(next_node)
        
        # Look for alternative suggestions in the reasoning
        reasoning = parsed_result.get("reasoning", "")
        
        # Extract node names from connected nodes
        connected_node_names = [node.name for node in self.connected_nodes]
        
        # Check for mentions of other connected nodes in reasoning
        for node_name in connected_node_names:
            if node_name in reasoning and node_name != next_node and node_name not in suggestions:
                suggestions.append(node_name)
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _extract_tool_calls(self, parsed_result: Dict[str, Any]) -> List[str]:
        """Extract tool call suggestions from the reasoning"""
        tool_calls = []
        reasoning = parsed_result.get("reasoning", "")
        
        # Look for explicit tool mentions in reasoning
        common_tools = ["search", "api_call", "database_query", "calculate", "transform_data"]
        for tool in common_tools:
            if f"use {tool}" in reasoning.lower() or f"call {tool}" in reasoning.lower():
                tool_calls.append(tool)
        
        # Check parameters for tool indications
        params = parsed_result.get("parameters", {})
        if isinstance(params, dict):
            for key in params.keys():
                if "tool" in key or "action" in key:
                    tool_value = params[key]
                    if isinstance(tool_value, str) and tool_value not in tool_calls:
                        tool_calls.append(tool_value)
        
        return tool_calls
    
    def _assess_reasoning_quality(self, parsed_result: Dict[str, Any]) -> str:
        """Assess the quality of the reasoning (for metrics/debugging)"""
        reasoning = parsed_result.get("reasoning", "")
        
        if not reasoning:
            return "missing"
            
        # Simple heuristics for quality assessment
        if len(reasoning) < 100:
            return "minimal"
        elif len(reasoning) > 500 and len(parsed_result.get("decision", "")) > 100:
            return "thorough"
        else:
            return "adequate"
    
    def _determine_workflow_stage(self, inputs: NodeInputs) -> str:
        """Determine the current stage of the workflow for context"""
        history_len = len(inputs.workflow_memory.conversation_history)
        
        if history_len == 0:
            return "initialization"
        elif history_len < 3:
            return "early"
        elif history_len < 8:
            return "mid"
        else:
            return "advanced"
