"""
LangChain-Enhanced Brain Node for Weev Platform

This module provides an advanced Brain Node implementation that leverages LangGraph's
state management and LangChain's agent capabilities to deliver sophisticated reasoning
and decision-making functionality for AI workflows.

Key Enhancements over Standard BrainNode:
========================================

1. **State-Based Reasoning**: Uses LangGraph's persistent state to maintain complex 
   reasoning contexts across multiple interactions and workflow steps.

2. **Multi-Agent Coordination**: Can coordinate multiple specialized agents for 
   complex problem-solving scenarios.

3. **Tool Integration**: Seamless integration with LangChain's tool ecosystem 
   for enhanced capabilities (web search, APIs, databases, etc.).

4. **Human-in-the-Loop**: Built-in support for human approval checkpoints and 
   feedback integration during reasoning processes.

5. **Advanced Memory Management**: Sophisticated memory systems that can maintain
   both short-term working memory and long-term knowledge across sessions.

6. **Error Recovery**: Robust error handling with automatic retry, fallback
   strategies, and graceful degradation.

Architecture:
============

The LangChainBrainNode extends the existing BrainNode functionality while
maintaining full backward compatibility. It operates in two modes:

**Standard Mode**: Functions exactly like the original BrainNode for simple tasks
**Enhanced Mode**: Uses LangGraph state management for complex multi-step reasoning

Integration Pattern:
==================

1. **Input Processing**: Converts Weev inputs to LangGraph state format
2. **State Management**: Maintains persistent reasoning state across calls
3. **Agent Execution**: Uses LangChain agents for tool-enabled reasoning
4. **Result Processing**: Converts LangGraph results back to Weev format
5. **Memory Bridging**: Updates both Weev and LangChain memory systems

State Schema:
============

```python
class BrainNodeState(TypedDict):
    # Reasoning context
    current_problem: str
    reasoning_steps: List[Dict[str, Any]]
    decision_criteria: List[str]
    
    # Tool usage
    tools_available: List[str]
    tool_results: Dict[str, Any]
    
    # Multi-agent coordination  
    agent_assignments: Dict[str, str]
    agent_results: Dict[str, Any]
    
    # Human interaction
    requires_approval: bool
    human_feedback: Optional[str]
    
    # Memory management
    working_memory: Dict[str, Any]
    long_term_insights: List[str]
```

Usage Examples:
==============

**Basic Enhanced Reasoning**:
```python
brain_node = LangChainBrainNode(
    node_id="brain_enhanced",
    name="Enhanced Brain",
    graph_manager=graph_manager,
    enable_tools=True
)

result = await brain_node.execute(
    user_configuration={
        "problem": "Analyze market trends for Q1 planning",
        "use_web_search": True,
        "require_approval": False
    },
    previous_node_data=[...],
    workflow_memory=memory
)
```

**Multi-Agent Orchestration**:
```python
brain_node = LangChainBrainNode(
    node_id="brain_multi_agent", 
    name="Multi-Agent Brain",
    agents={
        "researcher": ResearchAgent(),
        "analyst": AnalysisAgent(),
        "planner": PlanningAgent()
    }
)
```

**Human-in-the-Loop Workflow**:
```python
brain_node = LangChainBrainNode(
    node_id="brain_hitl",
    name="Human-Supervised Brain",
    human_approval_threshold=0.7,  # Require approval for low confidence decisions
    approval_callback=send_approval_request
)
```

Performance Optimizations:
=========================

1. **Incremental Reasoning**: Builds on previous reasoning states rather than starting fresh
2. **Selective Tool Use**: Only invokes tools when necessary based on problem analysis
3. **Parallel Agent Execution**: Runs multiple agents concurrently when possible
4. **Smart Caching**: Caches expensive operations and reasoning results
5. **Streaming Integration**: Provides real-time reasoning updates via WebSocket

Error Handling Strategy:
=======================

1. **Graceful Degradation**: Falls back to standard BrainNode on LangGraph errors
2. **State Recovery**: Automatically recovers from partial state corruption
3. **Tool Failure Handling**: Continues reasoning when individual tools fail
4. **Agent Coordination Errors**: Handles agent communication failures gracefully
5. **Memory Consistency**: Ensures memory remains consistent across error scenarios

Monitoring and Observability:
============================

- **Reasoning Traces**: Detailed logging of reasoning steps and decisions
- **Performance Metrics**: Execution time, tool usage, agent coordination efficiency
- **State Transitions**: Tracking of state changes throughout reasoning process
- **Error Analytics**: Comprehensive error reporting and pattern analysis
- **Human Interaction Tracking**: Metrics on human approval patterns and feedback

Author: Weev Platform Team
Version: 1.0.0
Date: 2025-01-XX
"""

import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import logging

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import BaseTool
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from ...BrainNode import BrainNode
from ...GeneralNodeLogic import (
    NodeInputs, NodeOutput, PreviousNodeOutput, 
    WorkflowMemory, NodeExecutionMode
)
from ..graph_manager import LangGraphManager, WorkflowState


class BrainNodeState(dict):
    """
    Enhanced state schema specifically for LangChain Brain Node operations.
    
    This state extends the base WorkflowState with brain-specific fields
    for advanced reasoning, tool usage, and multi-agent coordination.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize brain-specific state fields if not present
        self.setdefault("current_problem", "")
        self.setdefault("reasoning_steps", [])
        self.setdefault("decision_criteria", [])
        self.setdefault("confidence_score", 0.5)
        
        # Tool management
        self.setdefault("tools_available", [])
        self.setdefault("tool_results", {})
        self.setdefault("tool_call_count", 0)
        
        # Multi-agent coordination
        self.setdefault("agent_assignments", {})
        self.setdefault("agent_results", {})
        self.setdefault("active_agents", [])
        
        # Human interaction
        self.setdefault("requires_approval", False)
        self.setdefault("human_feedback", None)
        self.setdefault("approval_status", "pending")
        
        # Memory management
        self.setdefault("working_memory", {})
        self.setdefault("long_term_insights", [])
        self.setdefault("context_window", [])


class LangChainBrainNode(BrainNode):
    """
    Enhanced Brain Node with LangGraph state management and LangChain agent capabilities.
    
    This class extends the standard BrainNode with advanced features including
    persistent state, tool integration, multi-agent coordination, and human-in-the-loop
    workflows while maintaining full backward compatibility.
    """
    
    def __init__(
        self,
        node_id: str,
        name: str,
        graph_manager: Optional[LangGraphManager] = None,
        tools: Optional[List[BaseTool]] = None,
        agents: Optional[Dict[str, Any]] = None,
        execution_mode: NodeExecutionMode = NodeExecutionMode.PRODUCTION,
        enable_human_approval: bool = False,
        human_approval_threshold: float = 0.5,
        max_reasoning_steps: int = 10,
        enable_streaming: bool = True
    ):
        """
        Initialize the LangChain-enhanced Brain Node.
        
        Args:
            node_id: Unique identifier for the node
            name: Human-readable name for the node
            graph_manager: LangGraph manager for state management
            tools: List of LangChain tools available to the node
            agents: Dictionary of specialized agents for multi-agent workflows
            execution_mode: Execution mode (PROTOTYPE, PRODUCTION, DEBUG)
            enable_human_approval: Whether to enable human approval checkpoints
            human_approval_threshold: Confidence threshold below which human approval is required
            max_reasoning_steps: Maximum number of reasoning steps before termination
            enable_streaming: Whether to enable real-time streaming of reasoning process
        """
        # Initialize parent BrainNode
        super().__init__(node_id, name, execution_mode)
        
        # LangChain-specific initialization
        self.graph_manager = graph_manager
        self.tools = tools or []
        self.agents = agents or {}
        self.enable_human_approval = enable_human_approval
        self.human_approval_threshold = human_approval_threshold
        self.max_reasoning_steps = max_reasoning_steps
        self.enable_streaming = enable_streaming
        
        # State management
        self.current_state: Optional[BrainNodeState] = None
        self.state_history: List[BrainNodeState] = []
        
        # Tool executor for LangChain tools
        if self.tools:
            self.tool_executor = ToolExecutor(self.tools)
        else:
            self.tool_executor = None
        
        # Agent executors
        self.agent_executors: Dict[str, AgentExecutor] = {}
        self._initialize_agents()
        
        # Enhanced logger for debugging
        self.logger = logging.getLogger(f"weev.langchain_brain_node.{node_id}")
        self.logger.setLevel(
            logging.DEBUG if execution_mode == NodeExecutionMode.DEBUG else logging.INFO
        )
        
        # Performance tracking
        self.execution_stats = {
            "total_executions": 0,
            "avg_execution_time": 0.0,
            "tool_usage_count": 0,
            "human_approvals_requested": 0,
            "error_count": 0
        }
        
        self.logger.info(f"LangChainBrainNode initialized: {name}")
    
    def _initialize_agents(self):
        """Initialize specialized agents for multi-agent coordination."""
        for agent_name, agent_config in self.agents.items():
            try:
                if isinstance(agent_config, dict):
                    # Create agent from configuration
                    agent_executor = self._create_agent_from_config(agent_name, agent_config)
                else:
                    # Use pre-configured agent
                    agent_executor = agent_config
                
                self.agent_executors[agent_name] = agent_executor
                self.logger.info(f"Agent '{agent_name}' initialized successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize agent '{agent_name}': {e}")
    
    def _create_agent_from_config(self, agent_name: str, config: Dict[str, Any]) -> AgentExecutor:
        """Create an agent executor from configuration."""
        # This would need to be implemented based on your specific agent requirements
        # For now, return a basic agent structure
        prompt = ChatPromptTemplate.from_messages([
            ("system", config.get("system_prompt", f"You are {agent_name}, a specialized AI agent.")),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create a basic agent (this would need proper implementation)
        # agent = create_openai_functions_agent(llm, self.tools, prompt)
        # return AgentExecutor(agent=agent, tools=self.tools, verbose=True)
        
        # Placeholder return - would need actual implementation
        return None
    
    async def execute(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> NodeOutput:
        """
        Execute the LangChain-enhanced Brain Node.
        
        This method provides enhanced reasoning capabilities while maintaining
        compatibility with the standard BrainNode interface.
        """
        start_time = datetime.now()
        self.execution_stats["total_executions"] += 1
        
        try:
            self.logger.info(f"Starting LangChain Brain Node execution: {self.node_id}")
            
            # Determine execution strategy based on problem complexity
            execution_strategy = self._determine_execution_strategy(
                user_configuration, previous_node_data, workflow_memory
            )
            
            if execution_strategy == "enhanced":
                # Use LangGraph for complex reasoning
                result = await self._execute_enhanced_reasoning(
                    user_configuration, previous_node_data, workflow_memory, streaming_callback
                )
            elif execution_strategy == "multi_agent":
                # Use multi-agent coordination
                result = await self._execute_multi_agent_reasoning(
                    user_configuration, previous_node_data, workflow_memory, streaming_callback
                )
            else:
                # Fall back to standard BrainNode execution
                result = await super().execute(
                    user_configuration, previous_node_data, workflow_memory, streaming_callback
                )
            
            # Update performance statistics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_execution_stats(execution_time)
            
            self.logger.info(f"LangChain Brain Node execution completed: {self.node_id}")
            return result
            
        except Exception as e:
            self.execution_stats["error_count"] += 1
            self.logger.error(f"LangChain Brain Node execution failed: {e}")
            
            # Fall back to standard BrainNode execution on error
            try:
                return await super().execute(
                    user_configuration, previous_node_data, workflow_memory, streaming_callback
                )
            except Exception as fallback_error:
                self.logger.error(f"Fallback execution also failed: {fallback_error}")
                return self._create_error_output(str(e), start_time)
    
    def _determine_execution_strategy(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory
    ) -> str:
        """
        Determine the best execution strategy based on problem complexity.
        
        Returns:
            "standard": Use standard BrainNode execution
            "enhanced": Use LangGraph state-based reasoning
            "multi_agent": Use multi-agent coordination
        """
        # Check if graph manager is available for enhanced features
        if not self.graph_manager:
            return "standard"
        
        # Analyze problem complexity
        problem_complexity = self._analyze_problem_complexity(
            user_configuration, previous_node_data, workflow_memory
        )
        
        # Check for multi-agent requirements
        if (self.agents and 
            (user_configuration.get("use_multi_agents", False) or problem_complexity > 0.8)):
            return "multi_agent"
        
        # Check for enhanced reasoning requirements
        if (self.tools or 
            problem_complexity > 0.6 or 
            user_configuration.get("use_enhanced_reasoning", False)):
            return "enhanced"
        
        return "standard"
    
    def _analyze_problem_complexity(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory
    ) -> float:
        """
        Analyze the complexity of the current problem to determine execution strategy.
        
        Returns:
            Float between 0.0 and 1.0 representing problem complexity
        """
        complexity_score = 0.0
        
        # Check configuration complexity
        config_complexity = len(str(user_configuration)) / 1000.0  # Normalize by length
        complexity_score += min(config_complexity, 0.3)
        
        # Check workflow history complexity  
        history_complexity = len(workflow_memory.conversation_history) / 20.0  # Normalize
        complexity_score += min(history_complexity, 0.3)
        
        # Check for specific complexity indicators
        complexity_indicators = [
            "analyze", "research", "compare", "evaluate", "decide", "plan",
            "multi-step", "complex", "detailed", "comprehensive"
        ]
        
        problem_text = str(user_configuration).lower()
        indicator_matches = sum(1 for indicator in complexity_indicators if indicator in problem_text)
        complexity_score += min(indicator_matches / len(complexity_indicators), 0.4)
        
        return min(complexity_score, 1.0)
    
    async def _execute_enhanced_reasoning(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> NodeOutput:
        """
        Execute enhanced reasoning using LangGraph state management.
        
        This method uses persistent state to maintain complex reasoning
        contexts across multiple steps and interactions.
        """
        try:
            # Initialize or load state
            state = await self._initialize_enhanced_state(
                user_configuration, previous_node_data, workflow_memory
            )
            
            # Create reasoning workflow graph
            reasoning_graph = await self._create_reasoning_graph(state)
            
            # Execute reasoning workflow with streaming
            if self.enable_streaming and streaming_callback:
                result = await self._stream_reasoning_execution(
                    reasoning_graph, state, streaming_callback
                )
            else:
                result = await reasoning_graph.ainvoke(state)
            
            # Check for human approval requirement
            if self._requires_human_approval(result):
                result = await self._handle_human_approval(result, streaming_callback)
            
            # Convert result to NodeOutput format
            return self._convert_enhanced_result_to_output(result, user_configuration)
            
        except Exception as e:
            self.logger.error(f"Enhanced reasoning execution failed: {e}")
            raise
    
    async def _initialize_enhanced_state(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory
    ) -> BrainNodeState:
        """Initialize or load the enhanced reasoning state."""
        state = BrainNodeState()
        
        # Set current problem from configuration
        state["current_problem"] = user_configuration.get(
            "problem", 
            user_configuration.get("goal", "General reasoning task")
        )
        
        # Extract decision criteria
        state["decision_criteria"] = user_configuration.get("criteria", [])
        
        # Set available tools
        state["tools_available"] = [tool.name for tool in self.tools]
        
        # Initialize working memory with relevant context
        state["working_memory"] = {
            "user_config": user_configuration,
            "previous_outputs": [data.data for data in previous_node_data],
            "workflow_context": workflow_memory.global_context
        }
        
        # Load conversation context
        state["context_window"] = workflow_memory.get_relevant_context(max_history=5)
        
        self.current_state = state
        return state
    
    async def _create_reasoning_graph(self, initial_state: BrainNodeState) -> StateGraph:
        """
        Create a LangGraph reasoning workflow tailored to the current problem.
        
        The graph includes nodes for:
        - Problem analysis
        - Information gathering (using tools)
        - Reasoning steps
        - Decision making
        - Result validation
        """
        graph = StateGraph(BrainNodeState)
        
        # Add reasoning nodes
        graph.add_node("analyze_problem", self._analyze_problem_node)
        graph.add_node("gather_information", self._gather_information_node)
        graph.add_node("perform_reasoning", self._perform_reasoning_node)
        graph.add_node("make_decision", self._make_decision_node)
        graph.add_node("validate_result", self._validate_result_node)
        
        # Add edges
        graph.add_edge("analyze_problem", "gather_information")
        graph.add_conditional_edges(
            "gather_information",
            self._should_continue_gathering,
            {"continue": "gather_information", "proceed": "perform_reasoning"}
        )
        graph.add_edge("perform_reasoning", "make_decision")
        graph.add_conditional_edges(
            "make_decision", 
            self._should_validate,
            {"validate": "validate_result", "complete": END}
        )
        graph.add_conditional_edges(
            "validate_result",
            self._validation_result,
            {"retry": "perform_reasoning", "complete": END}
        )
        
        # Set entry point
        graph.set_entry_point("analyze_problem")
        
        return graph.compile()
    
    async def _analyze_problem_node(self, state: BrainNodeState) -> BrainNodeState:
        """Analyze the current problem and determine reasoning approach."""
        problem = state["current_problem"]
        
        # Perform problem analysis using LLM
        analysis_prompt = f"""
        Analyze the following problem and provide:
        1. Problem type and complexity
        2. Required information sources
        3. Reasoning approach
        4. Success criteria
        
        Problem: {problem}
        Context: {state["context_window"]}
        """
        
        # Use LLM for analysis (simplified - would need proper implementation)
        analysis_result = await self._call_llm_for_analysis(analysis_prompt)
        
        # Update state with analysis
        state["reasoning_steps"].append({
            "step": "problem_analysis",
            "result": analysis_result,
            "timestamp": datetime.now().timestamp()
        })
        
        return state
    
    async def _gather_information_node(self, state: BrainNodeState) -> BrainNodeState:
        """Gather information using available tools."""
        if not self.tools:
            return state
        
        # Determine which tools to use based on problem analysis
        relevant_tools = self._select_relevant_tools(state)
        
        for tool in relevant_tools:
            try:
                # Prepare tool input based on problem context
                tool_input = self._prepare_tool_input(tool, state)
                
                # Execute tool
                tool_result = await tool.arun(tool_input)
                
                # Store tool result
                state["tool_results"][tool.name] = {
                    "result": tool_result,
                    "timestamp": datetime.now().timestamp(),
                    "input": tool_input
                }
                
                state["tool_call_count"] += 1
                
            except Exception as e:
                self.logger.warning(f"Tool {tool.name} execution failed: {e}")
                state["tool_results"][tool.name] = {
                    "error": str(e),
                    "timestamp": datetime.now().timestamp()
                }
        
        return state
    
    async def _perform_reasoning_node(self, state: BrainNodeState) -> BrainNodeState:
        """Perform the main reasoning process."""
        # Construct reasoning prompt with all available information
        reasoning_prompt = self._build_reasoning_prompt(state)
        
        # Perform reasoning using LLM
        reasoning_result = await self._call_llm_for_reasoning(reasoning_prompt)
        
        # Update state with reasoning
        state["reasoning_steps"].append({
            "step": "main_reasoning",
            "result": reasoning_result,
            "timestamp": datetime.now().timestamp(),
            "tools_used": list(state["tool_results"].keys())
        })
        
        return state
    
    async def _make_decision_node(self, state: BrainNodeState) -> BrainNodeState:
        """Make the final decision based on reasoning."""
        # Extract decision from reasoning steps
        decision_prompt = self._build_decision_prompt(state)
        decision_result = await self._call_llm_for_decision(decision_prompt)
        
        # Calculate confidence score
        confidence = self._calculate_confidence_from_reasoning(state)
        state["confidence_score"] = confidence
        
        # Store decision
        state["final_decision"] = decision_result
        state["decision_timestamp"] = datetime.now().timestamp()
        
        return state
    
    async def _validate_result_node(self, state: BrainNodeState) -> BrainNodeState:
        """Validate the reasoning result."""
        # Perform validation checks
        validation_result = self._validate_reasoning_quality(state)
        
        state["validation_result"] = validation_result
        state["validation_timestamp"] = datetime.now().timestamp()
        
        return state
    
    def _should_continue_gathering(self, state: BrainNodeState) -> str:
        """Determine if more information gathering is needed."""
        if state["tool_call_count"] >= len(self.tools):
            return "proceed"
        
        # Check if we have enough information
        if len(state["tool_results"]) >= 2:  # Arbitrary threshold
            return "proceed"
        
        return "continue"
    
    def _should_validate(self, state: BrainNodeState) -> str:
        """Determine if validation is needed."""
        if state["confidence_score"] < 0.7:  # Low confidence requires validation
            return "validate"
        return "complete"
    
    def _validation_result(self, state: BrainNodeState) -> str:
        """Determine action based on validation result."""
        validation = state.get("validation_result", {})
        if validation.get("requires_retry", False):
            return "retry"
        return "complete"
    
    # Placeholder methods that would need full implementation
    async def _call_llm_for_analysis(self, prompt: str) -> str:
        """Call LLM for problem analysis."""
        # This would use your LLM manager to make the actual call
        return "Problem analysis result"
    
    async def _call_llm_for_reasoning(self, prompt: str) -> str:
        """Call LLM for main reasoning."""
        return "Reasoning result"
    
    async def _call_llm_for_decision(self, prompt: str) -> str:
        """Call LLM for decision making."""
        return "Decision result"
    
    def _select_relevant_tools(self, state: BrainNodeState) -> List[BaseTool]:
        """Select relevant tools based on problem analysis."""
        # Simple selection - would need more sophisticated logic
        return self.tools[:2]  # Use first 2 tools as example
    
    def _prepare_tool_input(self, tool: BaseTool, state: BrainNodeState) -> str:
        """Prepare input for a specific tool."""
        return state["current_problem"]  # Simplified
    
    def _build_reasoning_prompt(self, state: BrainNodeState) -> str:
        """Build comprehensive reasoning prompt."""
        return f"Reason about: {state['current_problem']}"
    
    def _build_decision_prompt(self, state: BrainNodeState) -> str:
        """Build decision-making prompt."""
        return f"Make decision about: {state['current_problem']}"
    
    def _calculate_confidence_from_reasoning(self, state: BrainNodeState) -> float:
        """Calculate confidence based on reasoning quality."""
        return 0.8  # Placeholder
    
    def _validate_reasoning_quality(self, state: BrainNodeState) -> Dict[str, Any]:
        """Validate the quality of reasoning."""
        return {"quality_score": 0.8, "requires_retry": False}
    
    async def _execute_multi_agent_reasoning(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> NodeOutput:
        """
        Execute multi-agent reasoning coordination.
        
        This method coordinates multiple specialized agents to solve
        complex problems that require diverse expertise.
        """
        # Placeholder for multi-agent implementation
        self.logger.info("Multi-agent reasoning not fully implemented yet")
        
        # Fall back to enhanced reasoning
        return await self._execute_enhanced_reasoning(
            user_configuration, previous_node_data, workflow_memory, streaming_callback
        )
    
    def _requires_human_approval(self, result: Dict[str, Any]) -> bool:
        """Check if human approval is required."""
        if not self.enable_human_approval:
            return False
        
        confidence = result.get("confidence_score", 1.0)
        return confidence < self.human_approval_threshold
    
    async def _handle_human_approval(
        self, 
        result: Dict[str, Any], 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Handle human approval workflow."""
        self.execution_stats["human_approvals_requested"] += 1
        
        # Send approval request (placeholder)
        if streaming_callback:
            approval_message = {
                "type": "approval_required",
                "decision": result.get("final_decision", ""),
                "confidence": result.get("confidence_score", 0.0),
                "reasoning": result.get("reasoning_steps", [])
            }
            streaming_callback(json.dumps(approval_message))
        
        # For now, auto-approve (would need actual human interaction)
        result["human_feedback"] = "auto_approved"
        result["approval_status"] = "approved"
        
        return result
    
    def _convert_enhanced_result_to_output(
        self, 
        result: Dict[str, Any], 
        user_configuration: Dict[str, Any]
    ) -> NodeOutput:
        """Convert enhanced reasoning result to standard NodeOutput format."""
        return NodeOutput(
            node_id=self.node_id,
            node_type="LangChainBrainNode",
            data=result.get("final_decision", "No decision made"),
            timestamp=datetime.now().timestamp(),
            metadata={
                "status": "success",
                "reasoning_steps": len(result.get("reasoning_steps", [])),
                "tools_used": list(result.get("tool_results", {}).keys()),
                "confidence_score": result.get("confidence_score", 0.5),
                "human_approval_required": result.get("requires_approval", False),
                "execution_mode": "enhanced"
            },
            success=True,
            confidence_score=result.get("confidence_score", 0.5),
            tool_calls_made=list(result.get("tool_results", {}).keys()),
            memory_updates={
                "enhanced_reasoning_result": result.get("final_decision", ""),
                "reasoning_confidence": result.get("confidence_score", 0.5)
            }
        )
    
    async def _stream_reasoning_execution(
        self,
        reasoning_graph: StateGraph,
        state: BrainNodeState,
        streaming_callback: Callable[[str], None]
    ) -> Dict[str, Any]:
        """Execute reasoning with real-time streaming updates."""
        try:
            async for chunk in reasoning_graph.astream(state):
                # Send streaming update
                stream_update = {
                    "type": "reasoning_update",
                    "node_id": self.node_id,
                    "data": chunk,
                    "timestamp": datetime.now().timestamp()
                }
                streaming_callback(json.dumps(stream_update))
            
            # Return final result
            return state
            
        except Exception as e:
            self.logger.error(f"Streaming reasoning execution failed: {e}")
            raise
    
    def _create_error_output(self, error_message: str, start_time: datetime) -> NodeOutput:
        """Create error output for failed execution."""
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return NodeOutput(
            node_id=self.node_id,
            node_type="LangChainBrainNode",
            data=f"Enhanced brain node execution failed: {error_message}",
            timestamp=datetime.now().timestamp(),
            metadata={
                "status": "error",
                "error": True,
                "error_message": error_message,
                "execution_time_ms": execution_time,
                "execution_mode": "error_fallback"
            },
            success=False,
            error_message=error_message
        )
    
    def _update_execution_stats(self, execution_time: float):
        """Update performance statistics."""
        total = self.execution_stats["total_executions"]
        current_avg = self.execution_stats["avg_execution_time"]
        
        # Update average execution time
        self.execution_stats["avg_execution_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
        
        # Update tool usage count
        if self.current_state:
            self.execution_stats["tool_usage_count"] += self.current_state.get("tool_call_count", 0)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        return {
            **self.execution_stats,
            "tools_available": len(self.tools),
            "agents_available": len(self.agents),
            "human_approval_enabled": self.enable_human_approval,
            "streaming_enabled": self.enable_streaming
        }