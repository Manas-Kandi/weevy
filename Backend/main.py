"""
Main FastAPI backend server for Weev AI Agent Workflow Platform
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
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

# DB and routers
from database.connection import init_db, close_db, db_health, AsyncSessionLocal
from database.models import Project, WorkflowNode, NodeConnection, WorkflowExecution
from api.projects import router as projects_router
from api.nodes import router as nodes_router
from api.executions import router as executions_router
from api.billing import router as billing_router
from llm.manager import LLMManager
from llm.providers import OpenAIProvider, AnthropicProvider, GoogleProvider, NvidiaProvider

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

@app.get("/health/db")
async def health_check_db():
    ok = await db_health()
    return {"database": "ok" if ok else "down"}

# Routers
app.include_router(projects_router)
app.include_router(nodes_router)
app.include_router(executions_router)
app.include_router(billing_router)

# Lifespan events
@app.on_event("startup")
async def on_startup():
    await init_db()
    # Initialize multi-provider LLM manager and attach to app state
    providers = [
        NvidiaProvider(),
        OpenAIProvider(),
        AnthropicProvider(),
        GoogleProvider(),
    ]
    app.state.llm_manager = LLMManager(providers)

@app.on_event("shutdown")
async def on_shutdown():
    await close_db()

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
    """Handle workflow execution with streaming updates. Supports either inline payload
    (nodes + connections) or a DB-backed run via project_id. Optionally accepts execution_id.
    """
    session = None
    try:
        execution_id: Optional[str] = workflow_data.get("execution_id")
        project_id: Optional[str] = workflow_data.get("project_id")
        workflow_id = workflow_data.get("workflow_id") or execution_id or project_id or "unknown"

        nodes = workflow_data.get("nodes")
        connections = workflow_data.get("connections")

        # If project_id is provided, build workflow from DB
        if project_id and (nodes is None or connections is None):
            session = AsyncSessionLocal()
            proj = await session.get(Project, project_id)
            if not proj:
                raise ValueError("Project not found")
            # Ensure an execution record exists
            if not execution_id:
                exe = WorkflowExecution(project_id=proj.id, status="running")
                session.add(exe)
                await session.commit()
                await session.refresh(exe)
                execution_id = str(exe.id)
            # Fetch nodes and connections
            node_rows = (await session.execute(
                __import__('sqlalchemy').select(WorkflowNode).where(WorkflowNode.project_id == proj.id)
            )).scalars().all()
            conn_rows = (await session.execute(
                __import__('sqlalchemy').select(NodeConnection).where(NodeConnection.project_id == proj.id)
            )).scalars().all()
            nodes = [
                {
                    "node_id": str(n.id),
                    "node_type": n.node_type,
                    "system_rules": f"Execute {n.node_type} node",
                    "user_configuration": n.configuration or {},
                }
                for n in node_rows
            ]
            connections = [
                {"from": str(c.from_node_id), "to": str(c.to_node_id)} for c in conn_rows
            ]

        await manager.send_personal_message(json.dumps({
            "type": "execution_started",
            "workflow_id": workflow_id,
            "execution_id": execution_id,
        }), websocket)

        # Execute
        workflow_payload = {"workflow_id": workflow_id, "nodes": nodes or [], "connections": connections or []}
        executor = WorkflowExecutor(workflow_payload, manager, execution_id=execution_id, db_session=session)
        await executor.execute()

    except Exception as e:
        await manager.send_personal_message(json.dumps({
            "type": "execution_error",
            "error": str(e),
            "execution_id": workflow_data.get("execution_id"),
        }), websocket)
    finally:
        if session is not None:
            await session.close()

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
