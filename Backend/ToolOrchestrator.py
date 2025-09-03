"""
Tool Orchestrator

Manages intelligent tool selection and execution based on BrainNode decisions.
Provides dynamic tool orchestration, dependency management, and execution optimization.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ToolExecutionStatus(Enum):
    """Status of tool execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success" 
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class ToolPriority(Enum):
    """Priority levels for tool execution"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class ToolCapability:
    """Definition of a tool's capabilities"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    execution_time_estimate: float = 1.0  # seconds
    reliability_score: float = 0.95  # 0.0 to 1.0
    cost_score: float = 0.1  # relative cost metric
    supported_actions: List[str] = field(default_factory=list)


@dataclass
class ToolExecutionPlan:
    """Plan for executing a sequence of tools"""
    execution_id: str
    tools: List[str]
    parameters: Dict[str, Any]
    execution_order: List[str]
    estimated_duration: float
    dependencies: Dict[str, List[str]]
    parallel_groups: List[List[str]]
    priority: ToolPriority = ToolPriority.MEDIUM


@dataclass 
class ToolExecutionResult:
    """Result of tool execution"""
    tool_name: str
    status: ToolExecutionStatus
    result_data: Any
    execution_time: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class ToolOrchestrator:
    """
    Manages intelligent tool selection and execution based on AI brain decisions.
    
    Features:
    - Intelligent tool selection based on context and capabilities
    - Dynamic execution planning with dependency resolution
    - Parallel execution optimization
    - Error handling and retry logic
    - Performance monitoring and optimization
    """
    
    def __init__(self, available_tools: Dict[str, Any]):
        self.available_tools = available_tools
        self.tool_capabilities = self._build_capability_registry()
        self.execution_history = []
        self.performance_metrics = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configuration
        self.max_parallel_tools = 5
        self.default_timeout = 30.0  # seconds
        self.retry_attempts = 3
        self.enable_parallel_execution = True

    def _build_capability_registry(self) -> Dict[str, ToolCapability]:
        """Build registry of tool capabilities from available tools"""
        capabilities = {}
        
        # Define capabilities for standard tools
        tool_definitions = {
            'web_search': ToolCapability(
                name='web_search',
                description='Search the web for information using various search engines',
                input_schema={'query': str, 'max_results': int, 'search_type': str},
                output_schema={'results': list, 'total_found': int},
                execution_time_estimate=3.0,
                reliability_score=0.95,
                cost_score=0.2,
                supported_actions=['search', 'deep_search', 'news_search']
            ),
            'email': ToolCapability(
                name='email',
                description='Email operations including sending, reading, and managing emails',
                input_schema={'action': str, 'to': list, 'subject': str, 'body': str},
                output_schema={'status': str, 'message_id': str},
                execution_time_estimate=2.0,
                reliability_score=0.98,
                cost_score=0.1,
                supported_actions=['draft', 'send', 'search', 'read']
            ),
            'slack': ToolCapability(
                name='slack',
                description='Slack messaging and channel management',
                input_schema={'action': str, 'channel': str, 'message': str},
                output_schema={'status': str, 'message_ts': str},
                execution_time_estimate=1.5,
                reliability_score=0.97,
                cost_score=0.05,
                supported_actions=['post_message', 'fetch_history', 'reply_thread']
            ),
            'calendar': ToolCapability(
                name='calendar',
                description='Calendar event management and scheduling',
                input_schema={'action': str, 'title': str, 'start': str, 'duration': int},
                output_schema={'status': str, 'event_id': str},
                execution_time_estimate=2.5,
                reliability_score=0.96,
                cost_score=0.15,
                supported_actions=['create_event', 'find_free_slots', 'list_events']
            ),
            'notion': ToolCapability(
                name='notion',
                description='Notion workspace and database management',
                input_schema={'action': str, 'page_id': str, 'content': dict},
                output_schema={'status': str, 'page_url': str},
                execution_time_estimate=3.5,
                reliability_score=0.94,
                cost_score=0.25,
                supported_actions=['create_page', 'update_page', 'query_database']
            ),
            'github': ToolCapability(
                name='github',
                description='GitHub repository and issue management',
                input_schema={'action': str, 'repo': str, 'title': str, 'body': str},
                output_schema={'status': str, 'issue_number': int},
                execution_time_estimate=2.0,
                reliability_score=0.98,
                cost_score=0.1,
                supported_actions=['create_issue', 'summarize_pr', 'propose_changes']
            ),
            'data_analyzer': ToolCapability(
                name='data_analyzer',
                description='Data analysis and visualization tools',
                input_schema={'action': str, 'data': dict, 'analysis_type': str},
                output_schema={'analysis': dict, 'visualization': str},
                execution_time_estimate=10.0,
                reliability_score=0.92,
                cost_score=0.8,
                supported_actions=['analyze', 'visualize', 'predict']
            )
        }
        
        # Register capabilities for available tools
        for tool_name, tool_instance in self.available_tools.items():
            if tool_name in tool_definitions:
                capabilities[tool_name] = tool_definitions[tool_name]
            else:
                # Create basic capability for unknown tools
                capabilities[tool_name] = ToolCapability(
                    name=tool_name,
                    description=f'Tool for {tool_name} operations',
                    input_schema={'action': str, 'params': dict},
                    output_schema={'result': dict},
                    supported_actions=['execute']
                )
        
        self.logger.info(f"Built capability registry for {len(capabilities)} tools")
        return capabilities

    async def create_execution_plan(self, 
                                  selected_tools: List[str],
                                  parameters: Dict[str, Any],
                                  context: Dict[str, Any]) -> ToolExecutionPlan:
        """
        Create optimized execution plan for selected tools.
        
        Args:
            selected_tools: List of tool names to execute
            parameters: Parameters for each tool
            context: Execution context and constraints
            
        Returns:
            ToolExecutionPlan with optimized execution order
        """
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.execution_history)}"
        
        # Validate selected tools
        valid_tools = [tool for tool in selected_tools if tool in self.tool_capabilities]
        invalid_tools = [tool for tool in selected_tools if tool not in self.tool_capabilities]
        
        if invalid_tools:
            self.logger.warning(f"Invalid tools requested: {invalid_tools}")
        
        if not valid_tools:
            raise ValueError("No valid tools selected for execution")
        
        # Build dependency graph
        dependencies = self._build_tool_dependencies(valid_tools, context)
        
        # Calculate execution order
        execution_order = self._calculate_execution_order(valid_tools, dependencies)
        
        # Identify parallel execution groups
        parallel_groups = self._identify_parallel_groups(execution_order, dependencies)
        
        # Estimate total duration
        estimated_duration = self._estimate_execution_duration(execution_order, parallel_groups)
        
        # Determine priority based on context
        priority = self._determine_execution_priority(context)
        
        plan = ToolExecutionPlan(
            execution_id=execution_id,
            tools=valid_tools,
            parameters=parameters,
            execution_order=execution_order,
            estimated_duration=estimated_duration,
            dependencies=dependencies,
            parallel_groups=parallel_groups,
            priority=priority
        )
        
        self.logger.info(f"Created execution plan {execution_id} for {len(valid_tools)} tools, "
                        f"estimated duration: {estimated_duration:.1f}s")
        
        return plan

    async def execute_tool_sequence(self,
                                  execution_plan: ToolExecutionPlan,
                                  workflow_context: Dict[str, Any]) -> List[ToolExecutionResult]:
        """
        Execute tools according to the execution plan.
        
        Args:
            execution_plan: Plan created by create_execution_plan
            workflow_context: Current workflow context
            
        Returns:
            List of ToolExecutionResult objects
        """
        results = []
        start_time = datetime.now().timestamp()
        
        self.logger.info(f"Starting execution plan {execution_plan.execution_id}")
        
        try:
            if self.enable_parallel_execution and execution_plan.parallel_groups:
                results = await self._execute_parallel_groups(execution_plan, workflow_context)
            else:
                results = await self._execute_sequential(execution_plan, workflow_context)
                
        except Exception as e:
            self.logger.error(f"Execution plan {execution_plan.execution_id} failed: {str(e)}")
            # Create failure result
            failure_result = ToolExecutionResult(
                tool_name="execution_plan",
                status=ToolExecutionStatus.FAILED,
                result_data=None,
                execution_time=datetime.now().timestamp() - start_time,
                error_message=str(e)
            )
            results.append(failure_result)
        
        # Update performance metrics
        self._update_performance_metrics(execution_plan, results)
        
        # Store in execution history
        self.execution_history.append({
            'plan': execution_plan,
            'results': results,
            'total_execution_time': datetime.now().timestamp() - start_time
        })
        
        return results

    async def _execute_parallel_groups(self,
                                     execution_plan: ToolExecutionPlan,
                                     workflow_context: Dict[str, Any]) -> List[ToolExecutionResult]:
        """Execute tools in parallel groups"""
        all_results = []
        accumulated_context = workflow_context.copy()
        
        for group_index, group in enumerate(execution_plan.parallel_groups):
            self.logger.info(f"Executing parallel group {group_index + 1}/{len(execution_plan.parallel_groups)}: {group}")
            
            # Execute group in parallel
            group_tasks = []
            for tool_name in group:
                task = self._execute_single_tool(tool_name, execution_plan.parameters, accumulated_context)
                group_tasks.append(task)
            
            # Wait for all tools in group to complete
            group_results = await asyncio.gather(*group_tasks, return_exceptions=True)
            
            # Process results and update context
            for i, result in enumerate(group_results):
                if isinstance(result, Exception):
                    # Handle exception
                    error_result = ToolExecutionResult(
                        tool_name=group[i],
                        status=ToolExecutionStatus.FAILED,
                        result_data=None,
                        execution_time=0,
                        error_message=str(result)
                    )
                    all_results.append(error_result)
                else:
                    all_results.append(result)
                    # Update context with successful results
                    if result.status == ToolExecutionStatus.SUCCESS:
                        accumulated_context[f'{result.tool_name}_result'] = result.result_data
        
        return all_results

    async def _execute_sequential(self,
                                execution_plan: ToolExecutionPlan,
                                workflow_context: Dict[str, Any]) -> List[ToolExecutionResult]:
        """Execute tools sequentially"""
        results = []
        accumulated_context = workflow_context.copy()
        
        for tool_name in execution_plan.execution_order:
            self.logger.info(f"Executing tool: {tool_name}")
            
            result = await self._execute_single_tool(tool_name, execution_plan.parameters, accumulated_context)
            results.append(result)
            
            # Update context with result
            if result.status == ToolExecutionStatus.SUCCESS:
                accumulated_context[f'{tool_name}_result'] = result.result_data
            
            # Stop execution if critical tool failed
            if (result.status == ToolExecutionStatus.FAILED and 
                execution_plan.priority in [ToolPriority.CRITICAL, ToolPriority.HIGH]):
                self.logger.warning(f"Critical tool {tool_name} failed, stopping execution")
                break
        
        return results

    async def _execute_single_tool(self,
                                 tool_name: str,
                                 parameters: Dict[str, Any],
                                 context: Dict[str, Any]) -> ToolExecutionResult:
        """Execute a single tool with retry logic"""
        tool_params = parameters.get(tool_name, {})
        start_time = datetime.now().timestamp()
        
        for attempt in range(self.retry_attempts):
            try:
                if tool_name not in self.available_tools:
                    raise ValueError(f"Tool {tool_name} not available")
                
                tool_instance = self.available_tools[tool_name]
                
                # Execute tool with timeout
                result_data = await asyncio.wait_for(
                    tool_instance.execute(parameters=tool_params, context=context),
                    timeout=self.default_timeout
                )
                
                # Success
                execution_time = datetime.now().timestamp() - start_time
                return ToolExecutionResult(
                    tool_name=tool_name,
                    status=ToolExecutionStatus.SUCCESS,
                    result_data=result_data,
                    execution_time=execution_time,
                    metadata={'attempt': attempt + 1}
                )
                
            except asyncio.TimeoutError:
                if attempt == self.retry_attempts - 1:
                    execution_time = datetime.now().timestamp() - start_time
                    return ToolExecutionResult(
                        tool_name=tool_name,
                        status=ToolExecutionStatus.TIMEOUT,
                        result_data=None,
                        execution_time=execution_time,
                        error_message=f"Tool execution timed out after {self.default_timeout}s",
                        metadata={'attempts': self.retry_attempts}
                    )
                
                self.logger.warning(f"Tool {tool_name} timed out, attempt {attempt + 1}/{self.retry_attempts}")
                
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    execution_time = datetime.now().timestamp() - start_time
                    return ToolExecutionResult(
                        tool_name=tool_name,
                        status=ToolExecutionStatus.FAILED,
                        result_data=None,
                        execution_time=execution_time,
                        error_message=str(e),
                        metadata={'attempts': self.retry_attempts}
                    )
                
                self.logger.warning(f"Tool {tool_name} failed, attempt {attempt + 1}/{self.retry_attempts}: {e}")
                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff

    def _build_tool_dependencies(self, tools: List[str], context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Build dependency graph for selected tools"""
        dependencies = {}
        
        for tool_name in tools:
            tool_deps = []
            
            if tool_name in self.tool_capabilities:
                # Add explicit dependencies from tool definition
                tool_deps.extend(self.tool_capabilities[tool_name].dependencies)
                
                # Infer dependencies based on context
                inferred_deps = self._infer_tool_dependencies(tool_name, tools, context)
                tool_deps.extend(inferred_deps)
            
            # Remove duplicates and self-references
            dependencies[tool_name] = list(set(dep for dep in tool_deps if dep != tool_name and dep in tools))
        
        return dependencies

    def _infer_tool_dependencies(self, tool_name: str, available_tools: List[str], context: Dict[str, Any]) -> List[str]:
        """Infer tool dependencies based on context and tool capabilities"""
        dependencies = []
        
        # Common dependency patterns
        dependency_rules = {
            'email': {
                'needs': ['web_search'],  # Often need to search before emailing
                'condition': lambda ctx: ctx.get('search_before_email', True)
            },
            'slack': {
                'needs': ['web_search'],  # May need info before posting
                'condition': lambda ctx: 'search' in str(ctx.get('user_request', '')).lower()
            },
            'notion': {
                'needs': ['web_search', 'data_analyzer'],  # May need data before documenting
                'condition': lambda ctx: ctx.get('analyze_before_document', False)
            },
            'github': {
                'needs': ['data_analyzer'],  # May need analysis before creating issues
                'condition': lambda ctx: 'analyze' in str(ctx.get('user_request', '')).lower()
            }
        }
        
        if tool_name in dependency_rules:
            rule = dependency_rules[tool_name]
            if rule['condition'](context):
                for dep in rule['needs']:
                    if dep in available_tools:
                        dependencies.append(dep)
        
        return dependencies

    def _calculate_execution_order(self, tools: List[str], dependencies: Dict[str, List[str]]) -> List[str]:
        """Calculate optimal execution order using topological sort"""
        # Build in-degree count
        in_degree = {tool: 0 for tool in tools}
        
        for tool, deps in dependencies.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[tool] += 1
        
        # Topological sort with priority consideration
        queue = [(priority, tool) for tool, priority in self._calculate_tool_priorities(tools, in_degree).items() 
                if in_degree[tool] == 0]
        queue.sort()  # Sort by priority
        
        execution_order = []
        
        while queue:
            _, current = queue.pop(0)
            execution_order.append(current)
            
            # Update in-degrees for dependent tools
            for tool in tools:
                if current in dependencies.get(tool, []):
                    in_degree[tool] -= 1
                    if in_degree[tool] == 0:
                        priority = self._calculate_tool_priorities(tools, in_degree)[tool]
                        queue.append((priority, tool))
                        queue.sort()  # Re-sort by priority
        
        return execution_order

    def _calculate_tool_priorities(self, tools: List[str], in_degree: Dict[str, int]) -> Dict[str, int]:
        """Calculate execution priorities for tools"""
        priorities = {}
        
        for tool in tools:
            priority = 0
            
            if tool in self.tool_capabilities:
                capability = self.tool_capabilities[tool]
                
                # Higher reliability = higher priority (lower number)
                priority += int((1.0 - capability.reliability_score) * 10)
                
                # Lower cost = higher priority
                priority += int(capability.cost_score * 10)
                
                # Faster execution = higher priority
                priority += int(capability.execution_time_estimate / 5)
            
            # Tools with no dependencies get higher priority
            priority += in_degree[tool] * 2
            
            priorities[tool] = priority
        
        return priorities

    def _identify_parallel_groups(self, execution_order: List[str], dependencies: Dict[str, List[str]]) -> List[List[str]]:
        """Identify groups of tools that can be executed in parallel"""
        if not self.enable_parallel_execution:
            return [[tool] for tool in execution_order]
        
        groups = []
        remaining_tools = set(execution_order)
        completed_tools = set()
        
        while remaining_tools:
            # Find tools with no pending dependencies
            ready_tools = []
            for tool in remaining_tools:
                tool_deps = set(dependencies.get(tool, []))
                if tool_deps.issubset(completed_tools):
                    ready_tools.append(tool)
            
            if not ready_tools:
                # Circular dependency or error - add remaining tools individually
                ready_tools = [next(iter(remaining_tools))]
            
            # Limit parallel group size
            parallel_group = ready_tools[:self.max_parallel_tools]
            groups.append(parallel_group)
            
            # Update sets
            for tool in parallel_group:
                remaining_tools.remove(tool)
                completed_tools.add(tool)
        
        return groups

    def _estimate_execution_duration(self, execution_order: List[str], parallel_groups: List[List[str]]) -> float:
        """Estimate total execution duration"""
        if not self.enable_parallel_execution:
            # Sequential execution
            return sum(self.tool_capabilities.get(tool, ToolCapability('', '', {}, {})).execution_time_estimate 
                      for tool in execution_order)
        
        # Parallel execution
        total_time = 0.0
        for group in parallel_groups:
            # Group time is the maximum time in the group
            group_time = max(
                self.tool_capabilities.get(tool, ToolCapability('', '', {}, {})).execution_time_estimate 
                for tool in group
            )
            total_time += group_time
        
        return total_time

    def _determine_execution_priority(self, context: Dict[str, Any]) -> ToolPriority:
        """Determine execution priority based on context"""
        user_request = str(context.get('user_request', '')).lower()
        
        # Look for priority indicators
        if any(word in user_request for word in ['urgent', 'asap', 'critical', 'emergency']):
            return ToolPriority.CRITICAL
        elif any(word in user_request for word in ['important', 'priority', 'soon']):
            return ToolPriority.HIGH
        elif any(word in user_request for word in ['background', 'later', 'whenever']):
            return ToolPriority.LOW
        else:
            return ToolPriority.MEDIUM

    def _update_performance_metrics(self, execution_plan: ToolExecutionPlan, results: List[ToolExecutionResult]):
        """Update performance metrics based on execution results"""
        plan_id = execution_plan.execution_id
        
        metrics = {
            'total_tools': len(execution_plan.tools),
            'successful_tools': sum(1 for r in results if r.status == ToolExecutionStatus.SUCCESS),
            'failed_tools': sum(1 for r in results if r.status == ToolExecutionStatus.FAILED),
            'total_execution_time': sum(r.execution_time for r in results),
            'average_tool_time': sum(r.execution_time for r in results) / len(results) if results else 0,
            'estimated_vs_actual': {
                'estimated': execution_plan.estimated_duration,
                'actual': sum(r.execution_time for r in results)
            }
        }
        
        self.performance_metrics[plan_id] = metrics
        
        # Update tool-specific performance
        for result in results:
            tool_name = result.tool_name
            if tool_name not in self.performance_metrics:
                self.performance_metrics[tool_name] = {'executions': [], 'success_rate': 0.0}
            
            self.performance_metrics[tool_name]['executions'].append({
                'execution_time': result.execution_time,
                'status': result.status.value,
                'timestamp': result.timestamp
            })
            
            # Calculate success rate
            executions = self.performance_metrics[tool_name]['executions']
            successes = sum(1 for e in executions if e['status'] == 'success')
            self.performance_metrics[tool_name]['success_rate'] = successes / len(executions)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary and insights"""
        if not self.execution_history:
            return {'message': 'No executions recorded yet'}
        
        total_executions = len(self.execution_history)
        total_tools_executed = sum(len(h['results']) for h in self.execution_history)
        
        success_rate = sum(
            sum(1 for r in h['results'] if r.status == ToolExecutionStatus.SUCCESS) 
            for h in self.execution_history
        ) / total_tools_executed if total_tools_executed > 0 else 0
        
        avg_execution_time = sum(h['total_execution_time'] for h in self.execution_history) / total_executions
        
        # Tool usage statistics
        tool_usage = {}
        for history in self.execution_history:
            for result in history['results']:
                tool_name = result.tool_name
                if tool_name not in tool_usage:
                    tool_usage[tool_name] = 0
                tool_usage[tool_name] += 1
        
        most_used_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_executions': total_executions,
            'total_tools_executed': total_tools_executed,
            'overall_success_rate': success_rate,
            'average_execution_time': avg_execution_time,
            'most_used_tools': most_used_tools,
            'available_tools': list(self.tool_capabilities.keys()),
            'parallel_execution_enabled': self.enable_parallel_execution
        }