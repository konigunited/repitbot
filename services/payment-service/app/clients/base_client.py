# -*- coding: utf-8 -*-
"""
Base HTTP Client for inter-service communication
Provides common functionality and circuit breaker pattern
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import httpx
from enum import Enum

from ..core.config import settings

logger = logging.getLogger(__name__)


class ServiceClientError(Exception):
    """Base exception for service client errors"""
    pass


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service unavailable, fail fast
    HALF_OPEN = "half_open"  # Testing if service is back up


class CircuitBreaker:
    """Circuit breaker implementation for service resilience"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise ServiceClientError("Service circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise ServiceClientError(f"Service call failed: {e}")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        return (
            datetime.now() - self.last_failure_time 
            > timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class BaseServiceClient:
    """Base class for service-to-service HTTP communication"""
    
    def __init__(self, base_url: str, service_name: str):
        self.base_url = base_url.rstrip('/')
        self.service_name = service_name
        
        # Create HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=30.0,
                pool=60.0
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            )
        )
        
        # Circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(httpx.RequestError, httpx.HTTPStatusError)
        )
        
        # Request retry configuration
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # Exponential backoff
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry and circuit breaker"""
        
        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": f"payment-service/{settings.SERVICE_VERSION}",
            "X-Service-Name": "payment-service"
        }
        
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
        
        if headers:
            request_headers.update(headers)
        
        # Prepare request data
        json_data = None
        if data and method.upper() in ["POST", "PUT", "PATCH"]:
            json_data = data
        
        # Execute request with circuit breaker
        async def _execute_request():
            return await self._execute_with_retry(
                method, endpoint, json_data, params, request_headers
            )
        
        return await self.circuit_breaker.call(_execute_request)
    
    async def _execute_with_retry(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Execute HTTP request with retry logic"""
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Request attempt {attempt + 1}: {method} {endpoint}")
                
                response = await self.client.request(
                    method=method,
                    url=endpoint,
                    json=json_data,
                    params=params,
                    headers=headers
                )
                
                # Raise for HTTP error status codes
                response.raise_for_status()
                
                # Parse JSON response
                if response.content:
                    return response.json()
                else:
                    return {}
                
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                # Don't retry on client errors (4xx), only server errors and network issues
                if isinstance(e, httpx.HTTPStatusError) and 400 <= e.response.status_code < 500:
                    break
                
                # Wait before retry (exponential backoff)
                if attempt < self.max_retries:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.debug(f"Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
        
        # All retries failed
        if last_exception:
            raise last_exception
        else:
            raise ServiceClientError(f"Request to {self.service_name} failed after {self.max_retries} retries")
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make GET request"""
        return await self._make_request("GET", endpoint, params=params, auth_token=auth_token)
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make POST request"""
        return await self._make_request("POST", endpoint, data=data, auth_token=auth_token)
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make PUT request"""
        return await self._make_request("PUT", endpoint, data=data, auth_token=auth_token)
    
    async def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make PATCH request"""
        return await self._make_request("PATCH", endpoint, data=data, auth_token=auth_token)
    
    async def delete(
        self,
        endpoint: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self._make_request("DELETE", endpoint, auth_token=auth_token)
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            response = await self.get("/health")
            return response.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Health check failed for {self.service_name}: {e}")
            return False
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
            "last_failure_time": self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None
        }