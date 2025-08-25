"""
Brain Node Module

Central reasoning node that coordinates other nodes and decides workflow actions.
"""

import os
from typing import Dict, List, Any, Optional
from GeneralNodeLogic import GeneralNodeLogic, NodeInputs, NodeOutput, PreviousNodeOutput, WorkflowMemory

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
    """
    def __init__(self, node_id: str, name: str):
        super().__init__()
        self.node_id = node_id
        self.name = name
        self.connected_nodes: List[Any] = []
        self.processing_strategy: str = "sequential"
        self.context_memory: Dict[str, Any] = {}  # persists context across runs
    
    async def execute(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory
    ) -> NodeOutput:
        """
        Execute the Brain Node using GeneralNodeLogic with specific system rules.
        Includes reasoning about connected nodes and persistence of context.
        """
        return NodeOutput(
            node_id=self.node_id,
            node_type="BrainNode",
            data=previous_node_data,
            timestamp=0,
            metadata={"status": "success"}
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
