"""
LangChain Integration Module for Weev AI Agent Workflow Platform

This package provides comprehensive LangChain and LangGraph integration for the Weev platform,
enabling advanced AI agent workflows with state management, tool integration, and multi-agent
orchestration capabilities.

Architecture Overview:
===================

The LangChain integration follows a modular architecture that bridges the existing Weev node
system with LangChain's powerful workflow capabilities:

1. **Hybrid Approach**: Maintains backward compatibility with existing nodes while adding
   LangChain-powered nodes for advanced workflows

2. **State Management**: Uses LangGraph's state persistence to maintain conversation context
   and workflow state across multiple interactions

3. **Tool Integration**: Provides a unified tool registry that connects LangChain tools
   with Weev's existing external integrations

4. **Memory Bridge**: Creates seamless interoperability between Weev's WorkflowMemory
   and LangChain's memory systems

5. **Multi-Agent Support**: Enables complex multi-agent workflows with proper coordination
   and communication patterns

Key Components:
==============

- **graph_manager.py**: Core LangGraph workflow orchestrator
- **chain_factory.py**: Factory for creating and managing LangChain chains
- **memory_manager.py**: Enhanced memory management with LangChain integration
- **tool_registry.py**: Unified tool registration and management system
- **nodes/**: LangChain-powered node implementations

Integration Benefits:
===================

1. **Enhanced Reasoning**: Advanced multi-step reasoning with state persistence
2. **Tool Ecosystem**: Access to LangChain's extensive tool ecosystem
3. **Memory Management**: Sophisticated conversation and context memory
4. **Human-in-the-Loop**: Built-in approval workflows and human oversight
5. **Scalability**: Parallel execution and efficient resource management

Usage:
======

The integration is designed to be used alongside existing Weev nodes:

```python
from langchain_integration import LangGraphManager, LangChainBrainNode

# Initialize LangGraph manager
graph_manager = LangGraphManager(llm_manager=app.state.llm_manager)

# Create enhanced brain node
brain_node = LangChainBrainNode(
    node_id="brain_1",
    name="Enhanced Brain",
    graph_manager=graph_manager
)
```

Author: Weev Platform Team
Version: 1.0.0
Date: 2025-01-XX
"""

from .graph_manager import LangGraphManager
from .memory_manager import LangChainMemoryManager
from .tool_registry import ToolRegistry

__version__ = "1.0.0"
__all__ = [
    "LangGraphManager",
    "LangChainMemoryManager",
    "ToolRegistry"
]