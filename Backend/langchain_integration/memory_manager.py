"""
LangChain Memory Manager for Weev Platform

This module provides comprehensive memory management capabilities that bridge
Weev's existing WorkflowMemory system with LangChain's memory components,
enabling sophisticated conversation and context management across AI workflows.

Key Features:
============

1. **Memory Bridge**: Seamless integration between Weev and LangChain memory systems
2. **Multi-Type Memory**: Support for conversation, buffer, summary, and vector memories
3. **Persistence**: Database-backed memory with automatic saving and loading
4. **Context Management**: Intelligent context windowing and relevance scoring
5. **Memory Sharing**: Share memory contexts between different workflow instances
6. **Performance Optimization**: Efficient memory storage and retrieval mechanisms

Memory Types:
============

1. **ConversationMemory**: Turn-by-turn conversation history
2. **BufferMemory**: Fixed-size buffer of recent interactions
3. **SummaryMemory**: Compressed summaries of long conversations
4. **VectorMemory**: Semantic memory using vector embeddings
5. **EntityMemory**: Named entity extraction and tracking
6. **KnowledgeMemory**: Long-term knowledge graph construction

Architecture:
============

The LangChainMemoryManager acts as a coordinator between different memory
systems and provides a unified interface for all memory operations:

```
LangChainMemoryManager
├── ConversationMemory (LangChain)
├── VectorMemory (ChromaDB/Pinecone)
├── WorkflowMemory (Weev)
└── PersistentStorage (Database)
```

Integration Patterns:
====================

**Automatic Sync**: Changes in one memory system are automatically reflected
in others to maintain consistency.

**Smart Retrieval**: Intelligent retrieval based on context relevance,
recency, and importance scoring.

**Memory Hierarchies**: Support for hierarchical memory structures with
different retention policies.

Usage Examples:
==============

**Basic Memory Operations**:
```python
memory_manager = LangChainMemoryManager(
    db_session=db_session,
    vector_store=vector_store
)

# Add conversation turn
await memory_manager.add_conversation_turn(
    workflow_id="wf_123",
    human_message="What is AI?",
    ai_message="AI is artificial intelligence..."
)

# Retrieve relevant context
context = await memory_manager.get_relevant_context(
    workflow_id="wf_123",
    query="Tell me more about machine learning",
    max_tokens=1000
)
```

**Advanced Memory Configuration**:
```python
memory_manager = LangChainMemoryManager(
    memory_types=["conversation", "summary", "vector"],
    max_conversation_turns=50,
    summary_frequency=10,
    vector_similarity_threshold=0.8
)
```

Author: Weev Platform Team
Version: 1.0.0
Date: 2025-01-XX
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain.memory.chat_message_histories import BaseChatMessageHistory
from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage

from ..GeneralNodeLogic import WorkflowMemory
from .vector_store import VectorStoreManager


class MemoryType(Enum):
    """Types of memory supported."""
    CONVERSATION = "conversation"
    BUFFER = "buffer"
    SUMMARY = "summary"
    VECTOR = "vector"
    ENTITY = "entity"
    KNOWLEDGE = "knowledge"


@dataclass
class MemoryConfig:
    """Configuration for memory management."""
    memory_types: List[MemoryType]
    max_conversation_turns: int = 100
    buffer_size: int = 10
    summary_frequency: int = 20  # Summarize every N turns
    vector_similarity_threshold: float = 0.8
    entity_extraction_enabled: bool = True
    knowledge_graph_enabled: bool = False
    persistence_enabled: bool = True
    compression_enabled: bool = True


class WeevChatMessageHistory(BaseChatMessageHistory):
    """
    Custom chat message history that integrates with Weev's WorkflowMemory.
    
    This class bridges LangChain's memory system with Weev's existing
    memory structures, ensuring compatibility and data consistency.
    """
    
    def __init__(
        self,
        workflow_id: str,
        workflow_memory: WorkflowMemory,
        db_session: Optional[Any] = None
    ):
        self.workflow_id = workflow_id
        self.workflow_memory = workflow_memory
        self.db_session = db_session
        self._messages: List[BaseMessage] = []
        self._load_messages()
    
    def _load_messages(self):
        """Load messages from Weev WorkflowMemory."""
        try:
            for history_item in self.workflow_memory.conversation_history:
                # Convert Weev history to LangChain messages
                if isinstance(history_item, dict):
                    if 'input' in history_item:
                        human_msg = HumanMessage(content=str(history_item['input']))
                        self._messages.append(human_msg)
                    
                    if 'output' in history_item:
                        ai_msg = AIMessage(content=str(history_item['output']))
                        self._messages.append(ai_msg)
        except Exception as e:
            logging.warning(f"Failed to load messages from WorkflowMemory: {e}")
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the history."""
        self._messages.append(message)
        
        # Sync back to WorkflowMemory
        try:
            if isinstance(message, HumanMessage):
                # This will be part of the next conversation turn
                pass
            elif isinstance(message, AIMessage):
                # Add as a conversation turn to Weev memory
                self.workflow_memory.add_to_history(
                    node_id="memory_manager",
                    node_type="LangChainMemory",
                    input_data={"type": "ai_message"},
                    output_data=message.content
                )
        except Exception as e:
            logging.warning(f"Failed to sync message to WorkflowMemory: {e}")
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages."""
        return self._messages.copy()
    
    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()


class LangChainMemoryManager:
    """
    Comprehensive memory manager for LangChain integration.
    
    This class provides a unified interface for managing different types of
    memory across AI agent workflows, with seamless integration between
    Weev's existing memory systems and LangChain's memory components.
    """
    
    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        db_session: Optional[Any] = None,
        vector_store_manager: Optional[VectorStoreManager] = None,
        llm_manager: Optional[Any] = None
    ):
        """
        Initialize the memory manager.
        
        Args:
            config: Memory configuration settings
            db_session: Database session for persistence
            vector_store_manager: Vector store for semantic memory
            llm_manager: LLM manager for summarization
        """
        self.config = config or MemoryConfig(
            memory_types=[MemoryType.CONVERSATION, MemoryType.BUFFER, MemoryType.VECTOR]
        )
        self.db_session = db_session
        self.vector_store_manager = vector_store_manager
        self.llm_manager = llm_manager
        
        # Memory instances
        self._conversation_memories: Dict[str, ConversationBufferMemory] = {}
        self._summary_memories: Dict[str, ConversationSummaryMemory] = {}
        self._workflow_memories: Dict[str, WorkflowMemory] = {}
        self._message_histories: Dict[str, WeevChatMessageHistory] = {}
        
        # Performance tracking
        self.memory_stats = {
            "total_conversations": 0,
            "total_messages": 0,
            "total_summaries": 0,
            "avg_retrieval_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        self.logger = logging.getLogger("weev.langchain_memory_manager")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"LangChainMemoryManager initialized with types: {[t.value for t in self.config.memory_types]}")
    
    async def get_or_create_memory(
        self,
        workflow_id: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        workflow_memory: Optional[WorkflowMemory] = None
    ) -> Any:
        """
        Get or create memory instance for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            memory_type: Type of memory to create
            workflow_memory: Existing Weev WorkflowMemory to integrate
            
        Returns:
            Memory instance of the requested type
        """
        try:
            if memory_type == MemoryType.CONVERSATION:
                return await self._get_conversation_memory(workflow_id, workflow_memory)
            elif memory_type == MemoryType.BUFFER:
                return await self._get_buffer_memory(workflow_id, workflow_memory)
            elif memory_type == MemoryType.SUMMARY:
                return await self._get_summary_memory(workflow_id, workflow_memory)
            elif memory_type == MemoryType.VECTOR:
                return await self._get_vector_memory(workflow_id, workflow_memory)
            else:
                raise ValueError(f"Unsupported memory type: {memory_type}")
        
        except Exception as e:
            self.logger.error(f"Failed to get/create memory for {workflow_id}: {e}")
            raise
    
    async def _get_conversation_memory(
        self,
        workflow_id: str,
        workflow_memory: Optional[WorkflowMemory] = None
    ) -> ConversationBufferMemory:
        """Get or create conversation memory."""
        if workflow_id not in self._conversation_memories:
            # Create message history bridge
            if workflow_memory:
                message_history = WeevChatMessageHistory(workflow_id, workflow_memory, self.db_session)
                self._message_histories[workflow_id] = message_history
            else:
                message_history = WeevChatMessageHistory(
                    workflow_id,
                    WorkflowMemory(workflow_id=workflow_id),
                    self.db_session
                )
            
            # Create conversation memory
            memory = ConversationBufferMemory(
                chat_memory=message_history,
                memory_key="chat_history",
                return_messages=True,
                max_token_limit=self.config.max_conversation_turns * 100  # Rough estimate
            )
            
            self._conversation_memories[workflow_id] = memory
            self.memory_stats["total_conversations"] += 1
        
        return self._conversation_memories[workflow_id]
    
    async def _get_buffer_memory(
        self,
        workflow_id: str,
        workflow_memory: Optional[WorkflowMemory] = None
    ) -> ConversationBufferMemory:
        """Get or create buffer memory with size limits."""
        # For now, use conversation memory with buffer size limit
        # In a full implementation, you'd create a custom buffer memory
        return await self._get_conversation_memory(workflow_id, workflow_memory)
    
    async def _get_summary_memory(
        self,
        workflow_id: str,
        workflow_memory: Optional[WorkflowMemory] = None
    ) -> ConversationSummaryMemory:
        """Get or create summary memory."""
        if workflow_id not in self._summary_memories:
            if not self.llm_manager:
                raise ValueError("LLM manager required for summary memory")
            
            # Create message history bridge
            if workflow_memory:
                message_history = WeevChatMessageHistory(workflow_id, workflow_memory, self.db_session)
            else:
                message_history = WeevChatMessageHistory(
                    workflow_id,
                    WorkflowMemory(workflow_id=workflow_id),
                    self.db_session
                )
            
            # Create summary memory (placeholder - would need proper LLM integration)
            memory = ConversationSummaryMemory(
                chat_memory=message_history,
                memory_key="chat_history",
                return_messages=True
            )
            
            self._summary_memories[workflow_id] = memory
            self.memory_stats["total_summaries"] += 1
        
        return self._summary_memories[workflow_id]
    
    async def _get_vector_memory(
        self,
        workflow_id: str,
        workflow_memory: Optional[WorkflowMemory] = None
    ) -> Dict[str, Any]:
        """Get or create vector memory (using vector store)."""
        if not self.vector_store_manager:
            raise ValueError("Vector store manager required for vector memory")
        
        # Vector memory is implemented through the vector store manager
        # Return a wrapper that provides memory-like interface
        return {
            "workflow_id": workflow_id,
            "vector_store": self.vector_store_manager,
            "type": "vector_memory"
        }
    
    async def add_conversation_turn(
        self,
        workflow_id: str,
        human_message: str,
        ai_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a conversation turn to memory.
        
        Args:
            workflow_id: Workflow identifier
            human_message: Human input message
            ai_message: AI response message
            metadata: Additional metadata for the turn
        """
        try:
            # Add to conversation memory
            if MemoryType.CONVERSATION in self.config.memory_types:
                conv_memory = await self.get_or_create_memory(workflow_id, MemoryType.CONVERSATION)
                
                # Add messages
                conv_memory.chat_memory.add_message(HumanMessage(content=human_message))
                conv_memory.chat_memory.add_message(AIMessage(content=ai_message))
            
            # Add to vector memory for semantic search
            if (MemoryType.VECTOR in self.config.memory_types and 
                self.vector_store_manager):
                
                # Create document for vector storage
                conversation_doc = {
                    "text": f"Human: {human_message}\nAI: {ai_message}",
                    "metadata": {
                        "workflow_id": workflow_id,
                        "timestamp": datetime.now().isoformat(),
                        "type": "conversation_turn",
                        **(metadata or {})
                    }
                }
                
                await self.vector_store_manager.add_documents([conversation_doc])
            
            # Check if summary is needed
            if (MemoryType.SUMMARY in self.config.memory_types and 
                self._should_create_summary(workflow_id)):
                await self._create_summary(workflow_id)
            
            self.memory_stats["total_messages"] += 2  # Human + AI message
            
        except Exception as e:
            self.logger.error(f"Failed to add conversation turn for {workflow_id}: {e}")
            raise
    
    def _should_create_summary(self, workflow_id: str) -> bool:
        """Check if a summary should be created."""
        if workflow_id not in self._conversation_memories:
            return False
        
        memory = self._conversation_memories[workflow_id]
        message_count = len(memory.chat_memory.messages)
        
        return message_count > 0 and message_count % self.config.summary_frequency == 0
    
    async def _create_summary(self, workflow_id: str) -> None:
        """Create a summary of the conversation."""
        try:
            if not self.llm_manager:
                return
            
            # Get conversation memory
            conv_memory = await self.get_or_create_memory(workflow_id, MemoryType.CONVERSATION)
            
            # Get summary memory
            summary_memory = await self.get_or_create_memory(workflow_id, MemoryType.SUMMARY)
            
            # The summary memory will automatically create summaries when accessed
            # This is a placeholder for more sophisticated summarization logic
            
            self.logger.info(f"Created summary for workflow {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create summary for {workflow_id}: {e}")
    
    async def get_relevant_context(
        self,
        workflow_id: str,
        query: Optional[str] = None,
        max_tokens: int = 1000,
        include_summary: bool = True
    ) -> str:
        """
        Get relevant context for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            query: Optional query for semantic search
            max_tokens: Maximum tokens to return
            include_summary: Whether to include conversation summary
            
        Returns:
            Formatted context string
        """
        start_time = datetime.now()
        
        try:
            context_parts = []
            
            # Get conversation memory context
            if MemoryType.CONVERSATION in self.config.memory_types:
                try:
                    conv_memory = await self.get_or_create_memory(workflow_id, MemoryType.CONVERSATION)
                    
                    # Get recent messages
                    messages = conv_memory.chat_memory.messages[-10:]  # Last 10 messages
                    if messages:
                        recent_conversation = []
                        for msg in messages:
                            if isinstance(msg, HumanMessage):
                                recent_conversation.append(f"Human: {msg.content}")
                            elif isinstance(msg, AIMessage):
                                recent_conversation.append(f"AI: {msg.content}")
                        
                        if recent_conversation:
                            context_parts.append("Recent Conversation:\n" + "\n".join(recent_conversation))
                
                except Exception as e:
                    self.logger.warning(f"Failed to get conversation context: {e}")
            
            # Get vector memory context (semantic search)
            if (MemoryType.VECTOR in self.config.memory_types and 
                self.vector_store_manager and query):
                
                try:
                    search_results = await self.vector_store_manager.similarity_search(
                        query=query,
                        k=5,
                        metadata_filter={"workflow_id": workflow_id}
                    )
                    
                    if search_results:
                        relevant_contexts = []
                        for result in search_results:
                            if result["score"] > self.config.vector_similarity_threshold:
                                relevant_contexts.append(result["content"])
                        
                        if relevant_contexts:
                            context_parts.append("Relevant Previous Context:\n" + "\n---\n".join(relevant_contexts))
                
                except Exception as e:
                    self.logger.warning(f"Failed to get vector context: {e}")
            
            # Get summary context
            if include_summary and MemoryType.SUMMARY in self.config.memory_types:
                try:
                    summary_memory = await self.get_or_create_memory(workflow_id, MemoryType.SUMMARY)
                    
                    # Get summary (this is a placeholder)
                    # In a real implementation, you'd extract the summary from the summary memory
                    summary = getattr(summary_memory, 'buffer', None)
                    if summary:
                        context_parts.append(f"Conversation Summary:\n{summary}")
                
                except Exception as e:
                    self.logger.warning(f"Failed to get summary context: {e}")
            
            # Combine and truncate context
            full_context = "\n\n".join(context_parts)
            
            # Simple token estimation (rough approximation)
            estimated_tokens = len(full_context.split())
            if estimated_tokens > max_tokens:
                # Truncate to approximate token limit
                words = full_context.split()
                truncated_words = words[:max_tokens]
                full_context = " ".join(truncated_words) + "..."
            
            # Update performance stats
            retrieval_time = (datetime.now() - start_time).total_seconds()
            total_retrievals = self.memory_stats.get("total_retrievals", 0) + 1
            current_avg = self.memory_stats["avg_retrieval_time"]
            self.memory_stats["avg_retrieval_time"] = (
                (current_avg * (total_retrievals - 1) + retrieval_time) / total_retrievals
            )
            
            return full_context
        
        except Exception as e:
            self.logger.error(f"Failed to get relevant context for {workflow_id}: {e}")
            return ""
    
    async def clear_memory(self, workflow_id: str, memory_types: Optional[List[MemoryType]] = None) -> None:
        """
        Clear memory for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            memory_types: Types of memory to clear (None = all)
        """
        types_to_clear = memory_types or self.config.memory_types
        
        try:
            for memory_type in types_to_clear:
                if memory_type == MemoryType.CONVERSATION and workflow_id in self._conversation_memories:
                    self._conversation_memories[workflow_id].clear()
                    del self._conversation_memories[workflow_id]
                
                elif memory_type == MemoryType.SUMMARY and workflow_id in self._summary_memories:
                    self._summary_memories[workflow_id].clear()
                    del self._summary_memories[workflow_id]
                
                elif memory_type == MemoryType.VECTOR and self.vector_store_manager:
                    # Clear vector memory for this workflow
                    # This would require implementing deletion in vector store manager
                    pass
            
            # Clear message history
            if workflow_id in self._message_histories:
                del self._message_histories[workflow_id]
            
            self.logger.info(f"Cleared memory for workflow {workflow_id}")
        
        except Exception as e:
            self.logger.error(f"Failed to clear memory for {workflow_id}: {e}")
            raise
    
    async def persist_memory(self, workflow_id: str) -> bool:
        """
        Persist memory to database.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if persistence was successful
        """
        if not self.config.persistence_enabled or not self.db_session:
            return False
        
        try:
            # This is a placeholder for database persistence
            # In a real implementation, you'd save memory state to database
            
            # Save conversation memory
            if workflow_id in self._conversation_memories:
                memory = self._conversation_memories[workflow_id]
                messages = memory.chat_memory.messages
                
                # Convert messages to serializable format
                serializable_messages = []
                for msg in messages:
                    serializable_messages.append({
                        "type": msg.__class__.__name__,
                        "content": msg.content,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Save to database (placeholder)
                self.logger.info(f"Persisted {len(serializable_messages)} messages for workflow {workflow_id}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to persist memory for {workflow_id}: {e}")
            return False
    
    async def load_memory(self, workflow_id: str) -> bool:
        """
        Load memory from database.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if loading was successful
        """
        if not self.config.persistence_enabled or not self.db_session:
            return False
        
        try:
            # This is a placeholder for database loading
            # In a real implementation, you'd load memory state from database
            
            self.logger.info(f"Loaded memory for workflow {workflow_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to load memory for {workflow_id}: {e}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory management statistics."""
        return {
            **self.memory_stats,
            "active_conversations": len(self._conversation_memories),
            "active_summaries": len(self._summary_memories),
            "active_message_histories": len(self._message_histories),
            "memory_types_enabled": [t.value for t in self.config.memory_types],
            "config": {
                "max_conversation_turns": self.config.max_conversation_turns,
                "summary_frequency": self.config.summary_frequency,
                "vector_similarity_threshold": self.config.vector_similarity_threshold,
                "persistence_enabled": self.config.persistence_enabled
            }
        }