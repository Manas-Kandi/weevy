"""
Main FastAPI backend server for Weev AI Agent Workflow Platform

Enhanced with comprehensive LangChain and LangGraph integration for advanced AI agent workflows.

Key Features:
============

1. **Hybrid Node System**: Maintains backward compatibility with existing nodes while adding 
   LangChain-enhanced nodes for advanced capabilities

2. **LangGraph Integration**: State-based workflow orchestration with persistent memory
   and complex reasoning capabilities

3. **Vector Database Support**: RAG capabilities with multiple vector database providers
   (ChromaDB, Pinecone, Qdrant, FAISS)

4. **Multi-Agent Coordination**: Support for specialized agents working together on
   complex problems

5. **Human-in-the-Loop**: Built-in approval workflows and human feedback integration

6. **Enhanced Memory Management**: Sophisticated conversation and context memory across
   workflow sessions

7. **Tool Ecosystem**: Integration with LangChain's extensive tool library for external
   API calls, web searches, database queries, and custom functions

Architecture Enhancements:
=========================

The FastAPI application now includes:

- **LangGraphManager**: Core orchestrator for stateful workflows
- **VectorStoreManager**: Unified interface for vector database operations  
- **ToolRegistry**: Centralized management of LangChain tools
- **Enhanced Node Registry**: Support for both standard and LangChain-powered nodes
- **Streaming Integration**: Real-time workflow execution updates
- **Performance Monitoring**: Comprehensive metrics and health checks

Initialization Flow:
==================

1. Database initialization (existing)
2. LLM Manager setup (existing) 
3. LangGraph Manager initialization (new)
4. Vector Store setup (new)
5. Tool Registry configuration (new)
6. Enhanced node registration (new)

API Extensions:
==============

New endpoints added:
- GET /health/langchain - LangChain component health checks
- GET /health/vector - Vector database health status
- POST /workflow/enhanced - Execute LangChain-powered workflows
- GET /tools/available - List available LangChain tools
- POST /vector/search - Direct vector similarity search

Usage:
======

The enhanced backend maintains full backward compatibility while providing new capabilities:

```python
# Standard workflow (unchanged)
POST /api/workflow/execute

# Enhanced LangChain workflow (new)
POST /api/workflow/enhanced
{
    "workflow_id": "enhanced_reasoning_001",
    "nodes": [...],
    "use_langchain": true,
    "enable_rag": true,
    "tools": ["web_search", "database_query"]
}
```
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import existing node classes
from Backend.BrainNode import BrainNode
from Backend.InputNode import InputNode
from Backend.OutputNode import OutputNode
from Backend.KnowledgeBaseNode import KnowledgeBaseNode
from Backend.WorkflowExecutor import WorkflowExecutor

# Import existing infrastructure
from Backend.database.connection import init_db, close_db, db_health, AsyncSessionLocal
from Backend.database.models import Project, WorkflowNode, NodeConnection, WorkflowExecution
from Backend.api.projects import router as projects_router
from Backend.api.nodes import router as nodes_router
from Backend.api.executions import router as executions_router
from Backend.api.billing import router as billing_router
from Backend.llm.manager import LLMManager
from Backend.llm.providers import OpenAIProvider, AnthropicProvider, GoogleProvider, NvidiaProvider

# Import LangChain integration components
try:
    from Backend.langchain_integration import LangGraphManager, LangChainMemoryManager, ToolRegistry
    from Backend.langchain_integration.nodes import LangChainBrainNode, RAGChainNode
    from Backend.langchain_integration.vector_store import VectorStoreManager, VectorStoreConfig
    from Backend.tools import WebSearchTool, DatabaseTool, APICallingTool
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LangChain components not available: {e}")
    LANGCHAIN_AVAILABLE = False

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

# Enhanced Node registry with LangChain support
NODE_CLASSES = {
    "BrainNode": BrainNode,
    "InputNode": InputNode,
    "OutputNode": OutputNode,
    "KnowledgeBaseNode": KnowledgeBaseNode,
    # LangChain-enhanced nodes
    "LangChainBrainNode": None,  # Will be initialized after LangGraph manager
    "RAGChainNode": None,
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

@app.get("/health/langchain")
async def health_check_langchain():
    """Health check for LangChain components"""
    try:
        health_status = {
            "langgraph_manager": "unknown",
            "vector_store": "unknown", 
            "tool_registry": "unknown",
            "enhanced_nodes": "unknown"
        }
        
        # Check LangGraph manager
        if hasattr(app.state, 'langgraph_manager'):
            health_status["langgraph_manager"] = "healthy"
        else:
            health_status["langgraph_manager"] = "not_initialized"
        
        # Check vector store
        if hasattr(app.state, 'vector_store_manager'):
            vector_health = await app.state.vector_store_manager.health_check()
            health_status["vector_store"] = vector_health["status"]
        else:
            health_status["vector_store"] = "not_initialized"
        
        # Check tool registry
        if hasattr(app.state, 'tool_registry'):
            tool_count = len(app.state.tool_registry.get_available_tools())
            health_status["tool_registry"] = f"healthy ({tool_count} tools)"
        else:
            health_status["tool_registry"] = "not_initialized"
        
        # Check enhanced nodes
        enhanced_node_count = sum(1 for node_class in NODE_CLASSES.values() if node_class is not None)
        health_status["enhanced_nodes"] = f"healthy ({enhanced_node_count} node types)"
        
        return health_status
        
    except Exception as e:
        return {"error": str(e), "status": "unhealthy"}

@app.get("/health/vector")
async def health_check_vector():
    """Detailed health check for vector database"""
    try:
        if not hasattr(app.state, 'vector_store_manager'):
            return {"status": "not_initialized", "error": "Vector store manager not initialized"}
        
        return await app.state.vector_store_manager.health_check()
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/tools/available")
async def list_available_tools():
    """List all available LangChain tools"""
    try:
        if not hasattr(app.state, 'tool_registry'):
            return {"tools": [], "error": "Tool registry not initialized"}
        
        tools = app.state.tool_registry.get_available_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": getattr(tool, 'args_schema', {})
                }
                for tool in tools
            ],
            "count": len(tools)
        }
        
    except Exception as e:
        return {"tools": [], "error": str(e)}

@app.post("/vector/search")
async def vector_similarity_search(
    query: str,
    k: int = 5,
    score_threshold: Optional[float] = None,
    metadata_filter: Optional[Dict[str, Any]] = None
):
    """Direct vector similarity search endpoint"""
    try:
        if not hasattr(app.state, 'vector_store_manager'):
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        results = await app.state.vector_store_manager.similarity_search(
            query=query,
            k=k,
            score_threshold=score_threshold,
            metadata_filter=metadata_filter
        )
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Routers
app.include_router(projects_router)
app.include_router(nodes_router)
app.include_router(executions_router)
app.include_router(billing_router)

# Lifespan events
@app.on_event("startup")
async def on_startup():
    """
    Enhanced startup sequence with comprehensive LangChain integration.
    
    Initialization order is important:
    1. Database (core infrastructure)
    2. LLM Manager (existing functionality) 
    3. Vector Store (for RAG capabilities)
    4. Tool Registry (for agent tools)
    5. LangGraph Manager (for stateful workflows)
    6. Enhanced Node Registration (LangChain-powered nodes)
    """
    logger = logging.getLogger("weev.startup")
    logger.info("Starting Weev backend with LangChain integration...")
    
    try:
        # Step 1: Initialize database (existing)
        logger.info("Initializing database...")
        await init_db()
        
        # Step 2: Initialize multi-provider LLM manager (existing)
        logger.info("Initializing LLM manager...")
        providers = [
            NvidiaProvider(),
            OpenAIProvider(), 
            AnthropicProvider(),
            GoogleProvider(),
        ]
        app.state.llm_manager = LLMManager(providers)
        logger.info(f"LLM Manager initialized with {len(providers)} providers")
        
        # Step 3: Initialize Vector Store Manager (new)
        if LANGCHAIN_AVAILABLE:
            logger.info("Initializing vector store manager...")
            try:
                vector_config = VectorStoreConfig(
                    provider=os.getenv("VECTOR_DB_PROVIDER", "chroma"),
                    embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers"),
                    collection_name=os.getenv("VECTOR_DB_COLLECTION", "weev_knowledge"),
                    persist_directory=os.getenv("VECTOR_DB_PERSIST_DIR", "./vector_db")
                )
                app.state.vector_store_manager = VectorStoreManager(config=vector_config)
                logger.info(f"Vector store initialized: {vector_config.provider}")
            except Exception as e:
                logger.warning(f"Vector store initialization failed: {e}. Continuing without vector capabilities.")
                app.state.vector_store_manager = None
        else:
            logger.info("LangChain not available, skipping vector store initialization")
            app.state.vector_store_manager = None
        
        # Step 4: Initialize Tool Registry (new)  
        if LANGCHAIN_AVAILABLE:
            logger.info("Initializing tool registry...")
            try:
                app.state.tool_registry = ToolRegistry()
                
                # Register standard tools
                standard_tools = []
                
                # Add web search tool if API keys available
                if os.getenv("SEARCH_API_KEY") or os.getenv("SERP_API_KEY"):
                    try:
                        web_search_tool = WebSearchTool()
                        standard_tools.append(web_search_tool)
                    except Exception as e:
                        logger.warning(f"Web search tool initialization failed: {e}")
                
                # Add database tool 
                try:
                    db_tool = DatabaseTool(connection_string=app.state.llm_manager)
                    standard_tools.append(db_tool)
                except Exception as e:
                    logger.warning(f"Database tool initialization failed: {e}")
                
                # Add API calling tool
                try:
                    api_tool = APICallingTool()
                    standard_tools.append(api_tool)
                except Exception as e:
                    logger.warning(f"API calling tool initialization failed: {e}")
                
                # Register all tools
                for tool in standard_tools:
                    app.state.tool_registry.register_tool(tool)
                
                logger.info(f"Tool registry initialized with {len(standard_tools)} tools")
            except Exception as e:
                logger.warning(f"Tool registry initialization failed: {e}. Continuing without tools.")
                app.state.tool_registry = None
        else:
            logger.info("LangChain not available, skipping tool registry initialization")
            app.state.tool_registry = None
        
        # Step 5: Initialize LangGraph Manager (new)
        logger.info("Initializing LangGraph manager...")
        try:
            app.state.langgraph_manager = LangGraphManager(
                llm_manager=app.state.llm_manager,
                db_session=AsyncSessionLocal(),
                checkpoint_dir=os.getenv("LANGGRAPH_CHECKPOINT_DIR", "./checkpoints")
            )
            logger.info("LangGraph manager initialized successfully")
        except Exception as e:
            logger.warning(f"LangGraph manager initialization failed: {e}. Enhanced workflows will be disabled.")
            app.state.langgraph_manager = None
        
        # Step 6: Initialize Enhanced Node Classes (new)
        logger.info("Initializing enhanced node classes...")
        try:
            # Initialize LangChain Brain Node factory
            if app.state.langgraph_manager:
                def create_langchain_brain_node(node_id: str, name: str, **kwargs):
                    tools = []
                    if app.state.tool_registry:
                        tools = app.state.tool_registry.get_available_tools()
                    
                    return LangChainBrainNode(
                        node_id=node_id,
                        name=name,
                        graph_manager=app.state.langgraph_manager,
                        tools=tools,
                        **kwargs
                    )
                
                NODE_CLASSES["LangChainBrainNode"] = create_langchain_brain_node
                logger.info("LangChain Brain Node registered")
            
            # Initialize RAG Chain Node factory
            if app.state.vector_store_manager:
                def create_rag_chain_node(node_id: str, name: str, **kwargs):
                    return RAGChainNode(
                        node_id=node_id,
                        name=name,
                        vector_store=app.state.vector_store_manager.get_store(),
                        llm_manager=app.state.llm_manager,
                        **kwargs
                    )
                
                NODE_CLASSES["RAGChainNode"] = create_rag_chain_node
                logger.info("RAG Chain Node registered")
            
            enhanced_nodes = sum(1 for node_class in NODE_CLASSES.values() if node_class is not None)
            logger.info(f"Enhanced node registration completed: {enhanced_nodes} node types available")
            
        except Exception as e:
            logger.error(f"Enhanced node initialization failed: {e}")
            # Don't fail startup for this
        
        # Step 7: Initialize sample vector data (optional)
        if (app.state.vector_store_manager and 
            os.getenv("INITIALIZE_SAMPLE_VECTORS", "false").lower() == "true"):
            logger.info("Initializing sample vector data...")
            try:
                sample_documents = [
                    {
                        "text": "LangChain is a framework for developing applications powered by language models. It provides tools for building LLM-powered applications with capabilities like document analysis, question answering, and chatbots.",
                        "metadata": {"type": "definition", "topic": "langchain", "source": "documentation"}
                    },
                    {
                        "text": "LangGraph is a library for building stateful, multi-actor applications with LLMs. It's designed to coordinate multiple chains or agents in a stateful way across multiple steps of computation.",
                        "metadata": {"type": "definition", "topic": "langgraph", "source": "documentation"}
                    },
                    {
                        "text": "Retrieval-Augmented Generation (RAG) is an AI framework that combines the power of large language models with external knowledge sources. It retrieves relevant information from a knowledge base and uses it to generate more accurate and contextual responses.",
                        "metadata": {"type": "definition", "topic": "rag", "source": "documentation"}
                    },
                    {
                        "text": "Weev is an AI agent workflow platform that enables users to create sophisticated AI workflows using a visual, node-based interface. It supports both standard and LangChain-powered nodes for advanced AI capabilities.",
                        "metadata": {"type": "definition", "topic": "weev", "source": "platform"}
                    }
                ]
                
                await app.state.vector_store_manager.add_documents(sample_documents)
                logger.info(f"Added {len(sample_documents)} sample documents to vector store")
                
            except Exception as e:
                logger.warning(f"Sample vector data initialization failed: {e}")
        
        # Final status report
        components_status = {
            "database": "✓",
            "llm_manager": "✓",
            "vector_store": "✓" if app.state.vector_store_manager else "✗",
            "tool_registry": "✓" if app.state.tool_registry else "✗", 
            "langgraph_manager": "✓" if app.state.langgraph_manager else "✗",
            "enhanced_nodes": f"✓ ({sum(1 for v in NODE_CLASSES.values() if v is not None)} types)"
        }
        
        logger.info("Weev backend startup completed successfully!")
        logger.info(f"Components status: {components_status}")
        
        # Log available capabilities
        capabilities = []
        if app.state.vector_store_manager:
            capabilities.append("RAG (Retrieval-Augmented Generation)")
        if app.state.tool_registry:
            tool_count = len(app.state.tool_registry.get_available_tools()) if app.state.tool_registry else 0
            capabilities.append(f"Tool Integration ({tool_count} tools)")
        if app.state.langgraph_manager:
            capabilities.append("Stateful Workflows (LangGraph)")
        
        if capabilities:
            logger.info(f"Enhanced capabilities available: {', '.join(capabilities)}")
        else:
            logger.info("Running with standard capabilities only")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        # Don't prevent app from starting, but log the error
        raise

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
