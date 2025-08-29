# LangChain Integration Guide for Weev Platform

## Overview

This guide provides comprehensive documentation for integrating and using LangChain capabilities within the Weev AI Agent Workflow Platform. The integration adds advanced AI agent functionality including state-based reasoning, retrieval-augmented generation (RAG), tool integration, and multi-agent coordination.

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [Node Types](#node-types)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)
7. [API Endpoints](#api-endpoints)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Performance Optimization](#performance-optimization)

## Installation and Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Redis (optional, for caching)
- Vector database (ChromaDB by default, or Pinecone/Qdrant for production)

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Core LangChain Configuration
VECTOR_DB_PROVIDER=chroma              # chroma, pinecone, qdrant, faiss
EMBEDDING_MODEL=sentence-transformers   # openai, sentence-transformers
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2  # Specific embedding model
VECTOR_DB_COLLECTION=weev_knowledge     # Collection name
VECTOR_DB_PERSIST_DIR=./vector_db       # Storage directory

# Vector Database Specific
PINECONE_API_KEY=your_pinecone_key     # If using Pinecone
PINECONE_ENV=us-west1-gcp              # Pinecone environment
QDRANT_URL=http://localhost:6333       # If using Qdrant
QDRANT_API_KEY=your_qdrant_key         # Qdrant API key

# Tool API Keys (Optional)
GOOGLE_API_KEY=your_google_key         # For Google search
GOOGLE_CSE_ID=your_cse_id              # Google Custom Search
BING_SEARCH_API_KEY=your_bing_key      # Bing Search API
SERP_API_KEY=your_serp_key             # SerpAPI key
TAVILY_API_KEY=your_tavily_key         # Tavily search

# LangGraph Configuration
LANGGRAPH_CHECKPOINT_DIR=./checkpoints  # Checkpoint storage
INITIALIZE_SAMPLE_VECTORS=false         # Load sample data on startup
```

### Installation Steps

1. **Install Dependencies**
   ```bash
   cd Backend
   pip install -r requirements.txt
   ```

2. **Setup Vector Database**
   ```bash
   # For ChromaDB (default - no additional setup required)
   
   # For Pinecone
   pip install pinecone-client
   
   # For Qdrant
   docker run -p 6333:6333 qdrant/qdrant
   ```

3. **Initialize Database Schema**
   ```bash
   # Run Alembic migrations if needed
   alembic upgrade head
   ```

4. **Start the Server**
   ```bash
   python main.py
   ```

## Architecture Overview

The LangChain integration follows a modular architecture that extends Weev's existing capabilities:

```
Weev Platform
├── Core System (Existing)
│   ├── BrainNode
│   ├── InputNode
│   ├── OutputNode
│   └── KnowledgeBaseNode
│
└── LangChain Integration (New)
    ├── LangGraphManager
    ├── VectorStoreManager
    ├── ToolRegistry
    ├── MemoryManager
    └── Enhanced Nodes
        ├── LangChainBrainNode
        ├── RAGChainNode
        ├── AgentExecutorNode
        └── ToolCallingNode
```

### Key Integration Points

1. **Backward Compatibility**: All existing Weev functionality remains unchanged
2. **Memory Bridge**: Seamless integration between Weev and LangChain memory systems
3. **State Management**: LangGraph provides persistent state across workflow executions
4. **Tool Ecosystem**: Access to LangChain's extensive tool library
5. **Streaming**: Real-time updates for better user experience

## Core Components

### 1. LangGraphManager

The core orchestrator for stateful AI workflows.

**Features:**
- State-based workflow execution
- Persistent checkpointing
- Error recovery and retry logic
- Real-time streaming support

**Usage:**
```python
from langchain_integration import LangGraphManager

manager = LangGraphManager(
    llm_manager=app.state.llm_manager,
    db_session=db_session
)

# Create workflow graph
graph = await manager.create_workflow_graph(workflow_config)

# Execute with streaming
async for update in manager.stream_workflow(workflow_id, input_data):
    print(update)
```

### 2. VectorStoreManager

Unified interface for vector database operations.

**Supported Providers:**
- ChromaDB (default, local development)
- Pinecone (production, cloud)
- Qdrant (self-hosted, high-performance)
- FAISS (local, high-speed)

**Usage:**
```python
from langchain_integration.vector_store import VectorStoreManager

# Initialize
vector_manager = VectorStoreManager()

# Add documents
await vector_manager.add_documents([
    {
        "text": "AI agents are autonomous software systems...",
        "metadata": {"type": "definition", "topic": "ai"}
    }
])

# Search
results = await vector_manager.similarity_search(
    "What are AI agents?", 
    k=5, 
    score_threshold=0.8
)
```

### 3. ToolRegistry

Centralized management for LangChain tools.

**Features:**
- Role-based access control
- Rate limiting
- Performance monitoring
- Security validation

**Usage:**
```python
from langchain_integration import ToolRegistry
from tools import WebSearchTool

registry = ToolRegistry()
registry.register_tool(WebSearchTool(), category="web")

# Get tools for user
tools = registry.get_available_tools(user_id="user123")
```

### 4. MemoryManager

Bridge between Weev and LangChain memory systems.

**Memory Types:**
- Conversation: Turn-by-turn dialogue
- Buffer: Fixed-size recent memory
- Summary: Compressed conversation summaries  
- Vector: Semantic memory search

**Usage:**
```python
from langchain_integration import LangChainMemoryManager

memory_manager = LangChainMemoryManager(
    vector_store_manager=vector_manager
)

# Add conversation turn
await memory_manager.add_conversation_turn(
    workflow_id="wf_123",
    human_message="What is AI?",
    ai_message="AI is artificial intelligence..."
)

# Get relevant context
context = await memory_manager.get_relevant_context(
    workflow_id="wf_123",
    query="Tell me more",
    max_tokens=1000
)
```

## Node Types

### 1. LangChainBrainNode

Enhanced brain node with state-based reasoning.

**Features:**
- Multi-step reasoning workflows
- Tool integration
- Human-in-the-loop approval
- Advanced memory management

**Configuration:**
```python
{
    "node_type": "LangChainBrainNode",
    "config": {
        "problem": "Analyze market trends for Q1 planning",
        "use_tools": ["web_search", "database_query"],
        "require_approval": false,
        "max_reasoning_steps": 10
    }
}
```

### 2. RAGChainNode

Retrieval-Augmented Generation for knowledge-based answers.

**Features:**
- Multi-source document retrieval
- Semantic similarity search
- Source attribution
- Context ranking and filtering

**Configuration:**
```python
{
    "node_type": "RAGChainNode",
    "config": {
        "question": "What are the benefits of automation?",
        "retrieval_config": {
            "k": 5,
            "score_threshold": 0.8,
            "metadata_filter": {"type": "technical"},
            "max_context_length": 4000
        }
    }
}
```

### 3. AgentExecutorNode

Autonomous agent with tool-calling capabilities.

**Features:**
- Dynamic tool selection
- Multi-step task execution
- Error handling and recovery
- Performance monitoring

**Configuration:**
```python
{
    "node_type": "AgentExecutorNode",
    "config": {
        "task": "Research competitor pricing",
        "available_tools": ["web_search", "api_call"],
        "max_iterations": 5,
        "timeout_seconds": 300
    }
}
```

## Configuration

### Vector Database Setup

#### ChromaDB (Default)
```python
# Automatic setup - no additional configuration required
VECTOR_DB_PROVIDER=chroma
VECTOR_DB_PERSIST_DIR=./vector_db
```

#### Pinecone (Production)
```python
VECTOR_DB_PROVIDER=pinecone
PINECONE_API_KEY=your-api-key
PINECONE_ENV=us-west1-gcp
```

#### Qdrant (Self-hosted)
```python
VECTOR_DB_PROVIDER=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-api-key  # Optional
```

### Tool Configuration

Tools are automatically registered based on available API keys:

```python
# Web Search Tools
GOOGLE_API_KEY=your-key          # Enables Google search
BING_SEARCH_API_KEY=your-key     # Enables Bing search
SERP_API_KEY=your-key            # Enables SerpAPI

# Always available (no API key required)
# - Database queries
# - API calls
# - Text processing
```

## Usage Examples

### Basic RAG Workflow

```python
# 1. Add documents to knowledge base
POST /vector/add_documents
{
    "documents": [
        {
            "text": "Company policy on remote work...",
            "metadata": {"type": "policy", "department": "hr"}
        }
    ]
}

# 2. Execute RAG query
POST /api/workflow/execute
{
    "workflow_id": "rag_demo",
    "nodes": [
        {
            "node_id": "rag_1",
            "node_type": "RAGChainNode",
            "config": {
                "question": "What is our remote work policy?",
                "retrieval_config": {
                    "k": 3,
                    "score_threshold": 0.8
                }
            }
        }
    ]
}
```

### Enhanced Brain Reasoning

```python
POST /api/workflow/execute
{
    "workflow_id": "enhanced_reasoning",
    "nodes": [
        {
            "node_id": "brain_1",
            "node_type": "LangChainBrainNode",
            "config": {
                "problem": "Should we expand to the European market?",
                "use_tools": ["web_search", "database_query"],
                "reasoning_steps": [
                    "Research market size",
                    "Analyze competition",
                    "Evaluate regulatory requirements",
                    "Calculate potential ROI"
                ]
            }
        }
    ]
}
```

### Multi-Agent Workflow

```python
POST /api/workflow/execute
{
    "workflow_id": "research_workflow",
    "nodes": [
        {
            "node_id": "researcher",
            "node_type": "AgentExecutorNode",
            "config": {
                "role": "researcher",
                "task": "Gather information about AI trends",
                "tools": ["web_search"]
            }
        },
        {
            "node_id": "analyst",
            "node_type": "AgentExecutorNode",
            "config": {
                "role": "analyst",
                "task": "Analyze research findings",
                "tools": ["database_query"]
            }
        }
    ],
    "connections": [
        {"from": "researcher", "to": "analyst"}
    ]
}
```

## API Endpoints

### Health Check Endpoints

```bash
# General health
GET /health

# LangChain components health
GET /health/langchain

# Vector database health
GET /health/vector
```

### Vector Operations

```bash
# Add documents
POST /vector/add_documents
{
    "documents": [...],
    "batch_size": 100
}

# Search documents
POST /vector/search
{
    "query": "search query",
    "k": 5,
    "score_threshold": 0.8,
    "metadata_filter": {"type": "document"}
}

# Health check
GET /vector/health
```

### Tool Management

```bash
# List available tools
GET /tools/available

# Execute tool directly
POST /tools/execute
{
    "tool_name": "web_search",
    "input": "latest AI news"
}
```

### Enhanced Workflows

```bash
# Execute enhanced workflow
POST /api/workflow/enhanced
{
    "workflow_id": "enhanced_001",
    "use_langchain": true,
    "enable_rag": true,
    "nodes": [...],
    "connections": [...]
}

# Stream workflow execution
WebSocket /ws/enhanced
```

## Best Practices

### 1. Vector Database Management

**Document Preparation:**
```python
# Good: Well-structured documents with metadata
{
    "text": "Clear, focused content about a specific topic",
    "metadata": {
        "title": "Document Title",
        "type": "article",
        "date": "2024-01-15",
        "source": "internal",
        "tags": ["ai", "automation"]
    }
}

# Avoid: Long, unfocused content without context
{
    "text": "Very long document with multiple unrelated topics...",
    "metadata": {}
}
```

**Chunking Strategy:**
- Use 500-1000 token chunks for most content
- Overlap chunks by 50-100 tokens
- Preserve sentence boundaries
- Include context in metadata

### 2. RAG Implementation

**Query Design:**
```python
# Good: Specific, well-formed questions
"What are the key benefits of implementing AI automation in customer service?"

# Avoid: Vague or overly broad queries
"Tell me about AI"
```

**Context Management:**
```python
# Optimal retrieval configuration
{
    "k": 5,                          # Retrieve 5 documents
    "score_threshold": 0.8,          # High similarity threshold
    "max_context_length": 4000,      # Reasonable context window
    "rerank": true,                  # Enable reranking
    "diversity_threshold": 0.8       # Ensure diverse results
}
```

### 3. Tool Usage

**Security:**
- Always validate tool inputs
- Use role-based access control
- Monitor tool execution
- Set appropriate rate limits

**Performance:**
- Cache frequently used tool results
- Use parallel execution where possible
- Set reasonable timeouts
- Implement circuit breakers

### 4. Memory Management

**Conversation Memory:**
```python
# Configure appropriate memory limits
{
    "max_conversation_turns": 100,
    "summary_frequency": 20,
    "vector_similarity_threshold": 0.8,
    "persistence_enabled": true
}
```

**Context Window Management:**
- Keep recent conversations in buffer memory
- Use summaries for long conversations
- Store important information in vector memory
- Clean up old memories periodically

## Troubleshooting

### Common Issues

#### 1. Vector Store Connection Issues

**Problem:** Vector store initialization fails
```
Error: Vector store initialization failed: connection timeout
```

**Solutions:**
- Check database connectivity
- Verify API keys and credentials
- Ensure sufficient disk space
- Check firewall settings

#### 2. Memory Issues

**Problem:** High memory usage
```
Warning: Memory usage exceeding limits
```

**Solutions:**
- Reduce chunk sizes
- Implement memory cleanup
- Use appropriate model sizes
- Enable memory compression

#### 3. Tool Execution Failures

**Problem:** Tools fail with authentication errors
```
Error: API authentication failed
```

**Solutions:**
- Verify API keys are correct
- Check rate limits
- Ensure proper permissions
- Test with minimal examples

### Debugging

#### Enable Debug Logging

```python
import logging
logging.getLogger("weev.langchain").setLevel(logging.DEBUG)
```

#### Performance Monitoring

```python
# Get component statistics
GET /health/langchain
GET /tools/available
GET /vector/health

# Monitor performance
{
    "vector_store_stats": {...},
    "tool_usage_stats": {...},
    "memory_stats": {...}
}
```

#### Common Debug Commands

```bash
# Check vector store health
curl http://localhost:8000/health/vector

# List available tools
curl http://localhost:8000/tools/available

# Test vector search
curl -X POST http://localhost:8000/vector/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "k": 3}'
```

## Performance Optimization

### Vector Database Optimization

1. **Index Optimization**
   - Use appropriate distance metrics
   - Optimize index parameters
   - Regular index maintenance

2. **Query Optimization**
   - Use specific queries
   - Implement query caching
   - Optimize batch sizes

3. **Storage Optimization**
   - Compress embeddings
   - Use efficient storage formats
   - Implement data lifecycle policies

### Tool Performance

1. **Caching Strategy**
   - Cache expensive operations
   - Use TTL-based expiration
   - Implement cache warming

2. **Connection Pooling**
   - Pool database connections
   - Reuse HTTP sessions
   - Optimize connection limits

3. **Parallel Execution**
   - Execute independent tools in parallel
   - Use async/await patterns
   - Implement proper error handling

### Memory Optimization

1. **Memory Lifecycle**
   - Regular cleanup of old memories
   - Implement memory compression
   - Use appropriate retention policies

2. **Context Management**
   - Optimize context window sizes
   - Use smart truncation strategies
   - Implement relevance scoring

## Monitoring and Observability

### Key Metrics

```python
{
    "vector_store": {
        "total_documents": 10000,
        "query_latency_p95": 150,
        "storage_size_gb": 2.5
    },
    "tools": {
        "total_executions": 5000,
        "success_rate": 0.95,
        "avg_response_time": 500
    },
    "workflows": {
        "total_executions": 1000,
        "enhanced_workflows": 300,
        "avg_execution_time": 2.5
    }
}
```

### Alerting

Set up alerts for:
- High error rates (>5%)
- Slow response times (>5s)
- Resource usage (>80%)
- API quota limits (>90%)

## Contributing

To contribute to the LangChain integration:

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd weev-final/Backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/langchain_integration/

# Run linting
flake8 langchain_integration/
```

## Support

For support with the LangChain integration:

1. Check this documentation
2. Review the troubleshooting section
3. Check existing GitHub issues
4. Create a new issue with detailed information

## License

This LangChain integration is part of the Weev Platform and follows the same licensing terms.