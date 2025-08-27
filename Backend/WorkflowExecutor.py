
import asyncio
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from BrainNode import BrainNode
from InputNode import InputNode
from OutputNode import OutputNode
from KnowledgeBaseNode import KnowledgeBaseNode
from ToolNode import ToolNode
from GeneralNodeLogic import NodeInputs, WorkflowMemory, PreviousNodeOutput
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
    def __init__(self, workflow: Dict[str, Any], manager, execution_id: Optional[str] = None, db_session: Optional[AsyncSession] = None):
        self.workflow = workflow
        self.manager = manager
        self.execution_id = execution_id
        self.db_session = db_session
        self.node_results: Dict[str, PreviousNodeOutput] = {}
        self.workflow_memory = WorkflowMemory(workflow_id=self.workflow.get("workflow_id"))

    async def execute(self):
        nodes = self.workflow.get('nodes', [])
        connections = self.workflow.get('connections', [])

        node_map = {node['node_id']: node for node in nodes}
        adj: Dict[str, List[str]] = {node['node_id']: [] for node in nodes}
        in_degree: Dict[str, int] = {node['node_id']: 0 for node in nodes}

        for conn in connections:
            adj[conn['from']].append(conn['to'])
            in_degree[conn['to']] += 1

        queue: List[str] = [node_id for node_id, degree in in_degree.items() if degree == 0]

        import json
        await self.manager.broadcast(json.dumps({
            "type": "workflow_started",
            "workflow_id": self.workflow.get('workflow_id'),
            "execution_id": self.execution_id,
            "message": "Workflow execution started"
        }))

        while queue:
            node_id = queue.pop(0)
            node_data = node_map[node_id]

            input_data = self.get_input_for_node(node_id, connections)

            try:
                node_type = node_data.get("node_type")
                if node_type not in NODE_CLASSES:
                    raise ValueError(f"Unknown node type: {node_type}")

                node_class = NODE_CLASSES[node_type]
                node_instance = node_class(node_id, f"{node_type}_{node_id}")

                inputs = NodeInputs(
                    system_rules=node_data.get("system_rules", ""),
                    user_configuration=node_data.get("user_configuration", {}),
                    previous_node_data=input_data,
                    workflow_memory=self.workflow_memory,
                )

                result = await node_instance.execute(
                    inputs.user_configuration,
                    inputs.previous_node_data,
                    inputs.workflow_memory,
                )

                # Convert NodeOutput -> PreviousNodeOutput for downstream nodes
                prev_out = self._to_previous_output(node_id, node_type, result)
                self.node_results[node_id] = prev_out

                await self.manager.broadcast(json.dumps({
                    "type": "node_executed",
                    "node_id": node_id,
                    "execution_id": self.execution_id,
                    "result": str(prev_out.data),
                    "message": "Node executed successfully"
                }))

                for neighbor_id in adj.get(node_id, []):
                    in_degree[neighbor_id] -= 1
                    if in_degree[neighbor_id] == 0:
                        queue.append(neighbor_id)

            except Exception as e:
                await self.manager.broadcast(json.dumps({
                    "type": "execution_error",
                    "node_id": node_id,
                    "execution_id": self.execution_id,
                    "error": str(e),
                    "message": "Error executing node"
                }))
                # persist failure
                await self._persist_status(status="failed", error=str(e))
                return

        await self.manager.broadcast(json.dumps({
            "type": "workflow_finished",
            "workflow_id": self.workflow.get('workflow_id'),
            "execution_id": self.execution_id,
            "message": "Workflow execution finished"
        }))
        # persist success
        summary = {nid: getattr(out, 'data', None) for nid, out in self.node_results.items()}
        await self._persist_status(status="completed", results=summary)

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
