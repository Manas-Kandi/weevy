"""
Output Node Module

Handles final output formatting and delivery for the workflow system.
"""

from typing import Dict, Any, List
from GeneralNodeLogic import GeneralNodeLogic, NodeInputs, NodeOutput, PreviousNodeOutput, WorkflowMemory

class OutputNode(GeneralNodeLogic):
    """
    Output Node - Formats and delivers final results to the user.
    """
    
    def __init__(self, node_id: str, name: str):
        super().__init__()
        self.node_id = node_id
        self.name = name
        self.output_format = "json"
        self.delivery_method = "websocket"
    
    async def execute(
        self,
        user_configuration: Dict[str, Any],
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory
    ) -> NodeOutput:
        """
        Format and deliver the final output based on user preferences.
        """
        return NodeOutput(
            node_id=self.node_id,
            node_type="OutputNode",
            data=previous_node_data,
            timestamp=__import__('datetime').datetime.now().timestamp(),
            metadata={"status": "success"},
            success=True
        )
    
    def _collect_final_data(self, previous_data: List[PreviousNodeOutput]) -> Dict[str, Any]:
        """Collect and merge data from all previous nodes"""
        final_data = {
            "workflow_results": [],
            "summary": {},
            "metadata": {}
        }
        
        for node_output in previous_data:
            final_data["workflow_results"].append({
                "node_id": node_output.node_id,
                "node_type": node_output.node_type,
                "data": node_output.data,
                "success": node_output.success,
                "timestamp": node_output.timestamp
            })
        
        # Create summary
        successful_nodes = [n for n in previous_data if n.success]
        final_data["summary"] = {
            "total_nodes": len(previous_data),
            "successful_nodes": len(successful_nodes),
            "failed_nodes": len(previous_data) - len(successful_nodes)
        }
        
        return final_data
    
    def _format_output(self, data: Dict[str, Any], format_type: str) -> Any:
        """Format output based on specified type"""
        if format_type == "json":
            return data
        elif format_type == "text":
            return self._format_as_text(data)
        elif format_type == "markdown":
            return self._format_as_markdown(data)
        else:
            return data
    
    def _format_as_text(self, data: Dict[str, Any]) -> str:
        """Format data as human-readable text"""
        text_output = []
        text_output.append("=== Workflow Results ===")
        
        for result in data.get("workflow_results", []):
            text_output.append(f"\n{result['node_type']} ({result['node_id']}):")
            text_output.append(str(result['data']))
        
        summary = data.get("summary", {})
        text_output.append(f"\n=== Summary ===")
        text_output.append(f"Total nodes: {summary.get('total_nodes', 0)}")
        text_output.append(f"Successful: {summary.get('successful_nodes', 0)}")
        text_output.append(f"Failed: {summary.get('failed_nodes', 0)}")
        
        return "\n".join(text_output)
    
    def _format_as_markdown(self, data: Dict[str, Any]) -> str:
        """Format data as markdown"""
        md_output = ["# Workflow Results\n"]
        
        for result in data.get("workflow_results", []):
            md_output.append(f"## {result['node_type']} - {result['node_id']}")
            md_output.append(f"```\n{result['data']}\n```\n")
        
        summary = data.get("summary", {})
        md_output.append("## Summary")
        md_output.append(f"- **Total nodes:** {summary.get('total_nodes', 0)}")
        md_output.append(f"- **Successful:** {summary.get('successful_nodes', 0)}")
        md_output.append(f"- **Failed:** {summary.get('failed_nodes', 0)}")
        
        return "\n".join(md_output)
    
    def _prepare_delivery(self, formatted_output: Any, delivery_method: str) -> Dict[str, Any]:
        """Prepare output for delivery"""
        return {
            "formatted_output": formatted_output,
            "delivery_method": delivery_method,
            "ready_for_delivery": True
        }
