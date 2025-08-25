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
from WorkflowExecutor import WorkflowExecutor

# Load environment variables
load_dotenv()

app = FastAPI(title="Weev Backend", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ],
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
        
        await manager.send_personal_message(json.dumps({
            "type": "execution_started",
            "workflow_id": workflow_id
        }), websocket)

        executor = WorkflowExecutor(workflow_data, manager)
        await executor.execute()

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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
