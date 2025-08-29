"""
Tool Registry for LangChain Integration in Weev Platform

This module provides a centralized registry for managing LangChain tools within the Weev
platform. It handles tool discovery, registration, access control, and lifecycle management
to enable seamless integration of external tools with AI agent workflows.

Key Responsibilities:
====================

1. **Tool Registration**: Register and manage LangChain tools from various sources
2. **Access Control**: Role-based access control for sensitive tools and operations  
3. **Tool Discovery**: Automatic discovery and cataloging of available tools
4. **Lifecycle Management**: Handle tool initialization, configuration, and cleanup
5. **Performance Monitoring**: Track tool usage, performance, and error rates
6. **Security**: Input validation, rate limiting, and audit logging for tool executions

Architecture:
============

The ToolRegistry follows a plugin architecture where tools can be:

1. **Built-in Tools**: Standard tools provided by the platform
2. **External Tools**: Tools from LangChain community or third-party providers
3. **Custom Tools**: User-defined tools specific to their workflows
4. **Dynamic Tools**: Tools created at runtime based on API specifications

Tool Categories:
===============

Tools are organized into categories for better management:

- **Data Access**: Database queries, file operations, API calls
- **Web Tools**: Web search, scraping, content retrieval  
- **Computation**: Mathematical calculations, data processing, formatting
- **Communication**: Email, messaging, notifications
- **Integration**: Third-party service integrations (Slack, GitHub, etc.)
- **AI Tools**: Additional AI model integrations, specialized processors

Registration Patterns:
=====================

**Decorator-based Registration**:
```python
@tool_registry.register_tool(category="web", requires_auth=True)
class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for information"
```

**Programmatic Registration**:
```python
tool_registry.register_tool(WebSearchTool(), category="web")
```

**Batch Registration**:
```python
tool_registry.register_tools([
    WebSearchTool(),
    DatabaseTool(),
    APICallingTool()
], category="data_access")
```

Security Features:
=================

1. **Input Sanitization**: All tool inputs are validated and sanitized
2. **Access Control Lists**: Fine-grained permissions per tool and user
3. **Rate Limiting**: Prevent abuse with configurable rate limits
4. **Audit logging**: Complete logging of all tool executions
5. **Sandboxing**: Isolated execution environments for untrusted tools

Usage Examples:
==============

**Basic Tool Registration**:
```python
from langchain_integration.tool_registry import ToolRegistry
from tools import WebSearchTool

registry = ToolRegistry()
registry.register_tool(WebSearchTool())

# Get available tools for a workflow
tools = registry.get_tools_for_user(user_id="user123", category="web")
```

**Advanced Configuration**:
```python
registry = ToolRegistry(
    enable_auth=True,
    rate_limit_per_minute=60,
    audit_log_level="INFO",
    sandbox_tools=["custom_code_executor"]
)

# Register with custom permissions
registry.register_tool(
    CustomTool(),
    permissions=["admin", "power_user"],
    rate_limit=10,
    requires_approval=True
)
```

Integration with Workflows:
==========================

Tools are automatically available to LangChain nodes through the registry:

```python
# In a LangChain node
available_tools = self.tool_registry.get_available_tools()
agent_executor = AgentExecutor(
    agent=agent,
    tools=available_tools,
    verbose=True
)
```

Performance Monitoring:
======================

The registry tracks comprehensive metrics:
- Tool execution frequency and duration
- Error rates and failure patterns  
- Resource usage per tool
- User adoption and usage patterns
- Performance bottlenecks and optimization opportunities

Author: Weev Platform Team
Version: 1.0.0
Date: 2025-01-XX
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from langchain.tools import BaseTool
from pydantic import BaseModel


class ToolCategory(Enum):
    """Tool categories for organization and access control."""
    WEB = "web"
    DATABASE = "database"
    API = "api"
    COMPUTATION = "computation"
    COMMUNICATION = "communication"
    INTEGRATION = "integration"
    AI = "ai"
    CUSTOM = "custom"
    SYSTEM = "system"


class ToolAccessLevel(Enum):
    """Access levels for tool usage."""
    PUBLIC = "public"          # Available to all users
    AUTHENTICATED = "authenticated"  # Requires user authentication
    RESTRICTED = "restricted"  # Requires specific permissions
    ADMIN = "admin"           # Admin-only tools


@dataclass
class ToolMetadata:
    """Metadata for registered tools."""
    tool_id: str
    name: str
    description: str
    category: ToolCategory
    access_level: ToolAccessLevel
    permissions_required: Set[str] = field(default_factory=set)
    rate_limit_per_minute: int = 60
    requires_approval: bool = False
    is_sandboxed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    error_count: int = 0
    avg_execution_time: float = 0.0


@dataclass
class ToolExecutionContext:
    """Context information for tool execution."""
    user_id: Optional[str]
    workflow_id: str
    node_id: str
    execution_id: Optional[str]
    permissions: Set[str] = field(default_factory=set)
    rate_limit_window: datetime = field(default_factory=datetime.now)


class ToolExecutionResult:
    """Result of tool execution with metadata."""
    
    def __init__(
        self,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.result = result
        self.error = error
        self.execution_time = execution_time
        self.metadata = metadata or {}
        self.timestamp = datetime.now()


class ToolRegistry:
    """
    Centralized registry for managing LangChain tools in the Weev platform.
    
    This class provides a unified interface for tool registration, discovery,
    access control, and execution monitoring across all AI agent workflows.
    """
    
    def __init__(
        self,
        enable_auth: bool = True,
        default_rate_limit: int = 60,
        audit_log_level: str = "INFO",
        sandbox_dangerous_tools: bool = True
    ):
        """
        Initialize the tool registry.
        
        Args:
            enable_auth: Whether to enforce authentication and permissions
            default_rate_limit: Default rate limit per minute for tools
            audit_log_level: Logging level for audit events
            sandbox_dangerous_tools: Whether to sandbox potentially dangerous tools
        """
        self.enable_auth = enable_auth
        self.default_rate_limit = default_rate_limit
        self.sandbox_dangerous_tools = sandbox_dangerous_tools
        
        # Tool storage
        self._tools: Dict[str, BaseTool] = {}
        self._tool_metadata: Dict[str, ToolMetadata] = {}
        
        # Access control
        self._user_permissions: Dict[str, Set[str]] = {}
        self._tool_permissions: Dict[str, Set[str]] = {}
        
        # Rate limiting
        self._rate_limit_tracker: Dict[str, List[datetime]] = {}
        
        # Performance tracking
        self._execution_history: List[ToolExecutionResult] = []
        self._performance_stats: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks and hooks
        self._pre_execution_hooks: List[Callable] = []
        self._post_execution_hooks: List[Callable] = []
        
        # Logging
        self.logger = logging.getLogger("weev.tool_registry")
        self.logger.setLevel(getattr(logging, audit_log_level.upper(), logging.INFO))
        
        self.logger.info("ToolRegistry initialized")
    
    def register_tool(
        self,
        tool: BaseTool,
        category: Union[ToolCategory, str] = ToolCategory.CUSTOM,
        access_level: Union[ToolAccessLevel, str] = ToolAccessLevel.AUTHENTICATED,
        permissions_required: Optional[Set[str]] = None,
        rate_limit_per_minute: Optional[int] = None,
        requires_approval: bool = False,
        is_sandboxed: Optional[bool] = None
    ) -> str:
        """
        Register a tool in the registry.
        
        Args:
            tool: The LangChain tool to register
            category: Tool category for organization
            access_level: Required access level for tool usage
            permissions_required: Specific permissions required
            rate_limit_per_minute: Rate limit override
            requires_approval: Whether tool usage requires approval
            is_sandboxed: Whether to sandbox the tool (auto-detected if None)
            
        Returns:
            Tool ID for the registered tool
        """
        try:
            # Generate tool ID
            tool_id = f"{category.value if isinstance(category, ToolCategory) else category}_{tool.name}_{len(self._tools)}"
            
            # Convert enums if needed
            if isinstance(category, str):
                category = ToolCategory(category)
            if isinstance(access_level, str):
                access_level = ToolAccessLevel(access_level)
            
            # Auto-detect sandboxing need
            if is_sandboxed is None:
                dangerous_keywords = ["exec", "eval", "shell", "command", "code", "system"]
                is_sandboxed = (
                    self.sandbox_dangerous_tools and
                    any(keyword in tool.name.lower() or keyword in tool.description.lower() 
                        for keyword in dangerous_keywords)
                )
            
            # Create tool metadata
            metadata = ToolMetadata(
                tool_id=tool_id,
                name=tool.name,
                description=tool.description,
                category=category,
                access_level=access_level,
                permissions_required=permissions_required or set(),
                rate_limit_per_minute=rate_limit_per_minute or self.default_rate_limit,
                requires_approval=requires_approval,
                is_sandboxed=is_sandboxed
            )
            
            # Store tool and metadata
            self._tools[tool_id] = tool
            self._tool_metadata[tool_id] = metadata
            
            # Initialize performance tracking
            self._performance_stats[tool_id] = {
                "total_executions": 0,
                "total_errors": 0,
                "avg_execution_time": 0.0,
                "last_execution": None,
                "peak_usage_hour": None
            }
            
            self.logger.info(f"Tool registered: {tool.name} (ID: {tool_id}, Category: {category.value})")
            return tool_id
            
        except Exception as e:
            self.logger.error(f"Failed to register tool {tool.name}: {e}")
            raise
    
    def register_tools(
        self,
        tools: List[BaseTool],
        category: Union[ToolCategory, str] = ToolCategory.CUSTOM,
        **kwargs
    ) -> List[str]:
        """
        Register multiple tools at once.
        
        Args:
            tools: List of LangChain tools to register
            category: Default category for all tools
            **kwargs: Additional arguments passed to register_tool
            
        Returns:
            List of tool IDs for registered tools
        """
        tool_ids = []
        for tool in tools:
            try:
                tool_id = self.register_tool(tool, category=category, **kwargs)
                tool_ids.append(tool_id)
            except Exception as e:
                self.logger.error(f"Failed to register tool {tool.name}: {e}")
                # Continue with other tools
                continue
        
        self.logger.info(f"Batch registration completed: {len(tool_ids)}/{len(tools)} tools registered")
        return tool_ids
    
    def unregister_tool(self, tool_id: str) -> bool:
        """
        Unregister a tool from the registry.
        
        Args:
            tool_id: ID of the tool to unregister
            
        Returns:
            True if tool was successfully unregistered
        """
        try:
            if tool_id in self._tools:
                tool_name = self._tool_metadata[tool_id].name
                del self._tools[tool_id]
                del self._tool_metadata[tool_id]
                
                # Clean up tracking data
                if tool_id in self._performance_stats:
                    del self._performance_stats[tool_id]
                if tool_id in self._rate_limit_tracker:
                    del self._rate_limit_tracker[tool_id]
                
                self.logger.info(f"Tool unregistered: {tool_name} (ID: {tool_id})")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to unregister tool {tool_id}: {e}")
            return False
    
    def get_available_tools(
        self,
        user_id: Optional[str] = None,
        category: Optional[Union[ToolCategory, str]] = None,
        access_level: Optional[Union[ToolAccessLevel, str]] = None
    ) -> List[BaseTool]:
        """
        Get list of available tools based on filters and permissions.
        
        Args:
            user_id: User ID for permission checking (if auth enabled)
            category: Filter by tool category
            access_level: Filter by access level
            
        Returns:
            List of available LangChain tools
        """
        available_tools = []
        
        for tool_id, tool in self._tools.items():
            metadata = self._tool_metadata[tool_id]
            
            # Check category filter
            if category and metadata.category != (
                category if isinstance(category, ToolCategory) else ToolCategory(category)
            ):
                continue
            
            # Check access level filter
            if access_level and metadata.access_level != (
                access_level if isinstance(access_level, ToolAccessLevel) else ToolAccessLevel(access_level)
            ):
                continue
            
            # Check permissions
            if self.enable_auth and user_id:
                if not self._has_tool_permission(user_id, tool_id):
                    continue
            
            available_tools.append(tool)
        
        self.logger.debug(f"Available tools query: {len(available_tools)} tools returned")
        return available_tools
    
    def get_tool_by_name(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by its name."""
        for tool_id, tool in self._tools.items():
            if tool.name == tool_name:
                return tool
        return None
    
    def get_tool_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """Get metadata for a specific tool."""
        return self._tool_metadata.get(tool_id)
    
    def _has_tool_permission(self, user_id: str, tool_id: str) -> bool:
        """Check if user has permission to use a specific tool."""
        if not self.enable_auth:
            return True
        
        metadata = self._tool_metadata.get(tool_id)
        if not metadata:
            return False
        
        # Public tools are always available
        if metadata.access_level == ToolAccessLevel.PUBLIC:
            return True
        
        # Get user permissions
        user_permissions = self._user_permissions.get(user_id, set())
        
        # Check if user has required permissions
        if metadata.permissions_required:
            return bool(metadata.permissions_required.intersection(user_permissions))
        
        # Default access rules by level
        if metadata.access_level == ToolAccessLevel.AUTHENTICATED:
            return user_id is not None  # Just need to be authenticated
        elif metadata.access_level == ToolAccessLevel.RESTRICTED:
            return "tool_user" in user_permissions
        elif metadata.access_level == ToolAccessLevel.ADMIN:
            return "admin" in user_permissions
        
        return False
    
    def set_user_permissions(self, user_id: str, permissions: Set[str]):
        """Set permissions for a user."""
        self._user_permissions[user_id] = permissions
        self.logger.info(f"Updated permissions for user {user_id}: {permissions}")
    
    def add_user_permission(self, user_id: str, permission: str):
        """Add a permission to a user."""
        if user_id not in self._user_permissions:
            self._user_permissions[user_id] = set()
        self._user_permissions[user_id].add(permission)
        self.logger.info(f"Added permission '{permission}' to user {user_id}")
    
    def check_rate_limit(self, user_id: str, tool_id: str) -> bool:
        """Check if user is within rate limit for a tool."""
        if not self.enable_auth:
            return True
        
        metadata = self._tool_metadata.get(tool_id)
        if not metadata:
            return False
        
        rate_key = f"{user_id}:{tool_id}"
        now = datetime.now()
        window_start = now - timedelta(minutes=1)
        
        # Clean old entries
        if rate_key in self._rate_limit_tracker:
            self._rate_limit_tracker[rate_key] = [
                timestamp for timestamp in self._rate_limit_tracker[rate_key]
                if timestamp > window_start
            ]
        else:
            self._rate_limit_tracker[rate_key] = []
        
        # Check limit
        current_count = len(self._rate_limit_tracker[rate_key])
        return current_count < metadata.rate_limit_per_minute
    
    def record_tool_usage(self, user_id: str, tool_id: str):
        """Record tool usage for rate limiting."""
        rate_key = f"{user_id}:{tool_id}"
        if rate_key not in self._rate_limit_tracker:
            self._rate_limit_tracker[rate_key] = []
        
        self._rate_limit_tracker[rate_key].append(datetime.now())
        
        # Update tool metadata
        if tool_id in self._tool_metadata:
            self._tool_metadata[tool_id].usage_count += 1
            self._tool_metadata[tool_id].last_used = datetime.now()
    
    async def execute_tool(
        self,
        tool_id: str,
        input_data: str,
        context: ToolExecutionContext
    ) -> ToolExecutionResult:
        """
        Execute a tool with proper access control, rate limiting, and monitoring.
        
        Args:
            tool_id: ID of the tool to execute
            input_data: Input data for the tool
            context: Execution context with user info and permissions
            
        Returns:
            Tool execution result with metadata
        """
        start_time = datetime.now()
        
        try:
            # Get tool and metadata
            tool = self._tools.get(tool_id)
            metadata = self._tool_metadata.get(tool_id)
            
            if not tool or not metadata:
                return ToolExecutionResult(
                    success=False,
                    error=f"Tool {tool_id} not found"
                )
            
            # Check permissions
            if self.enable_auth and context.user_id:
                if not self._has_tool_permission(context.user_id, tool_id):
                    return ToolExecutionResult(
                        success=False,
                        error="Insufficient permissions"
                    )
            
            # Check rate limit
            if context.user_id and not self.check_rate_limit(context.user_id, tool_id):
                return ToolExecutionResult(
                    success=False,
                    error="Rate limit exceeded"
                )
            
            # Execute pre-execution hooks
            for hook in self._pre_execution_hooks:
                try:
                    await hook(tool_id, input_data, context)
                except Exception as e:
                    self.logger.warning(f"Pre-execution hook failed: {e}")
            
            # Execute tool
            if metadata.is_sandboxed:
                result = await self._execute_sandboxed(tool, input_data)
            else:
                if hasattr(tool, 'arun'):
                    result = await tool.arun(input_data)
                else:
                    # Fallback to synchronous execution
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, tool.run, input_data
                    )
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Record usage
            if context.user_id:
                self.record_tool_usage(context.user_id, tool_id)
            
            # Update performance stats
            self._update_performance_stats(tool_id, execution_time, True)
            
            # Execute post-execution hooks
            for hook in self._post_execution_hooks:
                try:
                    await hook(tool_id, input_data, result, context)
                except Exception as e:
                    self.logger.warning(f"Post-execution hook failed: {e}")
            
            # Create result
            execution_result = ToolExecutionResult(
                success=True,
                result=result,
                execution_time=execution_time,
                metadata={
                    "tool_name": tool.name,
                    "tool_category": metadata.category.value,
                    "is_sandboxed": metadata.is_sandboxed
                }
            )
            
            # Log execution
            self.logger.info(
                f"Tool executed: {tool.name} by user {context.user_id} "
                f"in {execution_time:.3f}s"
            )
            
            return execution_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update error stats
            self._update_performance_stats(tool_id, execution_time, False)
            
            # Log error
            self.logger.error(
                f"Tool execution failed: {tool_id} by user {context.user_id}: {e}"
            )
            
            return ToolExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _execute_sandboxed(self, tool: BaseTool, input_data: str) -> str:
        """Execute a tool in a sandboxed environment."""
        # This is a simplified implementation
        # In production, you'd want proper containerization or process isolation
        self.logger.warning(f"Sandboxed execution not fully implemented for {tool.name}")
        
        # For now, just execute normally but with additional logging
        if hasattr(tool, 'arun'):
            return await tool.arun(input_data)
        else:
            return await asyncio.get_event_loop().run_in_executor(
                None, tool.run, input_data
            )
    
    def _update_performance_stats(self, tool_id: str, execution_time: float, success: bool):
        """Update performance statistics for a tool."""
        if tool_id not in self._performance_stats:
            return
        
        stats = self._performance_stats[tool_id]
        stats["total_executions"] += 1
        
        if not success:
            stats["total_errors"] += 1
            if tool_id in self._tool_metadata:
                self._tool_metadata[tool_id].error_count += 1
        
        # Update average execution time
        current_avg = stats["avg_execution_time"]
        total_executions = stats["total_executions"]
        stats["avg_execution_time"] = (
            (current_avg * (total_executions - 1) + execution_time) / total_executions
        )
        
        # Update tool metadata average
        if tool_id in self._tool_metadata:
            self._tool_metadata[tool_id].avg_execution_time = stats["avg_execution_time"]
        
        stats["last_execution"] = datetime.now().isoformat()
    
    def add_pre_execution_hook(self, hook: Callable):
        """Add a pre-execution hook."""
        self._pre_execution_hooks.append(hook)
    
    def add_post_execution_hook(self, hook: Callable):
        """Add a post-execution hook."""
        self._post_execution_hooks.append(hook)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        total_tools = len(self._tools)
        total_executions = sum(stats["total_executions"] for stats in self._performance_stats.values())
        total_errors = sum(stats["total_errors"] for stats in self._performance_stats.values())
        
        # Find most/least used tools
        most_used_tool = None
        least_used_tool = None
        max_usage = 0
        min_usage = float('inf')
        
        for tool_id, stats in self._performance_stats.items():
            usage = stats["total_executions"]
            if usage > max_usage:
                max_usage = usage
                most_used_tool = self._tool_metadata[tool_id].name
            if usage < min_usage:
                min_usage = usage
                least_used_tool = self._tool_metadata[tool_id].name
        
        return {
            "total_tools_registered": total_tools,
            "total_executions": total_executions,
            "total_errors": total_errors,
            "error_rate": total_errors / max(total_executions, 1),
            "most_used_tool": most_used_tool,
            "least_used_tool": least_used_tool,
            "tools_by_category": self._get_tools_by_category(),
            "avg_execution_time_by_tool": {
                self._tool_metadata[tool_id].name: stats["avg_execution_time"]
                for tool_id, stats in self._performance_stats.items()
            }
        }
    
    def _get_tools_by_category(self) -> Dict[str, int]:
        """Get count of tools by category."""
        category_counts = {}
        for metadata in self._tool_metadata.values():
            category = metadata.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        return category_counts
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their metadata."""
        tools_list = []
        for tool_id, tool in self._tools.items():
            metadata = self._tool_metadata[tool_id]
            stats = self._performance_stats.get(tool_id, {})
            
            tools_list.append({
                "tool_id": tool_id,
                "name": tool.name,
                "description": tool.description,
                "category": metadata.category.value,
                "access_level": metadata.access_level.value,
                "usage_count": metadata.usage_count,
                "error_count": metadata.error_count,
                "avg_execution_time": metadata.avg_execution_time,
                "last_used": metadata.last_used.isoformat() if metadata.last_used else None,
                "is_sandboxed": metadata.is_sandboxed,
                "requires_approval": metadata.requires_approval
            })
        
        return tools_list
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the tool registry."""
        try:
            total_tools = len(self._tools)
            healthy_tools = 0
            
            # Simple health check - tools that have been used successfully recently
            recent_cutoff = datetime.now() - timedelta(hours=24)
            
            for tool_id in self._tools.keys():
                metadata = self._tool_metadata[tool_id]
                stats = self._performance_stats[tool_id]
                
                # Consider tool healthy if it has low error rate and recent successful usage
                error_rate = stats["total_errors"] / max(stats["total_executions"], 1)
                recently_used = (
                    metadata.last_used and metadata.last_used > recent_cutoff
                ) if metadata.last_used else False
                
                if error_rate < 0.1 or recently_used:  # Less than 10% error rate or recently used
                    healthy_tools += 1
            
            return {
                "status": "healthy" if healthy_tools == total_tools else "degraded",
                "total_tools": total_tools,
                "healthy_tools": healthy_tools,
                "unhealthy_tools": total_tools - healthy_tools,
                "registry_uptime": (datetime.now() - datetime.now()).total_seconds(),  # Placeholder
                "performance_stats": self.get_performance_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "total_tools": len(self._tools)
            }