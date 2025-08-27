"""
Brain Node Module

Central reasoning node that coordinates other nodes and decides workflow actions.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from datetime import datetime
from openai import OpenAI
import asyncio

from GeneralNodeLogic import (
    GeneralNodeLogic, 
    NodeInputs, 
    NodeOutput, 
    PreviousNodeOutput, 
    WorkflowMemory,
    NodeExecutionMode
)

# Expanded system rules
BRAIN_NODE_SYSTEM_RULES = """
You are a Brain Node in an AI agent workflow system.
Your responsibilities:
- Reason intelligently about the workflow and user goals.
- Consider all available connected tools and their capabilities.
- Use previous node outputs and memory context to guide decisions.
- Always align actions with the user's configuration preferences.
- Choose the best next step: which node/tool to invoke, in what order.
- If multiple paths are possible, explain your reasoning.
- Output in a structured, traceable format for testing/debugging.
"""

class BrainNode(GeneralNodeLogic):
    """
    Brain Node - Central coordinator for the node system.
    Enhanced with NVIDIA API integration, dynamic prompt construction,
    reasoning capabilities, and tool suggestion.
    """
    def __init__(self, node_id: str, name: str, execution_mode: NodeExecutionMode = NodeExecutionMode.PRODUCTION):
        super().__init__(execution_mode)
        self.node_id = node_id
        self.name = name
        self.connected_nodes: List[Any] = []
        self.processing_strategy: str = "sequential"
        self.context_memory: Dict[str, Any] = {}  # persists context across runs
        
        # Set up specific NVIDIA API client for BrainNode
        try:
            api_key = os.environ.get('NVIDIA_API_KEY')
            if not api_key:
                raise ValueError("NVIDIA_API_KEY environment variable not set")
                
            self.brain_llm = OpenAI(
                api_key=api_key,
                base_url='https://integrate.api.nvidia.com/v1',
            )
            self.logger.info("BrainNode NVIDIA API client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize BrainNode NVIDIA API client: {str(e)}")
            raise
    
    async def execute(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> NodeOutput:
        """
        Execute the Brain Node using GeneralNodeLogic with specific system rules.
        Includes reasoning about connected nodes and persistence of context.
        """
        try:
            # Start timing execution
            start_time = datetime.now()
            self.logger.info(f"BrainNode execution started: {self.node_id}")
            
            # Create NodeInputs with BrainNode-specific system rules
            inputs = NodeInputs(
                system_rules=BRAIN_NODE_SYSTEM_RULES,
                user_configuration=user_configuration,
                previous_node_data=previous_node_data,
                workflow_memory=workflow_memory,
                execution_context={
                    "connected_nodes": [n.name for n in self.connected_nodes],
                    "processing_strategy": self.processing_strategy,
                    "context_memory": self.context_memory
                }
            )
            
            # Build dynamic prompt with enhanced brain-specific context
            prompt = self._build_brain_prompt(inputs)
            
            # Execute brain reasoning with LLM
            result = await self._execute_reasoning(prompt, inputs)
            
            # Parse the result to extract structured reasoning and decision
            parsed_result = self._parse_reasoning_result(result)
            
            # Store important context for future executions
            self._update_context_memory(parsed_result, inputs)
            
            # Calculate confidence based on reasoning quality
            confidence = self._calculate_decision_confidence(parsed_result)
            
            # Determine next node suggestions based on reasoning
            next_nodes = self._extract_next_node_suggestions(parsed_result)
            
            # Record any tool calls that were made or suggested
            tool_calls = self._extract_tool_calls(parsed_result)
            
            # Update workflow memory with brain node's reasoning and decision
            workflow_memory.global_context.update({
                "last_brain_reasoning": parsed_result.get("reasoning", ""),
                "last_brain_decision": parsed_result.get("decision", ""),
                "last_next_node": parsed_result.get("next_node", "")
            })
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return NodeOutput(
                node_id=self.node_id,
                node_type="BrainNode",
                data=parsed_result,  # Return the structured reasoning output
                timestamp=datetime.now().timestamp(),
                metadata={
                    "status": "success",
                    "execution_time_ms": execution_time,
                    "model_used": self.model_config['model'],
                    "reasoning_quality": self._assess_reasoning_quality(parsed_result),
                    "workflow_stage": self._determine_workflow_stage(inputs)
                },
                success=True,
                next_suggested_nodes=next_nodes,
                confidence_score=confidence,
                tool_calls_made=tool_calls,
                memory_updates={
                    "brain_reasoning": parsed_result.get("reasoning", ""),
                    "decision_path": parsed_result.get("next_node", "")
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
            
            # Use the BrainNode-specific client with streaming
            completion = self.brain_llm.chat.completions.create(
                model=model_params['model'],
                messages=[{"role": "system", "content": system_message}, 
                        {"role": "user", "content": prompt}],
                temperature=model_params.get('temperature', 0.4),
                top_p=model_params.get('top_p', 0.85),
                max_tokens=model_params.get('max_tokens', 4096),
                stream=True  # Enable streaming
            )
            
            full_response = ""
            reasoning_buffer = ""
            decision_buffer = ""
            next_node_buffer = ""
            parameters_buffer = ""
            current_section = None
            streaming_enabled = streaming_callback is not None
            
            # Track streaming metrics
            chunk_count = 0
            section_transitions = 0
            start_time = datetime.now()
            
            # Process streaming chunks with error handling
            for chunk in completion:
                try:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        chunk_count += 1
                        full_response += delta_content
                        
                        # Detect section transitions for structured output
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
                        
                        # Buffer content by section for partial processing
                        if current_section == "reasoning":
                            reasoning_buffer += delta_content
                        elif current_section == "decision":
                            decision_buffer += delta_content
                        elif current_section == "next_node":
                            next_node_buffer += delta_content
                        elif current_section == "parameters":
                            parameters_buffer += delta_content
                        
                        # Stream the content to the client if a callback is provided
                        if streaming_enabled:
                            try:
                                streaming_callback(delta_content)
                            except Exception as callback_error:
                                self.logger.warning(f"Streaming callback error: {str(callback_error)}")
                                # Continue processing even if the callback fails
                        else:
                            # If no callback but in debug mode, print to console
                            if self.execution_mode == NodeExecutionMode.DEBUG:
                                print(delta_content, end='', flush=True)
                                
                        # Log progress in debug mode
                        if chunk_count % 50 == 0 and self.execution_mode == NodeExecutionMode.DEBUG:
                            self.logger.debug(f"Streamed {chunk_count} chunks, current section: {current_section}")
                except Exception as chunk_error:
                    self.logger.warning(f"Error processing chunk: {str(chunk_error)}")
                    # Continue to the next chunk instead of failing the whole stream
                    continue
            
            # Streaming complete - log metrics
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Brain reasoning streaming complete: {len(full_response)} chars, "
                f"{chunk_count} chunks, {section_transitions} sections in {duration:.2f}s"
            )
            
            # Validate the response has the expected structure
            if not full_response or "REASONING:" not in full_response:
                self.logger.warning("Stream response may be incomplete or malformed")
                if len(full_response) < 50:
                    # If response is very short, likely an error occurred
                    return await self._fallback_non_streaming_reasoning(prompt, model_params)
            
            return full_response
        
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
            
            # Use the BrainNode-specific client without streaming
            completion = self.brain_llm.chat.completions.create(
                model=model_params['model'],
                messages=[{"role": "system", "content": system_message}, 
                        {"role": "user", "content": simplified_prompt}],
                temperature=model_params.get('temperature', 0.5),
                top_p=model_params.get('top_p', 0.9),  # Slightly higher top_p for more reliable generation
                max_tokens=model_params.get('max_tokens', 4096),
                stream=False  # Disable streaming for fallback
            )
            
            result = completion.choices[0].message.content
            self.logger.info(f"Fallback non-streaming complete: {len(result)} chars")
            return result
            
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
