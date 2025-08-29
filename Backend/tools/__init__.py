"""
LangChain Tools for Weev Platform External Integrations

This module provides LangChain-compatible tool implementations that enable AI agents
to interact with external systems, databases, APIs, and custom functions within the
Weev workflow platform.

Tool Categories:
===============

1. **Web Tools**: Internet search, web scraping, URL fetching
2. **Database Tools**: SQL queries, vector database operations, data retrieval
3. **API Tools**: REST API calls, GraphQL queries, webhook triggers  
4. **File Tools**: File operations, document processing, data transformation
5. **Computation Tools**: Mathematical calculations, data analysis, formatting
6. **Integration Tools**: Third-party service integrations (Slack, email, etc.)

Architecture:
============

All tools follow LangChain's BaseTool interface while integrating with Weev's
existing infrastructure:

1. **Tool Registration**: Automatic discovery and registration in ToolRegistry
2. **Permission System**: Role-based access control for sensitive operations
3. **Rate Limiting**: Built-in rate limiting for external API calls
4. **Error Handling**: Comprehensive error handling with retry mechanisms
5. **Logging**: Detailed execution logging for debugging and monitoring
6. **Streaming**: Support for streaming results in real-time

Tool Implementation Pattern:
===========================

Each tool follows this structure:

```python
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field

class CustomToolInput(BaseModel):
    """Input schema for the custom tool."""
    query: str = Field(..., description="The query to process")
    options: Optional[dict] = Field(None, description="Additional options")

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "Description of what the tool does"
    args_schema: Type[BaseModel] = CustomToolInput
    
    async def _arun(self, query: str, options: Optional[dict] = None) -> str:
        # Tool implementation
        return result
```

Security Considerations:
=======================

1. **Input Validation**: All tool inputs are validated using Pydantic models
2. **Sanitization**: User inputs are sanitized to prevent injection attacks
3. **API Key Management**: Secure handling of API keys and credentials
4. **Access Control**: Permission-based tool access
5. **Audit Trail**: Complete logging of tool executions

Integration with Workflow Memory:
================================

Tools can access and update workflow memory:

```python
class DatabaseTool(BaseTool):
    def __init__(self, workflow_memory):
        super().__init__()
        self.workflow_memory = workflow_memory
    
    async def _arun(self, query: str) -> str:
        # Access previous context
        context = self.workflow_memory.get_relevant_context()
        
        # Perform database operation
        result = await self.execute_query(query, context)
        
        # Update memory with results
        self.workflow_memory.global_context.update({
            "last_db_query": query,
            "last_db_result": result
        })
        
        return result
```

Usage in Agents:
===============

Tools are automatically available to LangChain agents:

```python
from tools import WebSearchTool, DatabaseTool
from langchain_integration.nodes import AgentExecutorNode

# Create tools
tools = [
    WebSearchTool(),
    DatabaseTool(connection=db_connection),
]

# Create agent with tools
agent_node = AgentExecutorNode(
    node_id="agent_1",
    name="Research Agent", 
    tools=tools
)
```
"""

from .web_search_tool import WebSearchTool
from .database_tool import DatabaseTool
from .api_calling_tool import APICallingTool
from .custom_function_tool import CustomFunctionTool

__all__ = [
    "WebSearchTool",
    "DatabaseTool",
    "APICallingTool", 
    "CustomFunctionTool"
]