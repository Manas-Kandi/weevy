"""
Main FastAPI backend server for Weev AI Agent Workflow Platform
"""

import os
import json
import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import node classes
from BrainNode import BrainNode
from InputNode import InputNode
from OutputNode import OutputNode
from KnowledgeBaseNode import KnowledgeBaseNode

# Load environment variables
load_dotenv()

app = FastAPI(title="Weev Backend", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            pass

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Request/Response models
class WorkflowRequest(BaseModel):
    workflow_id: str
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]

class NodeExecutionRequest(BaseModel):
    node_id: str
    node_type: str
    system_rules: str
    user_configuration: Dict[str, Any]
    previous_data: List[Dict[str, Any]] = []

# Node registry
NODE_CLASSES = {
    "BrainNode": BrainNode,
    "InputNode": InputNode,
    "OutputNode": OutputNode,
    "KnowledgeBaseNode": KnowledgeBaseNode
}

@app.get("/")
async def root():
    return {"message": "Weev Backend API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": asyncio.get_event_loop().time()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "execute_workflow":
                await handle_workflow_execution(message.get("data", {}), websocket)
            elif message.get("type") == "ping":
                await manager.send_personal_message(json.dumps({"type": "pong"}), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/canvas")
async def canvas_websocket(websocket: WebSocket):
    """Dedicated WebSocket endpoint for canvas operations"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "execute_workflow":
                await handle_workflow_execution(message.get("data", {}), websocket)
            elif message.get("type") == "node_status":
                await handle_node_status(message.get("data", {}), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def handle_workflow_execution(workflow_data: Dict[str, Any], websocket: WebSocket):
    """Handle workflow execution with streaming updates"""
    try:
        workflow_id = workflow_data.get("workflow_id", "unknown")
        nodes = workflow_data.get("nodes", [])
        connections = workflow_data.get("connections", [])
        
        # Send execution started
        await manager.send_personal_message(json.dumps({
            "type": "execution_started",
            "workflow_id": workflow_id
        }), websocket)
        
        # Execute nodes in order
        previous_outputs = []
        
        for i, node_data in enumerate(nodes):
            node_id = node_data.get("node_id")
            node_type = node_data.get("node_type")
            
            # Send node execution started
            await manager.send_personal_message(json.dumps({
                "type": "execution_update",
                "node_id": node_id,
                "content": f"Executing {node_type}..."
            }), websocket)
            
            try:
                # Create node instance
                if node_type not in NODE_CLASSES:
                    raise ValueError(f"Unknown node type: {node_type}")
                
                node_class = NODE_CLASSES[node_type]
                node_instance = node_class(node_id, f"{node_type}_{node_id}")
                
                # Prepare inputs
                user_config = node_data.get("user_configuration", {})
                system_rules = node_data.get("system_rules", "")
                
                # Execute node
                from GeneralNodeLogic import NodeInputs, WorkflowMemory
                
                workflow_memory = WorkflowMemory(workflow_id=workflow_id)
                
                inputs = NodeInputs(
                    system_rules=system_rules,
                    user_configuration=user_config,
                    previous_node_data=previous_outputs,
                    workflow_memory=workflow_memory
                )
                
                # Execute with streaming
                output = await node_instance.execute_node(inputs)
                
                # Send node result
                await manager.send_personal_message(json.dumps({
                    "type": "node_result",
                    "node_id": node_id,
                    "result": output.data,
                    "metadata": output.metadata
                }), websocket)
                
                previous_outputs.append({
                    "node_id": node_id,
                    "node_type": node_type,
                    "data": output.data,
                    "success": True
                })
                
            except Exception as e:
                await manager.send_personal_message(json.dumps({
                    "type": "execution_error",
                    "node_id": node_id,
                    "error": str(e)
                }), websocket)
                
                previous_outputs.append({
                    "node_id": node_id,
                    "node_type": node_type,
                    "data": str(e),
                    "success": False,
                    "error_message": str(e)
                })
        
        # Send execution completed
        await manager.send_personal_message(json.dumps({
            "type": "execution_complete",
            "workflow_id": workflow_id,
            "results": previous_outputs
        }), websocket)
        
    except Exception as e:
        await manager.send_personal_message(json.dumps({
            "type": "execution_error",
            "error": str(e)
        }), websocket)

async def handle_node_status(data: Dict[str, Any], websocket: WebSocket):
    """Handle node status requests"""
    await manager.send_personal_message(json.dumps({
        "type": "node_status_response",
        "data": {"status": "ready", "connected_nodes": len(NODE_CLASSES)}
    }), websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
