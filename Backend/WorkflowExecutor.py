
import asyncio
from typing import Any, Dict, List

from BrainNode import BrainNode
from InputNode import InputNode
from OutputNode import OutputNode
from KnowledgeBaseNode import KnowledgeBaseNode
from GeneralNodeLogic import NodeInputs, WorkflowMemory, PreviousNodeOutput

NODE_CLASSES = {
    "brain": BrainNode,
    "input": InputNode,
    "output": OutputNode,
    "knowledge": KnowledgeBaseNode,
}

class WorkflowExecutor:
    def __init__(self, workflow: Dict[str, Any], manager):
        self.workflow = workflow
        self.manager = manager
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
        await self.manager.broadcast(json.dumps({"type": "workflow_started", "workflow_id": self.workflow.get('workflow_id'), "message": "Workflow execution started"}))

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

                result = await node_instance.execute(inputs.user_configuration, inputs.previous_node_data, inputs.workflow_memory)
                self.node_results[node_id] = result

                await self.manager.broadcast(json.dumps({"type": "node_executed", "node_id": node_id, "result": str(result.data), "message": "Node executed successfully"}))

                for neighbor_id in adj.get(node_id, []):
                    in_degree[neighbor_id] -= 1
                    if in_degree[neighbor_id] == 0:
                        queue.append(neighbor_id)

            except Exception as e:
                await self.manager.broadcast(json.dumps({"type": "execution_error", "node_id": node_id, "error": str(e), "message": "Error executing node"}))
                return

        await self.manager.broadcast(json.dumps({"type": "workflow_finished", "workflow_id": self.workflow.get('workflow_id'), "message": "Workflow execution finished"}))

    def get_input_for_node(self, node_id: str, connections: List[Dict[str, str]]) -> List[PreviousNodeOutput]:
        input_data: List[PreviousNodeOutput] = []
        parent_connections = [conn for conn in connections if conn['to'] == node_id]

        for conn in parent_connections:
            parent_node_id = conn['from']
            if parent_node_id in self.node_results:
                input_data.append(self.node_results[parent_node_id])

        return input_data

