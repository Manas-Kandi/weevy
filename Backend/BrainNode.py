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
        # Build awareness of connected tools
        available_tools = [
            {
                "id": node.node_id,
                "name": node.name,
                "type": type(node).__name__,
                "capabilities": getattr(node, "capabilities", "unknown")
            }
            for node in self.connected_nodes
        ]
        
        # Merge prior context into inputs
        combined_context = {
            "previous_data": [p.to_dict() if hasattr(p, 'to_dict') else str(p) for p in previous_node_data],
            "context_memory": self.context_memory,
            "available_tools": available_tools
        }
        
        # Update user configuration with combined context
        enhanced_config = {**user_configuration, "combined_context": combined_context}
        
        inputs = NodeInputs(
            system_rules=BRAIN_NODE_SYSTEM_RULES,
            user_configuration=enhanced_config,
            previous_node_data=previous_node_data,
            workflow_memory=workflow_memory,
            execution_context=combined_context
        )
        
        output: NodeOutput = await self.execute_node(inputs)
        
        # Persist context memory for continuity
        if output.memory_updates:
            self.context_memory.update(output.memory_updates)
        
        return output
    
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
