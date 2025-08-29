"""
LangChain-Powered Nodes for Weev Platform

This module contains LangChain-enhanced node implementations that extend the capabilities
of the existing Weev node system with advanced AI agent features.

Node Types:
==========

1. **LangChainBrainNode**: Enhanced reasoning node using LangGraph state management
2. **RAGChainNode**: Retrieval-Augmented Generation for knowledge-based workflows
3. **AgentExecutorNode**: Autonomous agent with tool-calling capabilities
4. **ToolCallingNode**: Specialized node for external tool integration
5. **ConversationChainNode**: Multi-turn conversation management

Architecture:
============

All LangChain nodes inherit from the existing GeneralNodeLogic base class to ensure
compatibility with the existing Weev workflow system. They extend functionality by:

- Using LangGraph for state management and complex workflows
- Integrating with LangChain's tool ecosystem
- Providing enhanced memory and context management
- Supporting human-in-the-loop workflows

Integration Pattern:
==================

Each node follows this integration pattern:

1. **Initialization**: Sets up LangChain components (chains, tools, memory)
2. **State Bridge**: Converts Weev state to LangGraph state format
3. **Execution**: Runs LangChain/LangGraph workflows
4. **Result Processing**: Converts results back to Weev format
5. **Memory Update**: Updates both Weev and LangChain memory systems

Usage:
======

```python
from langchain_integration.nodes import LangChainBrainNode, RAGChainNode

# Create enhanced brain node
brain_node = LangChainBrainNode(
    node_id="brain_enhanced",
    name="Enhanced Brain",
    graph_manager=graph_manager
)

# Create RAG-enabled knowledge node
rag_node = RAGChainNode(
    node_id="rag_knowledge",
    name="RAG Knowledge Base",
    vector_store=vector_store
)
```
"""

from .langchain_brain_node import LangChainBrainNode
from .rag_chain_node import RAGChainNode
from .agent_executor_node import AgentExecutorNode
from .tool_calling_node import ToolCallingNode

__all__ = [
    "LangChainBrainNode",
    "RAGChainNode", 
    "AgentExecutorNode",
    "ToolCallingNode"
]