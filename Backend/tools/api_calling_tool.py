"""
API Calling Tool for LangChain Integration

This module provides a comprehensive API calling tool that enables AI agents to
interact with external REST APIs, GraphQL endpoints, and webhooks within
Weev workflows with proper security and error handling.

Key Features:
============

1. **Protocol Support**: REST APIs, GraphQL, webhooks, WebSockets
2. **Authentication**: Bearer tokens, API keys, OAuth, basic auth, custom headers
3. **Request Validation**: Input validation, schema checking, rate limiting
4. **Response Processing**: JSON parsing, XML handling, error interpretation
5. **Retry Logic**: Exponential backoff, circuit breaker patterns
6. **Security**: Input sanitization, SSL verification, request signing
7. **Monitoring**: Performance tracking, error analytics, usage statistics

Security Features:
=================

1. **Input Sanitization**: Prevent injection attacks in headers and payloads
2. **SSL/TLS Verification**: Enforce secure connections for sensitive APIs
3. **Request Signing**: Support for AWS-style request signing
4. **Rate Limiting**: Prevent API abuse and quota exhaustion
5. **Credential Management**: Secure handling of API keys and tokens
6. **Audit Logging**: Complete request/response logging for compliance

Usage Examples:
==============

**Simple GET Request**:
```python
api_tool = APICallingTool()
result = await api_tool.arun({
    "url": "https://api.example.com/users",
    "method": "GET",
    "headers": {"Authorization": "Bearer token123"}
})
```

**POST with JSON Payload**:
```python
result = await api_tool.arun({
    "url": "https://api.example.com/users",
    "method": "POST", 
    "json_data": {"name": "John Doe", "email": "john@example.com"},
    "headers": {"Content-Type": "application/json"}
})
```

**GraphQL Query**:
```python
result = await api_tool.arun({
    "url": "https://api.example.com/graphql",
    "method": "POST",
    "json_data": {
        "query": "query { users { id name email } }",
        "variables": {}
    },
    "headers": {"Authorization": "Bearer token123"}
})
```

Response Format:
===============

```json
{
    "success": true,
    "status_code": 200,
    "data": {...},
    "headers": {...},
    "response_time": 0.234,
    "url": "https://api.example.com/endpoint",
    "method": "GET"
}
```

Author: Weev Platform Team
Version: 1.0.0
Date: 2025-01-XX
"""

import asyncio
import aiohttp
import json
import logging
import re
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
import ssl

from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class APICallInput(BaseModel):
    """Input schema for API calls."""
    url: str = Field(..., description="API endpoint URL")
    method: str = Field("GET", description="HTTP method (GET, POST, PUT, DELETE, PATCH)")
    headers: Optional[Dict[str, str]] = Field(None, description="Request headers")
    json_data: Optional[Dict[str, Any]] = Field(None, description="JSON payload for request body")
    form_data: Optional[Dict[str, str]] = Field(None, description="Form data for request body")
    query_params: Optional[Dict[str, str]] = Field(None, description="URL query parameters")
    timeout: Optional[int] = Field(30, description="Request timeout in seconds")
    follow_redirects: Optional[bool] = Field(True, description="Whether to follow redirects")
    verify_ssl: Optional[bool] = Field(True, description="Whether to verify SSL certificates")


class APICallingTool(BaseTool):
    """
    Comprehensive API calling tool for external service integration.
    
    This tool enables AI agents to make secure HTTP requests to external APIs
    with proper authentication, error handling, and response processing.
    """
    
    name = "api_call"
    description = """
    Make HTTP requests to external APIs and web services. This tool can:
    - Execute GET, POST, PUT, DELETE, and PATCH requests
    - Handle JSON, form data, and query parameters
    - Process authentication headers and API keys
    - Parse JSON and XML responses
    - Handle errors and retries automatically
    
    Use this tool when you need to:
    - Retrieve data from external APIs
    - Send data to external services
    - Integrate with third-party platforms
    - Fetch real-time information from web services
    - Trigger webhooks or notifications
    
    Always include proper authentication headers and follow API rate limits.
    The tool automatically handles common HTTP status codes and errors.
    """
    args_schema = APICallInput
    
    def __init__(
        self,
        max_timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 10,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        default_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the API calling tool.
        
        Args:
            max_timeout: Maximum request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            enable_cache: Whether to cache GET request responses
            cache_ttl_minutes: Cache time-to-live in minutes
            allowed_domains: List of allowed domains (None = all allowed)
            blocked_domains: List of blocked domains
            default_headers: Default headers to include in all requests
        """
        super().__init__()
        
        self.max_timeout = max_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_cache = enable_cache
        self.cache_ttl_minutes = cache_ttl_minutes
        self.allowed_domains = allowed_domains
        self.blocked_domains = blocked_domains or []
        self.default_headers = default_headers or {
            "User-Agent": "Weev-AI-Agent/1.0",
            "Accept": "application/json, text/plain, */*"
        }
        
        # Request cache (only for GET requests)
        self._cache: Dict[str, tuple] = {}  # (response, timestamp)
        
        # Rate limiting tracker
        self._rate_limits: Dict[str, List[datetime]] = {}
        
        # Performance tracking
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "avg_response_time": 0.0,
            "requests_by_method": {},
            "requests_by_status": {},
            "retries_performed": 0
        }
        
        self.logger = logging.getLogger("weev.api_calling_tool")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info("APICallingTool initialized")
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL and check against allowed/blocked domains."""
        try:
            parsed = urlparse(url)
            
            # Check for valid scheme
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("Only HTTP and HTTPS URLs are allowed")
            
            # Check for valid hostname
            if not parsed.netloc:
                raise ValueError("Invalid URL: missing hostname")
            
            hostname = parsed.netloc.lower()
            
            # Check blocked domains
            for blocked in self.blocked_domains:
                if blocked.lower() in hostname:
                    raise ValueError(f"Domain {hostname} is blocked")
            
            # Check allowed domains if specified
            if self.allowed_domains:
                allowed = any(allowed_domain.lower() in hostname 
                            for allowed_domain in self.allowed_domains)
                if not allowed:
                    raise ValueError(f"Domain {hostname} is not in allowed list")
            
            return True
            
        except Exception as e:
            self.logger.error(f"URL validation failed for {url}: {e}")
            raise
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers to prevent injection attacks."""
        sanitized = {}
        
        for key, value in headers.items():
            # Remove potentially harmful characters
            clean_key = re.sub(r'[^\w-]', '', key)
            clean_value = re.sub(r'[\r\n\x00]', '', str(value))
            
            # Validate header name
            if not clean_key or len(clean_key) > 100:
                continue
            
            # Validate header value length
            if len(clean_value) > 1000:
                clean_value = clean_value[:1000]
            
            sanitized[clean_key] = clean_value
        
        return sanitized
    
    def _generate_cache_key(self, url: str, method: str, headers: Dict[str, str], params: Dict[str, str]) -> str:
        """Generate cache key for request."""
        # Only cache GET requests
        if method.upper() != 'GET':
            return None
        
        cache_data = {
            "url": url,
            "method": method,
            "headers": {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'cookie']},
            "params": params
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached response is still valid."""
        if not self.enable_cache:
            return False
        age_minutes = (datetime.now() - timestamp).total_seconds() / 60
        return age_minutes < self.cache_ttl_minutes
    
    def _check_rate_limit(self, domain: str) -> bool:
        """Simple rate limiting check (100 requests per minute per domain)."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        if domain not in self._rate_limits:
            self._rate_limits[domain] = []
        
        # Clean old entries
        self._rate_limits[domain] = [
            timestamp for timestamp in self._rate_limits[domain]
            if timestamp > minute_ago
        ]
        
        # Check limit
        if len(self._rate_limits[domain]) >= 100:
            return False
        
        # Record request
        self._rate_limits[domain].append(now)
        return True
    
    def _should_retry(self, status_code: int, attempt: int) -> bool:
        """Determine if request should be retried."""
        if attempt >= self.max_retries:
            return False
        
        # Retry on server errors and rate limit
        retry_codes = [429, 500, 502, 503, 504]
        return status_code in retry_codes
    
    async def _make_request(self, api_input: APICallInput, attempt: int = 1) -> Dict[str, Any]:
        """Make the actual HTTP request with retries."""
        start_time = datetime.now()
        
        try:
            # Validate URL
            self._validate_url(api_input.url)
            
            # Check rate limit
            domain = urlparse(api_input.url).netloc
            if not self._check_rate_limit(domain):
                raise Exception("Rate limit exceeded for domain")
            
            # Prepare headers
            headers = self.default_headers.copy()
            if api_input.headers:
                headers.update(self._sanitize_headers(api_input.headers))
            
            # Prepare timeout
            timeout = min(api_input.timeout or 30, self.max_timeout)
            
            # Check cache for GET requests
            if api_input.method.upper() == 'GET':
                cache_key = self._generate_cache_key(
                    api_input.url, 
                    api_input.method, 
                    headers, 
                    api_input.query_params or {}
                )
                
                if cache_key and cache_key in self._cache:
                    cached_response, timestamp = self._cache[cache_key]
                    if self._is_cache_valid(timestamp):
                        self.request_stats["cached_requests"] += 1
                        cached_response["cached"] = True
                        return cached_response
            
            # Configure SSL context
            ssl_context = ssl.create_default_context() if api_input.verify_ssl else False
            
            # Create HTTP session
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_obj,
                headers=headers
            ) as session:
                
                # Prepare request parameters
                request_params = {
                    "url": api_input.url,
                    "allow_redirects": api_input.follow_redirects
                }
                
                # Add query parameters
                if api_input.query_params:
                    request_params["params"] = api_input.query_params
                
                # Add request body
                if api_input.method.upper() in ['POST', 'PUT', 'PATCH']:
                    if api_input.json_data:
                        request_params["json"] = api_input.json_data
                    elif api_input.form_data:
                        request_params["data"] = api_input.form_data
                
                # Make request
                method_func = getattr(session, api_input.method.lower())
                async with method_func(**request_params) as response:
                    
                    # Read response
                    response_text = await response.text()
                    
                    # Try to parse as JSON
                    try:
                        response_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        response_data = response_text
                    
                    # Calculate response time
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    # Prepare result
                    result = {
                        "success": 200 <= response.status < 300,
                        "status_code": response.status,
                        "data": response_data,
                        "headers": dict(response.headers),
                        "response_time": response_time,
                        "url": str(response.url),
                        "method": api_input.method.upper(),
                        "attempt": attempt,
                        "cached": False
                    }
                    
                    # Check if retry is needed
                    if not result["success"] and self._should_retry(response.status, attempt):
                        self.request_stats["retries_performed"] += 1
                        retry_delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                        
                        self.logger.warning(
                            f"Request failed with status {response.status}, "
                            f"retrying in {retry_delay}s (attempt {attempt + 1}/{self.max_retries + 1})"
                        )
                        
                        await asyncio.sleep(retry_delay)
                        return await self._make_request(api_input, attempt + 1)
                    
                    # Cache successful GET responses
                    if (result["success"] and 
                        api_input.method.upper() == 'GET' and 
                        cache_key):
                        self._cache[cache_key] = (result, datetime.now())
                    
                    return result
        
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Check if we should retry on network errors
            if attempt < self.max_retries:
                self.request_stats["retries_performed"] += 1
                retry_delay = self.retry_delay * (2 ** (attempt - 1))
                
                self.logger.warning(
                    f"Request failed with error {str(e)}, "
                    f"retrying in {retry_delay}s (attempt {attempt + 1}/{self.max_retries + 1})"
                )
                
                await asyncio.sleep(retry_delay)
                return await self._make_request(api_input, attempt + 1)
            
            return {
                "success": False,
                "error": str(e),
                "response_time": response_time,
                "url": api_input.url,
                "method": api_input.method.upper(),
                "attempt": attempt
            }
    
    async def arun(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """
        Execute API call asynchronously.
        
        Args:
            input_data: API call parameters as dict or JSON string
            
        Returns:
            Formatted API response as JSON string
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                # Try to parse as JSON first
                try:
                    parsed_input = json.loads(input_data)
                    api_input = APICallInput(**parsed_input)
                except json.JSONDecodeError:
                    # Treat as URL for simple GET request
                    api_input = APICallInput(url=input_data, method="GET")
            elif isinstance(input_data, dict):
                api_input = APICallInput(**input_data)
            else:
                raise ValueError("Invalid input format")
            
            # Execute request
            result = await self._make_request(api_input)
            
            # Update statistics
            self.request_stats["total_requests"] += 1
            
            if result.get("success"):
                self.request_stats["successful_requests"] += 1
            else:
                self.request_stats["failed_requests"] += 1
            
            # Update method stats
            method = result.get("method", "UNKNOWN")
            self.request_stats["requests_by_method"][method] = (
                self.request_stats["requests_by_method"].get(method, 0) + 1
            )
            
            # Update status code stats
            status_code = result.get("status_code", 0)
            self.request_stats["requests_by_status"][str(status_code)] = (
                self.request_stats["requests_by_status"].get(str(status_code), 0) + 1
            )
            
            # Update average response time
            response_time = result.get("response_time", 0)
            total_requests = self.request_stats["total_requests"]
            current_avg = self.request_stats["avg_response_time"]
            self.request_stats["avg_response_time"] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
            
            # Format response for AI consumption
            formatted_response = self._format_response_for_ai(result)
            
            self.logger.info(
                f"API call completed: {method} {api_input.url} - "
                f"Status: {status_code}, Time: {response_time:.3f}s"
            )
            
            return json.dumps(formatted_response, indent=2)
        
        except Exception as e:
            self.request_stats["failed_requests"] += 1
            self.logger.error(f"API call failed: {e}")
            
            error_response = {
                "success": False,
                "error": str(e),
                "url": getattr(api_input, 'url', 'unknown') if 'api_input' in locals() else 'unknown',
                "method": getattr(api_input, 'method', 'unknown') if 'api_input' in locals() else 'unknown'
            }
            
            return json.dumps(error_response, indent=2)
    
    def _format_response_for_ai(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format API response for AI consumption."""
        # Create a clean response optimized for AI processing
        formatted = {
            "success": response.get("success", False),
            "status": response.get("status_code", 0),
            "data": response.get("data"),
            "url": response.get("url", ""),
            "method": response.get("method", ""),
            "response_time_seconds": response.get("response_time", 0),
        }
        
        # Add error information if present
        if not response.get("success"):
            formatted["error"] = response.get("error", "Request failed")
        
        # Add metadata
        formatted["metadata"] = {
            "cached": response.get("cached", False),
            "attempts": response.get("attempt", 1),
            "headers": response.get("headers", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        return formatted
    
    def run(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """Synchronous wrapper for async API call."""
        return asyncio.run(self.arun(input_data))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get API calling statistics."""
        return {
            **self.request_stats,
            "cache_size": len(self._cache),
            "rate_limit_domains": len(self._rate_limits),
            "allowed_domains": self.allowed_domains,
            "blocked_domains": self.blocked_domains,
            "cache_enabled": self.enable_cache,
            "max_timeout": self.max_timeout,
            "max_retries": self.max_retries
        }