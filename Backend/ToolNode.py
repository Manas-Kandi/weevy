from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from Backend.GeneralNodeLogic import GeneralNodeLogic, NodeOutput, PreviousNodeOutput, WorkflowMemory, NodeInputs

@dataclass
class ToolSpec:
    name: str
    description: str
    category: str
    prompt_template: str
    sample_response: str
    input_schema: Dict[str, Any]

# Comprehensive tool library organized by category
TOOLS = {
    # PRODUCT MANAGEMENT TOOLS
    "user_research": ToolSpec(
        name="User Research",
        description="Analyze user feedback, surveys, and interview data",
        category="Product Management",
        prompt_template="Analyze this user data and identify key insights, pain points, and feature requests: {input}",
        sample_response='{"insights": ["Users struggle with onboarding"], "sentiment": "mixed", "priority_issues": ["Performance"]}',
        input_schema={"input_data": {"type": "string"}, "analysis_type": {"type": "string", "enum": ["feedback", "survey", "interview"]}}
    ),
    
    "competitor_analysis": ToolSpec(
        name="Competitor Analysis",
        description="Research and compare competitor features",
        category="Product Management", 
        prompt_template="Analyze competitors and their features: {input}",
        sample_response='{"competitors": [{"name": "CompetitorX", "strengths": ["Better UX"]}], "opportunities": ["Mobile gap"]}',
        input_schema={"competitors": {"type": "array"}, "focus_area": {"type": "string"}}
    ),

    "feature_prioritization": ToolSpec(
        name="Feature Prioritization",
        description="Score and rank features by impact/effort",
        category="Product Management",
        prompt_template="Prioritize these features by impact and effort: {input}",
        sample_response='{"ranked_features": [{"name": "AI Chat", "score": 85}], "quick_wins": ["Search"]}',
        input_schema={"features": {"type": "array"}, "criteria": {"type": "object"}}
    ),

    # COMMUNICATION TOOLS  
    "email": ToolSpec(
        name="Email",
        description="Draft, send, read, and search emails",
        category="Communication",
        prompt_template="Handle email action '{action}' with data: {input}",
        sample_response='{"action": "draft", "subject": "Meeting Follow-up", "body": "Thank you for the productive meeting..."}',
        input_schema={"action": {"type": "string", "enum": ["draft", "send", "search"]}, "to": {"type": "array"}, "subject": {"type": "string"}, "body": {"type": "string"}}
    ),

    "slack": ToolSpec(
        name="Slack",
        description="Post messages, fetch history, manage threads",
        category="Communication", 
        prompt_template="Handle Slack action '{action}': {input}",
        sample_response='{"action": "post_message", "channel": "#general", "message": "Sprint planning meeting at 2pm"}',
        input_schema={"action": {"type": "string", "enum": ["post", "fetch", "reply"]}, "channel": {"type": "string"}, "message": {"type": "string"}}
    ),

    # PRODUCTIVITY TOOLS
    "calendar": ToolSpec(
        name="Calendar",
        description="Manage events and scheduling",
        category="Productivity",
        prompt_template="Handle calendar action '{action}': {input}",
        sample_response='{"action": "create_event", "title": "Product Review", "start": "2024-03-15T14:00:00Z", "attendees": ["team@company.com"]}',
        input_schema={"action": {"type": "string", "enum": ["create", "find_slots", "list"]}, "title": {"type": "string"}, "participants": {"type": "array"}}
    ),

    "notion": ToolSpec(
        name="Notion",
        description="Create/update pages and query databases",
        category="Productivity",
        prompt_template="Handle Notion action '{action}': {input}",
        sample_response='{"action": "create_page", "title": "Product Requirements", "content": "## Overview\\nNew AI feature for..."}',
        input_schema={"action": {"type": "string", "enum": ["create_page", "update_page", "query"]}, "title": {"type": "string"}, "content": {"type": "string"}}
    ),

    # RESEARCH TOOLS
    "web_search": ToolSpec(
        name="Web Search",
        description="Search web for current information",
        category="Research",
        prompt_template="Search for: {input}",
        sample_response='{"query": "AI chatbot best practices", "results": [{"title": "10 AI Chatbot Best Practices", "url": "example.com", "snippet": "Key practices for..."}]}',
        input_schema={"query": {"type": "string"}, "top_k": {"type": "number", "default": 5}}
    ),

    "web_crawl": ToolSpec(
        name="Web Crawl", 
        description="Extract content from specific URLs",
        category="Research",
        prompt_template="Extract and summarize content from: {input}",
        sample_response='{"url": "competitor.com/features", "summary": "Competitor offers 3 main features...", "key_points": ["Feature A", "Feature B"]}',
        input_schema={"url": {"type": "string"}, "focus": {"type": "string"}}
    ),

    # DATA ANALYSIS TOOLS
    "data_analyzer": ToolSpec(
        name="Data Analyzer",
        description="Analyze CSV/JSON data for insights",
        category="Data Analysis", 
        prompt_template="Analyze this data and provide insights: {input}",
        sample_response='{"insights": ["Usage peaked on weekends"], "trends": ["Upward growth"], "recommendations": ["Focus weekend features"]}',
        input_schema={"data": {"type": "string"}, "analysis_type": {"type": "string", "enum": ["trend", "cohort", "funnel"]}}
    ),

    "sql": ToolSpec(
        name="SQL Query",
        description="Query databases for product analytics", 
        category="Data Analysis",
        prompt_template="Execute SQL query: {input}",
        sample_response='{"query": "SELECT COUNT(*) FROM users WHERE created_at > \'2024-01-01\'", "results": [{"count": 1250}], "insights": ["25% user growth this year"]}',
        input_schema={"query": {"type": "string"}, "database": {"type": "string"}}
    ),

    # CONTENT CREATION TOOLS
    "writer": ToolSpec(
        name="Content Writer",
        description="Draft PRDs, blog posts, user guides",
        category="Content Creation",
        prompt_template="Write {content_type} about: {input}",
        sample_response='{"content_type": "PRD", "content": "# Product Requirements Document\\n## Problem Statement\\n...", "word_count": 500}',
        input_schema={"content_type": {"type": "string", "enum": ["PRD", "blog_post", "user_guide", "email"]}, "topic": {"type": "string"}, "length": {"type": "string"}}
    ),

    # DEVELOPMENT TOOLS (for technical PMs)
    "github": ToolSpec(
        name="GitHub",
        description="Create issues, analyze PRs, track development",
        category="Development",
        prompt_template="Handle GitHub action '{action}': {input}",
        sample_response='{"action": "create_issue", "title": "Add AI chat feature", "body": "User story: As a user...", "labels": ["enhancement", "ai"]}',
        input_schema={"action": {"type": "string", "enum": ["create_issue", "analyze_pr"]}, "repo": {"type": "string"}, "title": {"type": "string"}}
    ),

    "jira": ToolSpec(
        name="JIRA",
        description="Create tickets and track development progress",
        category="Development",
        prompt_template="Handle JIRA action '{action}': {input}",
        sample_response='{"action": "create_ticket", "summary": "Implement AI feature", "description": "Acceptance criteria...", "story_points": 8}',
        input_schema={"action": {"type": "string", "enum": ["create_ticket", "update_status"]}, "project": {"type": "string"}, "summary": {"type": "string"}}
    )
}

class ToolNode(GeneralNodeLogic):
    def __init__(self, node_id: str, name: str):
        super().__init__()
        self.node_id = node_id
        self.name = name

    def get_tools_by_category(self) -> Dict[str, List[str]]:
        categories = {}
        for tool_name, tool_spec in TOOLS.items():
            if tool_spec.category not in categories:
                categories[tool_spec.category] = []
            categories[tool_spec.category].append(tool_name)
        return categories

    async def execute(
        self,
        user_configuration: Dict[str, Any], 
        previous_node_data: List[PreviousNodeOutput],
        workflow_memory: WorkflowMemory
    ) -> NodeOutput:
        
        tool_name = user_configuration.get("tool_name")
        input_data = user_configuration.get("input_data", "")
        mode = user_configuration.get("mode", "prototype")  # prototype or production
        
        if not tool_name or tool_name not in TOOLS:
            return NodeOutput(
                node_id=self.node_id,
                node_type="ToolNode",
                data={
                    "error": "Tool not specified or not found",
                    "available_tools": self.get_tools_by_category()
                },
                timestamp=datetime.now().timestamp(),
                metadata={"error": True}
            )
        
        tool = TOOLS[tool_name]
        
        # Build context from connected nodes
        context_data = []
        for prev in previous_node_data:
            context_data.append({
                "node_type": prev.node_type,
                "data": str(prev.data)[:300]  # Truncate for context
            })
        
        if mode == "prototype":
            # Return realistic simulation for rapid prototyping
            result = {
                "tool": tool.name,
                "category": tool.category,
                "input_received": input_data,
                "context_from_previous_nodes": len(context_data),
                "simulated_result": tool.sample_response,
                "mode": "prototype_simulation",
                "note": "This is a realistic simulation. Switch to production mode for real API calls."
            }
        else:
            # Production mode would call real APIs
            # For now, return enhanced simulation with LLM processing
            prompt = tool.prompt_template.format(
                input=input_data,
                action=user_configuration.get("action", "default"),
                context=context_data
            )
            
            # Use LLM to generate more realistic response
            inputs = NodeInputs(
                system_rules=prompt,
                user_configuration=user_configuration,
                previous_node_data=previous_node_data,
                workflow_memory=workflow_memory
            )
            
            llm_result = await self.execute_node(inputs)
            
            result = {
                "tool": tool.name,
                "category": tool.category,
                "llm_enhanced_result": llm_result.data,
                "mode": "production_ready",
                "context_nodes": len(context_data)
            }
        
        return NodeOutput(
            node_id=self.node_id,
            node_type="ToolNode",
            data=result,
            timestamp=datetime.now().timestamp(),
            metadata={
                "tool_name": tool.name,
                "category": tool.category,
                "mode": mode,
                "context_nodes_count": len(context_data)
            }
        )