"""
LangChain Chain Implementations for Weev Platform

This module provides specialized LangChain chain implementations optimized for
the Weev AI agent workflow platform. These chains handle common patterns like
conversation management, RAG, summarization, and complex decision making.

Chain Types:
===========

1. **ConversationChain**: Multi-turn conversations with memory management
2. **RAGChain**: Retrieval-Augmented Generation for knowledge-based queries  
3. **SummarizationChain**: Document and conversation summarization
4. **DecisionChain**: Complex multi-criteria decision making
5. **SequentialChain**: Linear workflow execution
6. **ParallelChain**: Concurrent processing workflows
7. **RouterChain**: Conditional branching based on input analysis

Architecture Principles:
=======================

1. **Composability**: Chains can be combined to create complex workflows
2. **State Awareness**: All chains support LangGraph state management
3. **Memory Integration**: Seamless integration with Weev's WorkflowMemory
4. **Tool Support**: Chains can invoke tools through the unified ToolRegistry
5. **Streaming Support**: Real-time streaming for better UX
6. **Error Handling**: Robust error recovery and retry mechanisms

Chain Composition Patterns:
==========================

**Sequential Pattern**: 
Chain A → Chain B → Chain C (linear execution)

**Parallel Pattern**: 
Input → [Chain A, Chain B, Chain C] → Aggregation

**Router Pattern**: 
Input → Analysis → Route to appropriate chain

**MapReduce Pattern**: 
Input → Map to multiple chains → Reduce results

Usage Examples:
==============

```python
from chains import ConversationChain, RAGChain, DecisionChain

# Create a conversation chain with memory
conversation = ConversationChain(
    llm_manager=llm_manager,
    memory_manager=memory_manager
)

# Create a RAG chain for knowledge queries
rag_chain = RAGChain(
    llm_manager=llm_manager,
    vector_store=vector_store,
    retriever_config={"k": 5}
)

# Compose chains for complex workflows
decision_workflow = DecisionChain(
    criteria=["accuracy", "efficiency", "cost"],
    input_chains=[rag_chain, conversation]
)
```

Integration with Weev Nodes:
===========================

Chains are used internally by LangChain nodes but can also be used directly:

```python
# Use chain in a custom node
class CustomNode(GeneralNodeLogic):
    def __init__(self, chain):
        super().__init__()
        self.chain = chain
    
    async def execute(self, inputs):
        result = await self.chain.ainvoke(inputs)
        return self.format_output(result)
```
"""

from .conversation_chain import ConversationChain
from .rag_chain import RAGChain  
from .summarization_chain import SummarizationChain
from .decision_chain import DecisionChain

__all__ = [
    "ConversationChain",
    "RAGChain",
    "SummarizationChain", 
    "DecisionChain"
]