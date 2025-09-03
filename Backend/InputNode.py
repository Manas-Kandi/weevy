"""
Input Node Module

Handles user input collection and preprocessing for the workflow system.
"""

from typing import Dict, Any, List
from Backend.GeneralNodeLogic import GeneralNodeLogic, NodeInputs, NodeOutput, PreviousNodeOutput, WorkflowMemory

class InputNode(GeneralNodeLogic):
    """
    Input Node - Collects and preprocesses user input for the workflow.
    """
    
    def __init__(self, node_id: str, name: str):
        super().__init__()
        self.node_id = node_id
        self.name = name
        self.input_schema = {
            "type": "object",
            "properties": {
                "input_text": {"type": "string", "description": "User's input text"},
                "input_type": {"type": "string", "enum": ["text", "file", "api", "database"], "default": "text"},
                "metadata": {"type": "object", "description": "Additional input metadata"}
            },
            "required": ["input_text"]
        }
    
    async def execute(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory
    ) -> NodeOutput:
        """
        Process user input and prepare it for downstream nodes.
        """
        return NodeOutput(
            node_id=self.node_id,
            node_type="InputNode",
            data=user_configuration,
            timestamp=__import__('datetime').datetime.now().timestamp(),
            metadata={"status": "success"},
            success=True
        )
    
    def _process_input(self, text: str, input_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process input based on type"""
        if input_type == "text":
            return {
                "raw_text": text,
                "word_count": len(text.split()),
                "char_count": len(text),
                "processed": True
            }
        elif input_type == "file":
            return {
                "file_path": text,
                "file_type": metadata.get("file_type", "unknown"),
                "size": metadata.get("size", 0),
                "processed": True
            }
        else:
            return {
                "raw_input": text,
                "input_type": input_type,
                "metadata": metadata,
                "processed": True
            }
