"""
Security middleware for the dashboard API.
Provides rate limiting, IP filtering, and security headers.
"""

import logging
import time
import ipaddress
from typing import Dict, Optional, Set
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from utils.redis_utils import r

logger = logging.getLogger("uvicorn")

class SecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware for the dashboard API."""
    
    def __init__(self, app, rate_limit_requests: int = 60, rate_limit_window: int = 300):
        super().__init__(app)
        self.rate_limit_requests = rate_limit_requests  # Requests per window
        self.rate_limit_window = rate_limit_window      # Window in seconds (5 minutes)
        self.blocked_ips: Set[str] = set()
        
        # Security headers to add to all responses
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security checks."""
        try:
            # Get client IP
            client_ip = self.get_client_ip(request)
            
            # Log the detected IP for debugging
            logger.debug(f"Request from IP: {client_ip}")
            
            # Check if IP is blocked
            if await self.is_ip_blocked(client_ip):
                logger.warning(f"Blocked request from IP: {client_ip}")
                raise HTTPException(status_code=403, detail="Access forbidden")
            
            # Apply rate limiting
            if not await self.check_rate_limit(client_ip, request):
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Validate request headers for security
            await self.validate_request_headers(request)
            
            # Process the request
            response = await call_next(request)
            
            # Add security headers to response
            self.add_security_headers(response)
            
            # Log successful request
            self.log_request(request, response, client_ip)
            
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxy headers."""
        # For Docker/internal requests, prioritize the direct connection
        if request.client and request.client.host:
            direct_ip = request.client.host
            # If it's a Docker internal IP, use it directly
            if self.is_docker_internal_ip(direct_ip):
                logger.debug(f"Using direct Docker IP: {direct_ip}")
                return direct_ip
        
        # Check for common proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct connection IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def is_docker_internal_ip(self, ip: str) -> bool:
        """Check if IP is from Docker internal networks or local ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Define Docker and internal IP ranges
            internal_ranges = [
                ipaddress.ip_network('172.16.0.0/12'),   # Docker default bridge networks (172.16.0.0 - 172.31.255.255)
                ipaddress.ip_network('192.168.0.0/16'), # Private networks
                ipaddress.ip_network('10.0.0.0/8'),     # Private networks
                ipaddress.ip_network('127.0.0.0/8'),    # Localhost
                ipaddress.ip_network('::1/128'),        # IPv6 localhost
                ipaddress.ip_network('fc00::/7'),       # IPv6 private ranges
            ]
            
            # Check if IP falls within any internal range
            for network in internal_ranges:
                if ip_obj in network:
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug(f"Error checking IP range for {ip}: {e}")
            # If we can't parse the IP, assume it's external for safety
            return False
    
    async def is_ip_blocked(self, client_ip: str) -> bool:
        """Check if an IP address is blocked."""
        try:
            # Skip blocking for Docker internal IPs and local ranges
            if self.is_docker_internal_ip(client_ip):
                logger.debug(f"IP {client_ip} identified as Docker internal, not blocking")
                return False
            
            # Check local blocked set
            if client_ip in self.blocked_ips:
                return True
            
            # Check Redis for temporarily blocked IPs
            block_key = f"meta-glasses:security:blocked_ip:{client_ip}"
            blocked = r.get(block_key)
            
            if blocked:
                # Add to local set for faster subsequent checks
                self.blocked_ips.add(client_ip)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking IP block status: {e}")
            return False
    
    async def check_rate_limit(self, client_ip: str, request: Request) -> bool:
        """Check if request is within rate limits."""
        try:
            # Skip rate limiting for Docker internal IPs and local ranges
            if self.is_docker_internal_ip(client_ip):
                # Allow much higher limits for internal Docker traffic (dashboard, etc.)
                internal_limit = self.rate_limit_requests * 10  # 10x higher limit for internal IPs
                logger.debug(f"Using internal rate limit {internal_limit} for Docker IP: {client_ip}")
            else:
                internal_limit = self.rate_limit_requests
            
            current_time = int(time.time())
            window_start = current_time - self.rate_limit_window
            
            # Create rate limit key
            rate_key = f"meta-glasses:security:rate_limit:{client_ip}"
            
            # Get current request count in window
            pipe = r.pipeline()
            pipe.zremrangebyscore(rate_key, 0, window_start)  # Remove old entries
            pipe.zcard(rate_key)  # Count current entries
            pipe.zadd(rate_key, {str(current_time): current_time})  # Add current request
            pipe.expire(rate_key, self.rate_limit_window)  # Set expiry
            
            results = pipe.execute()
            current_requests = results[1]
            
            # Check if limit exceeded
            if current_requests >= internal_limit:
                # Log the rate limit violation
                logger.warning(f"Rate limit exceeded for {client_ip}: {current_requests} requests in {self.rate_limit_window}s (limit: {internal_limit})")
                
                # Block IP temporarily for repeat offenders (but only external IPs)
                if not self.is_docker_internal_ip(client_ip):
                    await self.handle_rate_limit_violation(client_ip)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Allow request on error to avoid blocking legitimate traffic
            return True
    
    async def handle_rate_limit_violation(self, client_ip: str):
        """Handle rate limit violations by temporarily blocking aggressive IPs."""
        try:
            # Check how many violations this IP has had
            violation_key = f"meta-glasses:security:violations:{client_ip}"
            violations = r.incr(violation_key)
            r.expire(violation_key, 3600)  # Reset violations after 1 hour
            
            # Block IP if too many violations
            if violations >= 3:
                block_key = f"meta-glasses:security:blocked_ip:{client_ip}"
                block_duration = min(3600 * violations, 86400)  # Max 24 hours
                r.setex(block_key, block_duration, "rate_limit_violation")
                
                logger.error(f"IP {client_ip} blocked for {block_duration}s due to repeated rate limit violations")
                
        except Exception as e:
            logger.error(f"Error handling rate limit violation: {e}")
    
    async def validate_request_headers(self, request: Request):
        """Validate request headers for security issues."""
        try:
            # Check for suspiciously large headers
            for name, value in request.headers.items():
                if len(value) > 8192:  # 8KB limit per header
                    logger.warning(f"Oversized header {name} from {self.get_client_ip(request)}")
                    raise HTTPException(status_code=400, detail="Request header too large")
            
            # Check for common attack patterns in User-Agent
            user_agent = request.headers.get("User-Agent", "").lower()
            suspicious_patterns = ["sqlmap", "nikto", "burp", "nmap", "dirb"]
            
            for pattern in suspicious_patterns:
                if pattern in user_agent:
                    client_ip = self.get_client_ip(request)
                    logger.warning(f"Suspicious User-Agent from {client_ip}: {user_agent}")
                    # Don't block automatically, but log for monitoring
                    break
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating request headers: {e}")
    
    def add_security_headers(self, response: Response):
        """Add security headers to response."""
        try:
            for header, value in self.security_headers.items():
                response.headers[header] = value
        except Exception as e:
            logger.error(f"Error adding security headers: {e}")
    
    def log_request(self, request: Request, response: Response, client_ip: str):
        """Log request details for monitoring."""
        try:
            # Only log non-successful responses or sensitive endpoints
            if response.status_code >= 400 or request.url.path.startswith("/api/dashboard"):
                logger.info(
                    f"API Request: {client_ip} {request.method} {request.url.path} "
                    f"-> {response.status_code}"
                )
        except Exception as e:
            logger.error(f"Error logging request: {e}")

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP whitelist middleware for additional protection in production."""
    
    def __init__(self, app, allowed_ips: Optional[Set[str]] = None, enabled: bool = False):
        super().__init__(app)
        self.allowed_ips = allowed_ips or set()
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next):
        """Check IP whitelist if enabled."""
        if not self.enabled:
            return await call_next(request)
        
        try:
            # Get client IP
            client_ip = self.get_client_ip(request)
            
            # Allow localhost and configured IPs
            if client_ip in ["127.0.0.1", "::1", "localhost"] or client_ip in self.allowed_ips:
                return await call_next(request)
            
            logger.warning(f"Access denied for non-whitelisted IP: {client_ip}")
            raise HTTPException(status_code=403, detail="Access denied")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"IP whitelist middleware error: {e}")
            return await call_next(request)
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        if request.client:
            return request.client.host
        return "unknown"

# Rate limiting decorator for specific endpoints
def rate_limit(requests: int = 10, window: int = 60):
    """Decorator for endpoint-specific rate limiting."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be implemented as a dependency in FastAPI
            # For now, we'll rely on the middleware
            return await func(*args, **kwargs)
        return wrapper
    return decorator