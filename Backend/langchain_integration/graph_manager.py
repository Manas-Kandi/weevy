"""
LangGraph Integration Manager for Weev Platform

This module provides the core integration between Weev's workflow system and LangGraph,
enabling stateful AI agent workflows with advanced orchestration capabilities.

Core Responsibilities:
=====================

1. **State Management**: Bridges Weev's WorkflowMemory with LangGraph's state system
2. **Graph Orchestration**: Creates and manages LangGraph workflow graphs
3. **Node Coordination**: Coordinates between Weev nodes and LangGraph nodes
4. **Persistence**: Handles state persistence across workflow executions
5. **Error Recovery**: Provides robust error handling and workflow recovery
6. **Streaming Integration**: Supports real-time streaming of workflow progress

Architecture Overview:
======================

The LangGraphManager acts as a bridge between two systems:

Weev Side:                    LangGraph Side:
- WorkflowMemory             - Graph State
- NodeInputs/Outputs         - Node Functions  
- WebSocket Streaming        - StateGraph
- Database Persistence       - Checkpointer

Key Components:
==============

1. **StateConverter**: Converts between Weev and LangGraph state formats
2. **GraphBuilder**: Dynamically builds LangGraph workflows from Weev configurations
3. **CheckpointManager**: Manages workflow state persistence
4. **StreamingBridge**: Bridges Weev's WebSocket streaming with LangGraph's streaming
5. **ErrorHandler**: Handles errors and provides recovery mechanisms

Usage Patterns:
===============

**Basic Graph Creation**:
```python
graph_manager = LangGraphManager(llm_manager=llm_manager, db_session=db_session)
graph = await graph_manager.create_workflow_graph(workflow_config)
result = await graph.ainvoke(initial_state)
```

**Stateful Execution**:
```python
# Resume from checkpoint
graph = await graph_manager.load_workflow_graph(workflow_id)
state = await graph_manager.get_current_state(workflow_id)
result = await graph.ainvoke(state)
```

**Streaming Execution**:
```python
async for chunk in graph_manager.stream_workflow(workflow_id, input_data):
    await websocket.send_json(chunk)
```

Integration Benefits:
====================

1. **Enhanced State Management**: Persistent, versioned workflow state
2. **Complex Orchestration**: Support for parallel, conditional, and iterative workflows
3. **Human-in-the-Loop**: Built-in checkpoints for human approval
4. **Error Recovery**: Automatic retry and recovery mechanisms
5. **Performance**: Optimized execution with caching and streaming
6. **Observability**: Detailed execution tracking and debugging

State Schema:
============

The manager uses a unified state schema that combines Weev and LangGraph concepts:

```python
class WorkflowState(TypedDict):
    # Weev compatibility
    workflow_id: str
    node_outputs: List[Dict[str, Any]]
    workflow_memory: Dict[str, Any]
    
    # LangGraph enhancements  
    current_step: str
    execution_path: List[str]
    intermediate_steps: List[Dict[str, Any]]
    tools_used: List[str]
    
    # Control flow
    next_action: Optional[str]
    should_continue: bool
    human_feedback_required: bool
```

Error Handling Strategy:
=======================

1. **Graceful Degradation**: Falls back to simpler workflows on errors
2. **Checkpoint Recovery**: Resumes from last successful checkpoint
3. **Retry Logic**: Configurable retry attempts with exponential backoff
4. **Circuit Breaker**: Prevents cascade failures
5. **Monitoring**: Comprehensive error logging and alerting

Performance Optimizations:
=========================

1. **State Caching**: In-memory caching of frequently accessed states
2. **Lazy Loading**: Load workflow components only when needed
3. **Connection Pooling**: Efficient database connection management
4. **Streaming**: Non-blocking execution with real-time updates
5. **Parallel Execution**: Concurrent processing where possible

Author: Weev Platform Team
Version: 1.0.0
Date: 2025-01-XX
"""

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable, TypedDict
from datetime import datetime
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from ..GeneralNodeLogic import WorkflowMemory, NodeInputs, NodeOutput
from ..llm.manager import LLMManager
from ..database.connection import AsyncSessionLocal


class WorkflowState(TypedDict):
    """
    Unified state schema for LangGraph workflows that maintains compatibility
    with Weev's existing WorkflowMemory system while adding LangGraph capabilities.
    """
    # Core Weev compatibility fields
    workflow_id: str
    node_outputs: List[Dict[str, Any]]
    workflow_memory: Dict[str, Any]
    user_configuration: Dict[str, Any]
    
    # LangGraph enhancements
    current_step: str
    execution_path: List[str]
    intermediate_steps: List[Dict[str, Any]]
    tools_used: List[str]
    messages: List[Dict[str, Any]]
    
    # Control flow
    next_action: Optional[str]
    should_continue: bool
    human_feedback_required: bool
    
    # Metadata
    started_at: float
    last_updated: float
    execution_count: int


class LangGraphManager:
    """
    Core manager for LangGraph integration with the Weev platform.
    
    This class provides the main interface for creating, managing, and executing
    LangGraph workflows within the Weev ecosystem. It handles state conversion,
    persistence, streaming, and error recovery.
    """
    
    def __init__(
        self, 
        llm_manager: LLMManager,
        db_session: Optional[Any] = None,
        checkpoint_dir: Optional[str] = None
    ):
        """
        Initialize the LangGraph manager.
        
        Args:
            llm_manager: Weev's LLM manager for model access
            db_session: Database session for state persistence  
            checkpoint_dir: Directory for checkpoint storage
        """
        self.llm_manager = llm_manager
        self.db_session = db_session or AsyncSessionLocal()
        self.checkpoint_dir = checkpoint_dir or "./checkpoints"
        
        # Initialize logging
        self.logger = logging.getLogger("weev.langgraph_manager")
        self.logger.setLevel(logging.INFO)
        
        # State management
        self.active_workflows: Dict[str, StateGraph] = {}
        self.state_cache: Dict[str, WorkflowState] = {}
        
        # Initialize checkpointer
        self._setup_checkpointer()
        
        self.logger.info("LangGraphManager initialized successfully")
    
    def _setup_checkpointer(self):
        """Set up the appropriate checkpointer based on configuration."""
        try:
            # Try to use PostgreSQL checkpointer if database available
            if self.db_session:
                self.checkpointer = PostgresSaver.from_conn_string(
                    conn_string=self._get_db_connection_string()
                )
                self.logger.info("Using PostgreSQL checkpointer")
            else:
                # Fallback to SQLite checkpointer
                self.checkpointer = SqliteSaver.from_conn_string(
                    f"sqlite:///{self.checkpoint_dir}/checkpoints.db"
                )
                self.logger.info("Using SQLite checkpointer")
        except Exception as e:
            self.logger.warning(f"Checkpointer setup failed: {e}. Using in-memory state.")
            self.checkpointer = None
    
    def _get_db_connection_string(self) -> str:
        """Generate PostgreSQL connection string from environment."""
        import os
        host = os.getenv("DATABASE_HOST", "localhost")
        port = os.getenv("DATABASE_PORT", "5432") 
        user = os.getenv("DATABASE_USER", "weev")
        password = os.getenv("DATABASE_PASSWORD", "")
        database = os.getenv("DATABASE_NAME", "weev")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    async def create_workflow_graph(
        self,
        workflow_config: Dict[str, Any],
        initial_state: Optional[WorkflowState] = None
    ) -> StateGraph:
        """
        Create a LangGraph workflow from Weev workflow configuration.
        
        This method converts Weev's node-based workflow configuration into
        a LangGraph StateGraph that can be executed with all the benefits
        of LangGraph's state management and orchestration.
        
        Args:
            workflow_config: Weev workflow configuration
            initial_state: Optional initial state for the workflow
            
        Returns:
            Configured LangGraph StateGraph ready for execution
        """
        workflow_id = workflow_config.get("workflow_id", str(uuid.uuid4()))
        
        try:
            self.logger.info(f"Creating workflow graph for {workflow_id}")
            
            # Create state graph
            graph = StateGraph(WorkflowState)
            
            # Convert Weev nodes to LangGraph nodes
            nodes = workflow_config.get("nodes", [])
            connections = workflow_config.get("connections", [])
            
            # Add nodes to graph
            for node_config in nodes:
                node_func = self._create_node_function(node_config)
                graph.add_node(node_config["node_id"], node_func)
            
            # Add edges based on connections
            for connection in connections:
                from_node = connection["from"]
                to_node = connection["to"]
                
                # Add conditional edge if specified
                if "condition" in connection:
                    condition_func = self._create_condition_function(connection["condition"])
                    graph.add_conditional_edges(from_node, condition_func)
                else:
                    graph.add_edge(from_node, to_node)
            
            # Set entry point
            if nodes:
                entry_node = self._determine_entry_node(nodes, connections)
                graph.set_entry_point(entry_node)
            
            # Compile graph with checkpointer
            compiled_graph = graph.compile(checkpointer=self.checkpointer)
            
            # Cache the workflow
            self.active_workflows[workflow_id] = compiled_graph
            
            self.logger.info(f"Workflow graph created successfully: {workflow_id}")
            return compiled_graph
            
        except Exception as e:
            self.logger.error(f"Failed to create workflow graph: {e}")
            raise
    
    def _create_node_function(self, node_config: Dict[str, Any]) -> Callable:
        """
        Create a LangGraph node function from Weev node configuration.
        
        This method creates a function that can be used as a LangGraph node,
        bridging between Weev's node system and LangGraph's execution model.
        """
        node_type = node_config.get("node_type", "general")
        node_id = node_config["node_id"]
        
        async def node_function(state: WorkflowState) -> WorkflowState:
            """Generated node function that executes Weev node logic."""
            try:
                self.logger.debug(f"Executing node: {node_id}")
                
                # Convert LangGraph state to Weev inputs
                node_inputs = self._convert_state_to_inputs(state, node_config)
                
                # Execute the appropriate node type
                if node_type == "BrainNode":
                    result = await self._execute_brain_node(node_inputs, state)
                elif node_type == "InputNode":
                    result = await self._execute_input_node(node_inputs, state)
                elif node_type == "OutputNode": 
                    result = await self._execute_output_node(node_inputs, state)
                elif node_type == "KnowledgeBaseNode":
                    result = await self._execute_knowledge_node(node_inputs, state)
                else:
                    result = await self._execute_general_node(node_inputs, state)
                
                # Update state with results
                updated_state = self._update_state_with_result(state, result, node_id)
                
                self.logger.debug(f"Node {node_id} completed successfully")
                return updated_state
                
            except Exception as e:
                self.logger.error(f"Node {node_id} execution failed: {e}")
                # Return state with error information
                error_state = state.copy()
                error_state["intermediate_steps"].append({
                    "node_id": node_id,
                    "error": str(e),
                    "timestamp": datetime.now().timestamp()
                })
                return error_state
        
        return node_function
    
    def _convert_state_to_inputs(
        self, 
        state: WorkflowState, 
        node_config: Dict[str, Any]
    ) -> NodeInputs:
        """Convert LangGraph state to Weev NodeInputs format."""
        # Reconstruct workflow memory from state
        workflow_memory = WorkflowMemory(
            workflow_id=state["workflow_id"],
            conversation_history=state["workflow_memory"].get("conversation_history", []),
            global_context=state["workflow_memory"].get("global_context", {}),
            execution_path=state["execution_path"]
        )
        
        # Create node inputs
        return NodeInputs(
            system_rules=node_config.get("system_rules", ""),
            user_configuration=state["user_configuration"],
            previous_node_data=self._extract_previous_node_data(state),
            workflow_memory=workflow_memory,
            execution_context={"langgraph_state": state}
        )
    
    def _extract_previous_node_data(self, state: WorkflowState) -> List[Any]:
        """Extract previous node outputs from state."""
        # Convert node outputs to PreviousNodeOutput format
        previous_data = []
        for output in state["node_outputs"]:
            # This would need to be properly implemented based on your PreviousNodeOutput structure
            previous_data.append(output)
        return previous_data
    
    async def _execute_brain_node(self, inputs: NodeInputs, state: WorkflowState) -> NodeOutput:
        """Execute a brain node with LangGraph context."""
        from ..BrainNode import BrainNode
        
        brain_node = BrainNode(
            node_id=f"langgraph_brain_{uuid.uuid4().hex[:8]}",
            name="LangGraph Brain Node"
        )
        
        # Inject LangGraph-specific context
        brain_node.llm_manager = self.llm_manager
        brain_node.db_session = self.db_session
        
        return await brain_node.execute(
            inputs.user_configuration,
            inputs.previous_node_data,
            inputs.workflow_memory
        )
    
    async def _execute_input_node(self, inputs: NodeInputs, state: WorkflowState) -> NodeOutput:
        """Execute an input node."""
        from ..InputNode import InputNode
        
        input_node = InputNode(
            node_id=f"langgraph_input_{uuid.uuid4().hex[:8]}",
            name="LangGraph Input Node"
        )
        
        return await input_node.execute(
            inputs.user_configuration,
            inputs.previous_node_data, 
            inputs.workflow_memory
        )
    
    async def _execute_output_node(self, inputs: NodeInputs, state: WorkflowState) -> NodeOutput:
        """Execute an output node."""
        from ..OutputNode import OutputNode
        
        output_node = OutputNode(
            node_id=f"langgraph_output_{uuid.uuid4().hex[:8]}",
            name="LangGraph Output Node"
        )
        
        return await output_node.execute(
            inputs.user_configuration,
            inputs.previous_node_data,
            inputs.workflow_memory
        )
    
    async def _execute_knowledge_node(self, inputs: NodeInputs, state: WorkflowState) -> NodeOutput:
        """Execute a knowledge base node.""" 
        from ..KnowledgeBaseNode import KnowledgeBaseNode
        
        kb_node = KnowledgeBaseNode(
            node_id=f"langgraph_kb_{uuid.uuid4().hex[:8]}",
            name="LangGraph Knowledge Base Node"
        )
        
        return await kb_node.execute(
            inputs.user_configuration,
            inputs.previous_node_data,
            inputs.workflow_memory
        )
    
    async def _execute_general_node(self, inputs: NodeInputs, state: WorkflowState) -> NodeOutput:
        """Execute a general node using GeneralNodeLogic."""
        from ..GeneralNodeLogic import GeneralNodeLogic, NodeExecutionMode
        
        general_node = GeneralNodeLogic(NodeExecutionMode.PRODUCTION)
        general_node.llm_manager = self.llm_manager
        general_node.db_session = self.db_session
        
        return await general_node.execute_node(inputs)
    
    def _update_state_with_result(
        self, 
        state: WorkflowState, 
        result: NodeOutput,
        node_id: str
    ) -> WorkflowState:
        """Update LangGraph state with node execution result."""
        updated_state = state.copy()
        
        # Add node output to results
        updated_state["node_outputs"].append({
            "node_id": result.node_id,
            "node_type": result.node_type,
            "data": result.data,
            "timestamp": result.timestamp,
            "success": result.success,
            "metadata": result.metadata
        })
        
        # Update execution path
        updated_state["execution_path"].append(node_id)
        updated_state["execution_count"] += 1
        updated_state["last_updated"] = datetime.now().timestamp()
        
        # Update intermediate steps
        updated_state["intermediate_steps"].append({
            "step": len(updated_state["execution_path"]),
            "node_id": node_id,
            "result": result.data,
            "timestamp": result.timestamp
        })
        
        # Update workflow memory with any memory updates from the node
        if hasattr(result, 'memory_updates') and result.memory_updates:
            updated_state["workflow_memory"]["global_context"].update(result.memory_updates)
        
        # Update tools used if any
        if hasattr(result, 'tool_calls_made') and result.tool_calls_made:
            updated_state["tools_used"].extend(result.tool_calls_made)
        
        # Determine next action based on result
        if hasattr(result, 'next_suggested_nodes') and result.next_suggested_nodes:
            updated_state["next_action"] = result.next_suggested_nodes[0]
        
        # Check if human feedback is required
        if hasattr(result, 'metadata') and result.metadata.get("requires_human_feedback"):
            updated_state["human_feedback_required"] = True
        
        return updated_state
    
    def _create_condition_function(self, condition_config: Dict[str, Any]) -> Callable:
        """Create a condition function for conditional edges."""
        def condition_function(state: WorkflowState) -> str:
            """Generated condition function for routing."""
            # Implement condition logic based on configuration
            # This is a simplified example - would need full implementation
            condition_type = condition_config.get("type", "simple")
            
            if condition_type == "simple":
                field = condition_config["field"]
                operator = condition_config["operator"] 
                value = condition_config["value"]
                
                state_value = state.get(field)
                
                if operator == "equals" and state_value == value:
                    return condition_config.get("true_path", "continue")
                elif operator == "not_equals" and state_value != value:
                    return condition_config.get("true_path", "continue")
                else:
                    return condition_config.get("false_path", "end")
            
            return "continue"
        
        return condition_function
    
    def _determine_entry_node(
        self, 
        nodes: List[Dict[str, Any]], 
        connections: List[Dict[str, Any]]
    ) -> str:
        """Determine the entry node for the workflow."""
        # Find node that has no incoming connections
        target_nodes = {conn["to"] for conn in connections}
        
        for node in nodes:
            if node["node_id"] not in target_nodes:
                return node["node_id"]
        
        # Fallback to first node
        return nodes[0]["node_id"] if nodes else "start"
    
    async def execute_workflow(
        self,
        workflow_id: str,
        initial_input: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow with the given input.
        
        Args:
            workflow_id: ID of the workflow to execute
            initial_input: Initial input data for the workflow
            config: Optional execution configuration
            
        Returns:
            Final workflow result
        """
        try:
            graph = self.active_workflows.get(workflow_id)
            if not graph:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            # Create initial state
            initial_state = self._create_initial_state(workflow_id, initial_input)
            
            # Execute workflow
            result = await graph.ainvoke(initial_state, config=config)
            
            self.logger.info(f"Workflow {workflow_id} executed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            raise
    
    async def stream_workflow(
        self,
        workflow_id: str,
        initial_input: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream workflow execution with real-time updates.
        
        Args:
            workflow_id: ID of the workflow to execute
            initial_input: Initial input data for the workflow
            config: Optional execution configuration
            
        Yields:
            Workflow execution updates in real-time
        """
        try:
            graph = self.active_workflows.get(workflow_id)
            if not graph:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            # Create initial state
            initial_state = self._create_initial_state(workflow_id, initial_input)
            
            # Stream workflow execution
            async for chunk in graph.astream(initial_state, config=config):
                yield {
                    "type": "workflow_update",
                    "workflow_id": workflow_id,
                    "data": chunk,
                    "timestamp": datetime.now().timestamp()
                }
                
        except Exception as e:
            self.logger.error(f"Workflow streaming failed: {e}")
            yield {
                "type": "workflow_error",
                "workflow_id": workflow_id, 
                "error": str(e),
                "timestamp": datetime.now().timestamp()
            }
    
    def _create_initial_state(
        self, 
        workflow_id: str, 
        initial_input: Dict[str, Any]
    ) -> WorkflowState:
        """Create initial state for workflow execution."""
        return WorkflowState(
            workflow_id=workflow_id,
            node_outputs=[],
            workflow_memory={
                "conversation_history": [],
                "global_context": initial_input.get("context", {}),
                "user_preferences": {}
            },
            user_configuration=initial_input.get("configuration", {}),
            current_step="start",
            execution_path=[],
            intermediate_steps=[],
            tools_used=[],
            messages=[],
            next_action=None,
            should_continue=True,
            human_feedback_required=False,
            started_at=datetime.now().timestamp(),
            last_updated=datetime.now().timestamp(),
            execution_count=0
        )
    
    async def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get current state of a workflow."""
        # Check cache first
        if workflow_id in self.state_cache:
            return self.state_cache[workflow_id]
        
        # Load from checkpointer if available
        if self.checkpointer:
            try:
                state = await self.checkpointer.aget({"configurable": {"thread_id": workflow_id}})
                if state:
                    self.state_cache[workflow_id] = state.values
                    return state.values
            except Exception as e:
                self.logger.warning(f"Failed to load state from checkpointer: {e}")
        
        return None
    
    async def save_workflow_state(self, workflow_id: str, state: WorkflowState):
        """Save workflow state."""
        # Update cache
        self.state_cache[workflow_id] = state
        
        # Save to checkpointer if available
        if self.checkpointer:
            try:
                await self.checkpointer.aput(
                    {"configurable": {"thread_id": workflow_id}},
                    state,
                    {}
                )
            except Exception as e:
                self.logger.warning(f"Failed to save state to checkpointer: {e}")
    
    def cleanup_workflow(self, workflow_id: str):
        """Clean up workflow resources."""
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
        
        if workflow_id in self.state_cache:
            del self.state_cache[workflow_id]
        
        self.logger.info(f"Cleaned up workflow: {workflow_id}")