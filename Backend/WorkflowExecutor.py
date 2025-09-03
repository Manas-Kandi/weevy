
import asyncio
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from BrainNode import BrainNode
from InputNode import InputNode
from OutputNode import OutputNode
from KnowledgeBaseNode import KnowledgeBaseNode
from ToolNode import ToolNode
from GeneralNodeLogic import NodeInputs, WorkflowMemory, PreviousNodeOutput
from WorkflowInputProcessor import WorkflowInputProcessor, ProcessingMode
from ToolOrchestrator import ToolOrchestrator
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import WorkflowExecution

# Support both canonical short types and class-like names
NODE_CLASSES = {
    # canonical
    "brain": BrainNode,
    "input": InputNode,
    "output": OutputNode,
    "knowledge": KnowledgeBaseNode,
    "tool": ToolNode,
    # class-style
    "BrainNode": BrainNode,
    "InputNode": InputNode,
    "OutputNode": OutputNode,
    "KnowledgeBaseNode": KnowledgeBaseNode,
    "ToolNode": ToolNode,
}

class WorkflowExecutor:
    def __init__(
        self,
        workflow: Dict[str, Any],
        manager,
        execution_id: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        llm_manager: Any | None = None,
        user_id: Optional[str] = None,
        available_tools: Optional[Dict[str, Any]] = None,
        processing_mode: ProcessingMode = ProcessingMode.PRODUCTION
    ):
        self.workflow = workflow
        self.manager = manager
        self.execution_id = execution_id
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.user_id = user_id
        self.available_tools = available_tools or {}
        self.processing_mode = processing_mode
        
        # Enhanced execution components
        self.workflow_processor = WorkflowInputProcessor(processing_mode)
        self.tool_orchestrator = ToolOrchestrator(self.available_tools) if self.available_tools else None
        self.node_results: Dict[str, PreviousNodeOutput] = {}
        self.workflow_memory = WorkflowMemory(workflow_id=self.workflow.get("workflow_id"))
        self.logger = logging.getLogger(f"{__name__}.WorkflowExecutor")

    async def execute(self):
        """Execute workflow with enhanced input processing and intelligent tool orchestration."""
        try:
            self.logger.info(f"Starting enhanced workflow execution: {self.workflow.get('workflow_id')}")
            
            # Process workflow inputs using WorkflowInputProcessor
            processing_result = self.workflow_processor.process_workflow(self.workflow)
            
            if processing_result.validation_summary:
                self.logger.warning(f"Validation issues found: {processing_result.validation_summary}")
            
            # Update workflow memory with global context
            self.workflow_memory.global_context.update(processing_result.global_context)
            
            # Broadcast workflow started
            import json
            await self.manager.broadcast(json.dumps({
                "type": "workflow_started",
                "workflow_id": processing_result.workflow_id,
                "execution_id": self.execution_id,
                "message": "Enhanced workflow execution started",
                "processing_mode": processing_result.processing_mode.value,
                "total_nodes": len(processing_result.processed_nodes)
            }))
            
            # Execute nodes in the calculated order
            for node_id in processing_result.execution_order:
                if node_id not in processing_result.processed_nodes:
                    continue
                    
                processed_node = processing_result.processed_nodes[node_id]
                
                # Skip nodes with validation errors in production mode
                if (processed_node.validation_errors and 
                    self.processing_mode == ProcessingMode.PRODUCTION):
                    self.logger.error(f"Skipping node {node_id} due to validation errors: {processed_node.validation_errors}")
                    continue
                
                try:
                    await self._execute_processed_node(processed_node, processing_result.connection_graph)
                    
                except Exception as e:
                    self.logger.error(f"Node {node_id} execution failed: {e}")
                    await self.manager.broadcast(json.dumps({
                        "type": "execution_error",
                        "node_id": node_id,
                        "execution_id": self.execution_id,
                        "error": str(e),
                        "message": "Error executing enhanced node"
                    }))
                    
                    # Decide whether to continue or stop based on error severity
                    if self._is_critical_error(e, processed_node):
                        await self._persist_status(status="failed", error=str(e))
                        return
            
            # Workflow completed successfully
            await self.manager.broadcast(json.dumps({
                "type": "workflow_finished",
                "workflow_id": processing_result.workflow_id,
                "execution_id": self.execution_id,
                "message": "Enhanced workflow execution completed",
                "total_execution_time": "calculated_later"
            }))
            
            # Persist final results
            summary = {nid: getattr(out, 'data', None) for nid, out in self.node_results.items()}
            await self._persist_status(status="completed", results=summary)
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            await self.manager.broadcast(json.dumps({
                "type": "execution_error",
                "execution_id": self.execution_id,
                "error": str(e),
                "message": "Workflow execution failed"
            }))
            await self._persist_status(status="failed", error=str(e))

    async def _execute_processed_node(self, processed_node, connection_graph: Dict[str, List[str]]):
        """Execute a processed node with enhanced configuration."""
        node_id = processed_node.node_id
        node_type = processed_node.node_type
        
        # Get input data from connected nodes
        input_data = self._get_input_for_processed_node(node_id, connection_graph)
        
        # Create node instance
        if node_type not in NODE_CLASSES:
            raise ValueError(f"Unknown node type: {node_type}")
        
        node_class = NODE_CLASSES[node_type]
        
        # Special handling for BrainNode with tool orchestration
        if node_type in ['brain', 'BrainNode']:
            node_instance = node_class(
                node_id, 
                f"{node_type}_{node_id}",
                available_tools=self.available_tools,
                tool_orchestrator=self.tool_orchestrator
            )
        else:
            node_instance = node_class(node_id, f"{node_type}_{node_id}")
        
        # Inject runtime dependencies
        self._inject_node_dependencies(node_instance)
        
        # Create enhanced NodeInputs using processed configuration
        inputs = NodeInputs(
            system_rules=processed_node.system_instructions,
            user_configuration=processed_node.configuration,
            previous_node_data=input_data,
            workflow_memory=self.workflow_memory,
        )
        
        # Execute node
        result = await node_instance.execute(
            inputs.user_configuration,
            inputs.previous_node_data,
            inputs.workflow_memory,
        )
        
        # Convert result and store
        prev_out = self._to_previous_output(node_id, node_type, result)
        self.node_results[node_id] = prev_out
        
        # Broadcast execution result
        import json
        await self.manager.broadcast(json.dumps({
            "type": "node_executed",
            "node_id": node_id,
            "execution_id": self.execution_id,
            "result": str(prev_out.data)[:500],  # Truncate long results
            "node_type": node_type,
            "success": prev_out.success,
            "confidence": getattr(result, 'confidence_score', 0.0),
            "message": "Enhanced node executed successfully"
        }))

    def _get_input_for_processed_node(self, node_id: str, connection_graph: Dict[str, List[str]]) -> List[PreviousNodeOutput]:
        """Get input data for a node from its connected predecessors."""
        input_data = []
        
        # Find nodes that connect TO this node
        for from_node_id, to_node_ids in connection_graph.items():
            if node_id in to_node_ids and from_node_id in self.node_results:
                input_data.append(self.node_results[from_node_id])
        
        return input_data

    def _inject_node_dependencies(self, node_instance):
        """Inject runtime dependencies into node instance."""
        try:
            if hasattr(node_instance, 'llm_manager'):
                node_instance.llm_manager = self.llm_manager
            if hasattr(node_instance, 'db_session'):
                node_instance.db_session = self.db_session
            if hasattr(node_instance, 'execution_id'):
                node_instance.execution_id = self.execution_id
            if hasattr(node_instance, 'user_id'):
                node_instance.user_id = self.user_id
        except Exception as e:
            self.logger.warning(f"Failed to inject dependencies: {e}")

    def _is_critical_error(self, error: Exception, processed_node) -> bool:
        """Determine if an error is critical enough to stop workflow execution."""
        # Consider node type and error type
        if processed_node.node_type in ['input', 'brain']:
            return True  # Input and brain nodes are usually critical
        
        # Check for specific error types
        if isinstance(error, (ValueError, TypeError, KeyError)):
            return True
        
        return False

    async def _persist_status(self, status: str, results: Optional[dict] = None, error: Optional[str] = None) -> None:
        if not self.db_session or not self.execution_id:
            return
        try:
            exe_id = self.execution_id
            if isinstance(exe_id, str):
                try:
                    exe_id = uuid.UUID(exe_id)
                except Exception:
                    return
            exe = await self.db_session.get(WorkflowExecution, exe_id)
            if not exe:
                return
            exe.status = status
            if results is not None:
                exe.results = results
            if error is not None:
                exe.error_message = error
            if status in ("failed", "completed"):
                from datetime import datetime as _dt
                exe.completed_at = _dt.utcnow()
            await self.db_session.commit()
        except Exception:
            # Don't crash execution if DB update fails
            pass

    def get_input_for_node(self, node_id: str, connections: List[Dict[str, str]]) -> List[PreviousNodeOutput]:
        input_data: List[PreviousNodeOutput] = []
        parent_connections = [conn for conn in connections if conn['to'] == node_id]

        for conn in parent_connections:
            parent_node_id = conn['from']
            if parent_node_id in self.node_results:
                input_data.append(self.node_results[parent_node_id])

        return input_data

    def _to_previous_output(self, node_id: str, node_type: str, result: PreviousNodeOutput | Any) -> PreviousNodeOutput:
        """Normalize any node result to PreviousNodeOutput expected downstream.

        If `result` is already a PreviousNodeOutput, return it. Otherwise, assume it
        is a NodeOutput-like object and map fields with safe defaults.
        """
        if isinstance(result, PreviousNodeOutput):
            return result

        # Best-effort extraction from NodeOutput
        data = getattr(result, 'data', result)
        timestamp = getattr(result, 'timestamp', None) or datetime.now().timestamp()

        # Infer success from explicit flag or metadata if present
        if hasattr(result, 'success'):
            success = bool(getattr(result, 'success'))
            error_message = getattr(result, 'error_message', None)
        else:
            success = True
            error_message = None

        metadata = getattr(result, 'metadata', {}) or {}
        error_flag = bool(metadata.get('error'))
        if error_flag:
            success = False
            error_message = error_message or metadata.get('error_message')
        exec_ms = metadata.get('execution_time_ms')

        return PreviousNodeOutput(
            node_id=node_id,
            node_type=node_type,
            data=data,
            timestamp=timestamp,
            connection_type="direct",
            success=success,
            error_message=error_message,
            execution_time_ms=exec_ms,
        )
