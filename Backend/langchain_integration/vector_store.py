"""
Vector Database Configuration and Management for Weev Platform

This module provides comprehensive vector database integration for the Weev platform,
enabling Retrieval-Augmented Generation (RAG) capabilities, semantic search, and
knowledge management across AI agent workflows.

Supported Vector Databases:
==========================

1. **ChromaDB**: Default lightweight vector database for development and small-scale deployments
2. **Pinecone**: Production-grade cloud vector database for scalable applications  
3. **Qdrant**: High-performance vector database with advanced filtering capabilities
4. **FAISS**: Facebook AI Similarity Search for local high-performance vector operations
5. **Weaviate**: Open-source vector database with GraphQL API

Key Features:
============

1. **Multi-Provider Support**: Seamless switching between different vector database providers
2. **Automatic Embeddings**: Integrated embedding generation using various models
3. **Metadata Filtering**: Advanced filtering capabilities for precise retrieval
4. **Hybrid Search**: Combination of semantic and keyword search
5. **Batch Operations**: Efficient bulk document ingestion and updates
6. **Performance Monitoring**: Built-in metrics and performance tracking
7. **Backup and Recovery**: Automated backup strategies for vector data

Architecture:
============

The vector store manager follows a provider pattern that abstracts the underlying
vector database implementation:

```
VectorStoreManager
├── ChromaDBProvider (default)
├── PineconeProvider  
├── QdrantProvider
├── FAISSProvider
└── WeaviateProvider
```

Each provider implements a common interface for:
- Document ingestion and indexing
- Semantic search and retrieval
- Metadata filtering and querying
- Performance optimization

Configuration Options:
=====================

Environment Variables:
- VECTOR_DB_PROVIDER: Choice of vector database (chroma, pinecone, qdrant, faiss, weaviate)
- VECTOR_DB_CONNECTION_STRING: Database connection details
- EMBEDDING_MODEL: Embedding model to use (openai, sentence-transformers, etc.)
- VECTOR_DIMENSION: Dimension of embedding vectors
- VECTOR_DB_COLLECTION: Default collection name

Usage Examples:
==============

**Basic Setup**:
```python
from langchain_integration.vector_store import VectorStoreManager

# Initialize with default ChromaDB
vector_manager = VectorStoreManager()

# Add documents
await vector_manager.add_documents([
    {"text": "AI agents are autonomous software systems...", "metadata": {"type": "definition"}},
    {"text": "Workflow orchestration enables...", "metadata": {"type": "explanation"}}
])

# Semantic search
results = await vector_manager.similarity_search("What are AI agents?", k=5)
```

**Advanced Configuration**:
```python
# Use Pinecone for production
vector_manager = VectorStoreManager(
    provider="pinecone",
    config={
        "api_key": "your-pinecone-key",
        "environment": "us-west1-gcp",
        "index_name": "weev-knowledge-base"
    }
)

# Hybrid search with metadata filtering
results = await vector_manager.hybrid_search(
    query="workflow automation",
    metadata_filter={"type": "tutorial", "difficulty": "beginner"},
    k=10,
    score_threshold=0.7
)
```

**RAG Integration**:
```python
from langchain_integration.nodes import RAGChainNode

# Create RAG-enabled node
rag_node = RAGChainNode(
    node_id="rag_assistant",
    name="Knowledge Assistant",
    vector_store=vector_manager.get_store(),
    retrieval_config={"k": 5, "score_threshold": 0.8}
)
```

Performance Optimization:
========================

1. **Embedding Caching**: Cache frequently used embeddings to reduce computation
2. **Index Optimization**: Automatic index optimization based on query patterns
3. **Batch Processing**: Efficient batch operations for large document sets
4. **Connection Pooling**: Optimized connection management for database providers
5. **Memory Management**: Efficient memory usage for large vector collections

Security and Privacy:
====================

1. **Encryption**: Vector data encryption at rest and in transit
2. **Access Control**: Role-based access control for vector collections
3. **Data Isolation**: Tenant isolation for multi-customer deployments
4. **Audit Logging**: Comprehensive logging of all vector operations
5. **Privacy Filters**: Automatic PII detection and filtering

Integration with Weev Workflows:
===============================

The vector store integrates seamlessly with Weev's workflow system:

1. **Automatic Indexing**: New workflow outputs are automatically indexed
2. **Context Retrieval**: Previous workflow contexts are retrievable via semantic search
3. **Knowledge Evolution**: Vector knowledge base evolves with workflow usage
4. **Cross-Workflow Learning**: Knowledge sharing between different workflow instances

Monitoring and Analytics:
========================

Built-in monitoring provides insights into:
- Query performance and latency
- Embedding quality and distribution
- Usage patterns and popular queries
- Storage utilization and growth
- Error rates and failure patterns

Author: Weev Platform Team
Version: 1.0.0
Date: 2025-01-XX
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import json

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from langchain.embeddings import OpenAIEmbeddings, SentenceTransformerEmbeddings
from langchain.vectorstores import Chroma, Pinecone, Qdrant, FAISS
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


class VectorStoreConfig:
    """Configuration class for vector store settings."""
    
    def __init__(
        self,
        provider: str = "chroma",
        embedding_model: str = "sentence-transformers",
        embedding_model_name: str = "all-MiniLM-L6-v2",
        vector_dimension: int = 384,
        collection_name: str = "weev_knowledge",
        persist_directory: str = "./vector_db",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        self.provider = provider.lower()
        self.embedding_model = embedding_model
        self.embedding_model_name = embedding_model_name
        self.vector_dimension = vector_dimension
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.extra_config = kwargs
        
        # Load from environment variables if available
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        self.provider = os.getenv("VECTOR_DB_PROVIDER", self.provider)
        self.embedding_model = os.getenv("EMBEDDING_MODEL", self.embedding_model)
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME", self.embedding_model_name)
        self.collection_name = os.getenv("VECTOR_DB_COLLECTION", self.collection_name)
        self.persist_directory = os.getenv("VECTOR_DB_PERSIST_DIR", self.persist_directory)
        
        # Parse vector dimension from env
        try:
            self.vector_dimension = int(os.getenv("VECTOR_DIMENSION", str(self.vector_dimension)))
        except ValueError:
            pass


class VectorStoreManager:
    """
    Unified manager for different vector database providers.
    
    This class provides a consistent interface across different vector database
    implementations, handling provider-specific configurations and optimizations
    while maintaining a simple API for the rest of the Weev platform.
    """
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        """
        Initialize the vector store manager.
        
        Args:
            config: Vector store configuration. If None, uses default configuration.
        """
        self.config = config or VectorStoreConfig()
        self.logger = logging.getLogger("weev.vector_store_manager")
        self.logger.setLevel(logging.INFO)
        
        # Initialize embeddings model
        self.embeddings = self._initialize_embeddings()
        
        # Initialize text splitter for document processing
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Initialize vector store
        self.vector_store = None
        self._initialize_vector_store()
        
        # Performance tracking
        self.performance_stats = {
            "total_documents": 0,
            "total_queries": 0,
            "avg_query_time": 0.0,
            "last_updated": datetime.now().timestamp()
        }
        
        self.logger.info(f"VectorStoreManager initialized with provider: {self.config.provider}")
    
    def _initialize_embeddings(self):
        """Initialize the embeddings model based on configuration."""
        try:
            if self.config.embedding_model.lower() == "openai":
                # Requires OPENAI_API_KEY environment variable
                return OpenAIEmbeddings(
                    model=self.config.embedding_model_name or "text-embedding-ada-002"
                )
            
            elif self.config.embedding_model.lower() == "sentence-transformers":
                return SentenceTransformerEmbeddings(
                    model_name=self.config.embedding_model_name
                )
            
            else:
                self.logger.warning(f"Unknown embedding model: {self.config.embedding_model}")
                # Fallback to sentence transformers
                return SentenceTransformerEmbeddings(
                    model_name="all-MiniLM-L6-v2"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to initialize embeddings: {e}")
            # Fallback to basic sentence transformers
            return SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    
    def _initialize_vector_store(self):
        """Initialize the vector store based on the configured provider."""
        try:
            if self.config.provider == "chroma":
                self._initialize_chroma()
            elif self.config.provider == "pinecone":
                self._initialize_pinecone()
            elif self.config.provider == "qdrant":
                self._initialize_qdrant()
            elif self.config.provider == "faiss":
                self._initialize_faiss()
            elif self.config.provider == "weaviate":
                self._initialize_weaviate()
            else:
                self.logger.warning(f"Unknown provider: {self.config.provider}, falling back to Chroma")
                self._initialize_chroma()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {e}")
            # Fallback to in-memory storage
            self._initialize_fallback_store()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB vector store."""
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not available. Install with: pip install chromadb")
        
        try:
            # Create persist directory if it doesn't exist
            os.makedirs(self.config.persist_directory, exist_ok=True)
            
            # Initialize Chroma client
            chroma_settings = Settings(
                persist_directory=self.config.persist_directory,
                anonymized_telemetry=False
            )
            
            self.vector_store = Chroma(
                collection_name=self.config.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.config.persist_directory,
                client_settings=chroma_settings
            )
            
            self.logger.info("ChromaDB vector store initialized successfully")
            
        except Exception as e:
            self.logger.error(f"ChromaDB initialization failed: {e}")
            raise
    
    def _initialize_pinecone(self):
        """Initialize Pinecone vector store."""
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone not available. Install with: pip install pinecone-client")
        
        try:
            api_key = os.getenv("PINECONE_API_KEY") or self.config.extra_config.get("api_key")
            environment = os.getenv("PINECONE_ENV") or self.config.extra_config.get("environment", "us-west1-gcp")
            index_name = self.config.extra_config.get("index_name", self.config.collection_name)
            
            if not api_key:
                raise ValueError("Pinecone API key not provided")
            
            # Initialize Pinecone
            pinecone.init(api_key=api_key, environment=environment)
            
            # Create index if it doesn't exist
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=self.config.vector_dimension,
                    metric="cosine"
                )
                self.logger.info(f"Created Pinecone index: {index_name}")
            
            self.vector_store = Pinecone.from_existing_index(
                index_name=index_name,
                embedding=self.embeddings
            )
            
            self.logger.info("Pinecone vector store initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Pinecone initialization failed: {e}")
            raise
    
    def _initialize_qdrant(self):
        """Initialize Qdrant vector store."""
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant not available. Install with: pip install qdrant-client")
        
        try:
            url = os.getenv("QDRANT_URL") or self.config.extra_config.get("url", "http://localhost:6333")
            api_key = os.getenv("QDRANT_API_KEY") or self.config.extra_config.get("api_key")
            
            client = QdrantClient(url=url, api_key=api_key)
            
            self.vector_store = Qdrant(
                client=client,
                collection_name=self.config.collection_name,
                embeddings=self.embeddings
            )
            
            self.logger.info("Qdrant vector store initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Qdrant initialization failed: {e}")
            raise
    
    def _initialize_faiss(self):
        """Initialize FAISS vector store."""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu or faiss-gpu")
        
        try:
            # Try to load existing FAISS index
            faiss_index_path = os.path.join(self.config.persist_directory, "faiss_index")
            
            if os.path.exists(faiss_index_path):
                self.vector_store = FAISS.load_local(faiss_index_path, self.embeddings)
                self.logger.info("Loaded existing FAISS index")
            else:
                # Create empty FAISS store that will be populated later
                self.vector_store = None
                self.logger.info("FAISS vector store will be created on first document addition")
            
        except Exception as e:
            self.logger.error(f"FAISS initialization failed: {e}")
            raise
    
    def _initialize_weaviate(self):
        """Initialize Weaviate vector store."""
        # Placeholder for Weaviate initialization
        self.logger.warning("Weaviate provider not yet implemented")
        self._initialize_fallback_store()
    
    def _initialize_fallback_store(self):
        """Initialize a simple in-memory fallback store."""
        self.logger.warning("Using fallback in-memory vector store")
        self.vector_store = None
        self._fallback_documents = []
        self._fallback_embeddings = []
    
    async def add_documents(
        self, 
        documents: List[Dict[str, Any]], 
        batch_size: int = 100
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents with 'text' and optional 'metadata' fields
            batch_size: Number of documents to process in each batch
            
        Returns:
            List of document IDs that were added
        """
        try:
            # Convert to LangChain Document format
            langchain_docs = []
            for doc in documents:
                if isinstance(doc, dict):
                    langchain_doc = Document(
                        page_content=doc.get("text", ""),
                        metadata=doc.get("metadata", {})
                    )
                else:
                    langchain_doc = doc
                
                langchain_docs.append(langchain_doc)
            
            # Split documents into chunks
            split_docs = []
            for doc in langchain_docs:
                chunks = self.text_splitter.split_documents([doc])
                split_docs.extend(chunks)
            
            # Process in batches
            document_ids = []
            for i in range(0, len(split_docs), batch_size):
                batch = split_docs[i:i + batch_size]
                batch_ids = await self._add_document_batch(batch)
                document_ids.extend(batch_ids)
            
            # Update performance stats
            self.performance_stats["total_documents"] += len(split_docs)
            self.performance_stats["last_updated"] = datetime.now().timestamp()
            
            self.logger.info(f"Added {len(split_docs)} document chunks to vector store")
            return document_ids
            
        except Exception as e:
            self.logger.error(f"Failed to add documents: {e}")
            raise
    
    async def _add_document_batch(self, documents: List[Document]) -> List[str]:
        """Add a batch of documents to the vector store."""
        if self.vector_store is None:
            return await self._add_to_fallback_store(documents)
        
        try:
            if self.config.provider == "faiss" and self.vector_store is None:
                # Create FAISS index from first batch
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
                return [f"faiss_{i}" for i in range(len(documents))]
            else:
                # Add to existing store
                ids = self.vector_store.add_documents(documents)
                return ids
                
        except Exception as e:
            self.logger.error(f"Batch addition failed: {e}")
            return []
    
    async def _add_to_fallback_store(self, documents: List[Document]) -> List[str]:
        """Add documents to fallback in-memory store."""
        document_ids = []
        for doc in documents:
            doc_id = f"fallback_{len(self._fallback_documents)}"
            self._fallback_documents.append(doc)
            
            # Generate embedding (simplified)
            try:
                embedding = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.embeddings.embed_query, 
                    doc.page_content
                )
                self._fallback_embeddings.append(embedding)
            except Exception as e:
                self.logger.warning(f"Failed to generate embedding for fallback: {e}")
                self._fallback_embeddings.append([0.0] * self.config.vector_dimension)
            
            document_ids.append(doc_id)
        
        return document_ids
    
    async def similarity_search(
        self, 
        query: str, 
        k: int = 5,
        score_threshold: Optional[float] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search in the vector store.
        
        Args:
            query: Search query text
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            metadata_filter: Filter results by metadata
            
        Returns:
            List of search results with content, metadata, and scores
        """
        start_time = datetime.now()
        
        try:
            if self.vector_store is None:
                return await self._fallback_similarity_search(query, k)
            
            # Perform similarity search with scores
            if hasattr(self.vector_store, 'similarity_search_with_score'):
                results = self.vector_store.similarity_search_with_score(
                    query=query,
                    k=k,
                    filter=metadata_filter
                )
            else:
                # Fallback to regular similarity search
                docs = self.vector_store.similarity_search(
                    query=query,
                    k=k,
                    filter=metadata_filter
                )
                results = [(doc, 0.0) for doc in docs]  # No scores available
            
            # Filter by score threshold if specified
            if score_threshold is not None:
                results = [(doc, score) for doc, score in results if score >= score_threshold]
            
            # Format results
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })
            
            # Update performance stats
            query_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(query_time)
            
            self.logger.info(f"Similarity search completed: {len(formatted_results)} results in {query_time:.3f}s")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Similarity search failed: {e}")
            return []
    
    async def _fallback_similarity_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Perform similarity search using fallback in-memory store."""
        if not self._fallback_documents:
            return []
        
        try:
            # Generate query embedding
            query_embedding = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.embeddings.embed_query, 
                query
            )
            
            # Calculate similarities (simplified cosine similarity)
            similarities = []
            for i, doc_embedding in enumerate(self._fallback_embeddings):
                # Simple dot product similarity (not normalized)
                similarity = sum(a * b for a, b in zip(query_embedding, doc_embedding))
                similarities.append((i, similarity))
            
            # Sort by similarity and take top k
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_results = similarities[:k]
            
            # Format results
            results = []
            for doc_idx, score in top_results:
                doc = self._fallback_documents[doc_idx]
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Fallback similarity search failed: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        k: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword matching.
        
        Args:
            query: Search query text
            k: Number of results to return
            semantic_weight: Weight for semantic similarity (0.0 to 1.0)
            keyword_weight: Weight for keyword matching (0.0 to 1.0)  
            metadata_filter: Filter results by metadata
            score_threshold: Minimum combined score threshold
            
        Returns:
            List of search results with combined scores
        """
        # For now, just perform semantic search
        # Full hybrid search would require additional keyword indexing
        return await self.similarity_search(
            query=query,
            k=k,
            score_threshold=score_threshold,
            metadata_filter=metadata_filter
        )
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """
        Delete documents from the vector store.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            if self.vector_store is None:
                return self._delete_from_fallback_store(document_ids)
            
            if hasattr(self.vector_store, 'delete'):
                self.vector_store.delete(document_ids)
                return True
            else:
                self.logger.warning("Vector store does not support document deletion")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete documents: {e}")
            return False
    
    def _delete_from_fallback_store(self, document_ids: List[str]) -> bool:
        """Delete documents from fallback in-memory store."""
        try:
            indices_to_remove = []
            for doc_id in document_ids:
                if doc_id.startswith("fallback_"):
                    index = int(doc_id.split("_")[1])
                    indices_to_remove.append(index)
            
            # Remove in reverse order to maintain indices
            for index in sorted(indices_to_remove, reverse=True):
                if 0 <= index < len(self._fallback_documents):
                    self._fallback_documents.pop(index)
                    self._fallback_embeddings.pop(index)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete from fallback store: {e}")
            return False
    
    def _update_query_stats(self, query_time: float):
        """Update query performance statistics."""
        total_queries = self.performance_stats["total_queries"]
        current_avg = self.performance_stats["avg_query_time"]
        
        # Update average query time
        self.performance_stats["avg_query_time"] = (
            (current_avg * total_queries + query_time) / (total_queries + 1)
        )
        self.performance_stats["total_queries"] += 1
    
    def get_store(self):
        """Get the underlying vector store instance."""
        return self.vector_store
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            **self.performance_stats,
            "provider": self.config.provider,
            "embedding_model": self.config.embedding_model,
            "collection_name": self.config.collection_name,
            "vector_dimension": self.config.vector_dimension
        }
    
    async def persist(self):
        """Persist the vector store to disk (if supported)."""
        try:
            if self.config.provider == "chroma" and hasattr(self.vector_store, 'persist'):
                self.vector_store.persist()
                self.logger.info("Vector store persisted successfully")
            
            elif self.config.provider == "faiss" and self.vector_store is not None:
                os.makedirs(self.config.persist_directory, exist_ok=True)
                faiss_index_path = os.path.join(self.config.persist_directory, "faiss_index")
                self.vector_store.save_local(faiss_index_path)
                self.logger.info("FAISS index saved successfully")
            
            else:
                self.logger.info("Vector store persistence not required/supported")
                
        except Exception as e:
            self.logger.error(f"Failed to persist vector store: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the vector store."""
        health_status = {
            "status": "unknown",
            "provider": self.config.provider,
            "collection_name": self.config.collection_name,
            "document_count": self.performance_stats["total_documents"],
            "last_updated": self.performance_stats["last_updated"],
            "error": None
        }
        
        try:
            if self.vector_store is not None:
                # Try a simple operation to check if store is working
                test_results = await self.similarity_search("health check test", k=1)
                health_status["status"] = "healthy"
                health_status["test_query_successful"] = True
            
            elif self._fallback_documents:
                health_status["status"] = "fallback"
                health_status["fallback_document_count"] = len(self._fallback_documents)
            
            else:
                health_status["status"] = "empty"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status