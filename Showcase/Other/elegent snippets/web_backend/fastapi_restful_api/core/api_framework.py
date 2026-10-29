# Service ID: WBF45
# Service Name: تصميم وتطوير واجهات API من نوع Restful باستخدام FastAPI | Flask مع بايثون

"""
Advanced RESTful API Framework Module

This module provides comprehensive RESTful API development capabilities
using FastAPI with advanced features for modern web applications.

Author: Senior API Developer
Version: 4.1.2
License: Commercial
"""

from typing import Dict, List, Optional, Union, Any, Callable, Type
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import secrets
from abc import ABC, abstractmethod

# FastAPI and related imports
from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, validator
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
import redis
import jwt
from passlib.context import CryptContext

# Configure logging for API operations
logger = logging.getLogger('restful_api')

# ==================== SECTION 1: Core API Models and Schemas ====================

class APIStatus(Enum):
    """
    API endpoint status enumeration
    تعداد حالة نقاط النهاية للواجهة البرمجية
    """
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"
    BETA = "beta"

class HTTPMethod(Enum):
    """HTTP method enumeration"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"

@dataclass
class APIEndpoint:
    """
    Data class representing API endpoint configuration
    فئة البيانات التي تمثل تكوين نقطة النهاية للواجهة البرمجية
    """
    path: str
    method: HTTPMethod
    handler: Callable
    description: str
    tags: List[str] = field(default_factory=list)
    status: APIStatus = APIStatus.ACTIVE
    auth_required: bool = True
    rate_limit: Optional[int] = None
    cache_ttl: Optional[int] = None
    version: str = "v1"

class BaseAPIModel(BaseModel):
    """
    Base Pydantic model for API schemas
    النموذج الأساسي لـ Pydantic لمخططات الواجهة البرمجية
    """
    
    class Config:
        orm_mode = True
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True

class APIResponse(BaseAPIModel):
    """Standard API response model"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('timestamp', pre=True)
    def format_timestamp(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

class PaginationParams(BaseAPIModel):
    """
    Pagination parameters for API endpoints
    معاملات التصفح لنقاط النهاية للواجهة البرمجية
    """
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$", description="Sort order")

class FilterParams(BaseAPIModel):
    """Generic filter parameters"""
    search: Optional[str] = Field(None, description="Search query")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    status: Optional[str] = Field(None, description="Status filter")
    category: Optional[str] = Field(None, description="Category filter")

# Database Models
Base = declarative_base()

class APIUser(Base):
    """
    API user model for authentication
    نموذج مستخدم الواجهة البرمجية للمصادقة
    """
    __tablename__ = "api_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # API specific fields
    api_key = Column(String(64), unique=True, index=True)
    api_secret = Column(String(128))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Rate limiting and usage tracking
    rate_limit_per_hour = Column(Integer, default=1000)
    current_usage = Column(Integer, default=0)
    last_request_time = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    api_tokens = relationship("APIToken", back_populates="user")
    request_logs = relationship("APIRequestLog", back_populates="user")

class APIToken(Base):
    """
    API token model for authentication
    نموذج رمز الواجهة البرمجية للمصادقة
    """
    __tablename__ = "api_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("api_users.id"), nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    token_type = Column(String(20), default="bearer")
    
    # Token metadata
    name = Column(String(100), nullable=False)
    description = Column(Text)
    scopes = Column(Text)  # JSON string of permissions
    
    # Expiration and status
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    # Security
    created_from_ip = Column(String(45))
    last_used_ip = Column(String(45))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("APIUser", back_populates="api_tokens")

class APIRequestLog(Base):
    """
    API request logging model
    نموذج تسجيل طلبات الواجهة البرمجية
    """
    __tablename__ = "api_request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("api_users.id"))
    
    # Request details
    method = Column(String(10), nullable=False)
    endpoint = Column(String(255), nullable=False)
    full_url = Column(Text)
    user_agent = Column(Text)
    ip_address = Column(String(45))
    
    # Request/Response data
    request_headers = Column(Text)  # JSON
    request_body = Column(Text)
    response_status = Column(Integer)
    response_size = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    api_version = Column(String(10))
    error_message = Column(Text)
    
    # Relationships
    user = relationship("APIUser", back_populates="request_logs")

# ==================== SECTION 2: Authentication and Security ====================

class APISecurityManager:
    """
    Comprehensive API security and authentication manager
    مدير الأمان والمصادقة الشامل للواجهة البرمجية
    """
    
    def __init__(self, secret_key: str, redis_client: Optional[redis.Redis] = None):
        self.secret_key = secret_key
        self.redis_client = redis_client
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()
        
        # Security configurations
        self.token_expire_hours = 24
        self.refresh_token_expire_days = 30
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 15
        
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        إنشاء رمز الوصول JWT
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.token_expire_hours)
            
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm="HS256")
        return encoded_jwt
    
    def create_refresh_token(self, user_id: int) -> str:
        """
        Create refresh token for token renewal
        إنشاء رمز التحديث لتجديد الرمز
        """
        data = {
            "user_id": user_id,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32)  # JWT ID for token tracking
        }
        
        return jwt.encode(data, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token
        التحقق من وفك تشفير رمز JWT
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # Check if token is expired
            if datetime.utcnow() > datetime.fromtimestamp(payload.get("exp", 0)):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            # Check if token is blacklisted (if Redis is available)
            if self.redis_client:
                jti = payload.get("jti")
                if jti and self.redis_client.get(f"blacklist:{jti}"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked"
                    )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_api_key(self) -> tuple[str, str]:
        """
        Generate API key and secret pair
        إنشاء زوج مفتاح وسر الواجهة البرمجية
        """
        api_key = f"ak_{secrets.token_urlsafe(32)}"
        api_secret = secrets.token_urlsafe(64)
        return api_key, api_secret
    
    def validate_api_key(self, api_key: str, api_secret: str, db: Session) -> Optional[APIUser]:
        """
        Validate API key and secret
        التحقق من صحة مفتاح وسر الواجهة البرمجية
        """
        user = db.query(APIUser).filter(
            APIUser.api_key == api_key,
            APIUser.is_active == True
        ).first()
        
        if not user:
            return None
            
        # Verify API secret (should be hashed in production)
        if user.api_secret != api_secret:
            return None
            
        # Update last request time and usage
        user.last_request_time = datetime.utcnow()
        user.current_usage += 1
        db.commit()
        
        return user
    
    def check_rate_limit(self, user: APIUser) -> bool:
        """
        Check if user has exceeded rate limit
        فحص ما إذا كان المستخدم قد تجاوز حد المعدل
        """
        if not user.last_request_time:
            return True
            
        # Reset usage if more than an hour has passed
        if datetime.utcnow() - user.last_request_time > timedelta(hours=1):
            user.current_usage = 0
            return True
            
        return user.current_usage < user.rate_limit_per_hour
    
    def blacklist_token(self, token: str) -> bool:
        """
        Add token to blacklist
        إضافة الرمز إلى القائمة السوداء
        """
        if not self.redis_client:
            return False
            
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                # Set expiration time for blacklist entry
                ttl = exp - datetime.utcnow().timestamp()
                if ttl > 0:
                    self.redis_client.setex(f"blacklist:{jti}", int(ttl), "1")
                    return True
                    
        except jwt.JWTError:
            pass
            
        return False

class APIAuthenticationSchemes:
    """
    Different authentication schemes for API
    مخططات المصادقة المختلفة للواجهة البرمجية
    """
    
    def __init__(self, security_manager: APISecurityManager, db_session: Session):
        self.security_manager = security_manager
        self.db = db_session
    
    async def jwt_auth(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> APIUser:
        """
        JWT token authentication dependency
        تبعية مصادقة رمز JWT
        """
        token = credentials.credentials
        payload = self.security_manager.verify_token(token)
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = self.db.query(APIUser).filter(APIUser.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
    
    async def api_key_auth(self, request: Request) -> APIUser:
        """
        API key authentication dependency
        تبعية مصادقة مفتاح الواجهة البرمجية
        """
        api_key = request.headers.get("X-API-Key")
        api_secret = request.headers.get("X-API-Secret")
        
        if not api_key or not api_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key and secret required"
            )
        
        user = self.security_manager.validate_api_key(api_key, api_secret, self.db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API credentials"
            )
        
        # Check rate limiting
        if not self.security_manager.check_rate_limit(user):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        return user
    
    async def optional_auth(self, request: Request) -> Optional[APIUser]:
        """
        Optional authentication for public endpoints
        المصادقة الاختيارية لنقاط النهاية العامة
        """
        try:
            # Try JWT first
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = self.security_manager.verify_token(token)
                user_id = payload.get("user_id")
                if user_id:
                    return self.db.query(APIUser).filter(APIUser.id == user_id).first()
            
            # Try API key
            api_key = request.headers.get("X-API-Key")
            api_secret = request.headers.get("X-API-Secret")
            if api_key and api_secret:
                return self.security_manager.validate_api_key(api_key, api_secret, self.db)
                
        except:
            pass  # Ignore authentication errors for optional auth
            
        return None

# ==================== SECTION 3: Request/Response Handling ====================

class APIRequestHandler:
    """
    Advanced request and response handling for API endpoints
    معالج متقدم للطلبات والاستجابات لنقاط النهاية للواجهة البرمجية
    """
    
    def __init__(self, db_session: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db_session
        self.redis_client = redis_client
        self.request_start_time = None
        
    async def log_request(self, request: Request, user: Optional[APIUser] = None) -> None:
        """
        Log API request for monitoring and analytics
        تسجيل طلب الواجهة البرمجية للمراقبة والتحليلات
        """
        self.request_start_time = datetime.utcnow()
        
        # Extract request information
        headers = dict(request.headers)
        body = None
        
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    body = body.decode('utf-8')
        except:
            body = None
        
        # Create log entry
        log_entry = APIRequestLog(
            user_id=user.id if user else None,
            method=request.method,
            endpoint=str(request.url.path),
            full_url=str(request.url),
            user_agent=headers.get('user-agent', ''),
            ip_address=request.client.host if request.client else '',
            request_headers=json.dumps(headers),
            request_body=body,
            api_version=headers.get('api-version', 'v1')
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        # Store log ID for response logging
        request.state.log_id = log_entry.id
    
    def create_success_response(self, data: Any = None, message: str = "Success", 
                              metadata: Optional[Dict[str, Any]] = None) -> APIResponse:
        """
        Create standardized success response
        إنشاء استجابة نجاح موحدة
        """
        return APIResponse(
            success=True,
            message=message,
            data=data,
            metadata=metadata
        )
    
    def create_error_response(self, message: str, errors: Optional[List[str]] = None,
                            status_code: int = 400) -> JSONResponse:
        """
        Create standardized error response
        إنشاء استجابة خطأ موحدة
        """
        response_data = APIResponse(
            success=False,
            message=message,
            errors=errors or []
        )
        
        return JSONResponse(
            status_code=status_code,
            content=jsonable_encoder(response_data)
        )
    
    def create_paginated_response(self, items: List[Any], total: int, 
                                pagination: PaginationParams) -> APIResponse:
        """
        Create paginated response with metadata
        إنشاء استجابة مقسمة مع البيانات الوصفية
        """
        total_pages = (total + pagination.size - 1) // pagination.size
        
        metadata = {
            "pagination": {
                "current_page": pagination.page,
                "page_size": pagination.size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": pagination.page < total_pages,
                "has_previous": pagination.page > 1
            }
        }
        
        return self.create_success_response(
            data=items,
            message=f"Retrieved {len(items)} items",
            metadata=metadata
        )

# ==================== SECTION 4: API Middleware and Utilities ====================

class APIMiddleware:
    """
    Custom middleware for API request processing
    البرمجيات الوسطية المخصصة لمعالجة طلبات الواجهة البرمجية
    """
    
    def __init__(self, app: FastAPI, security_manager: APISecurityManager):
        self.app = app
        self.security_manager = security_manager
        
    async def process_request(self, request: Request, call_next):
        """
        Process incoming API requests
        معالجة طلبات الواجهة البرمجية الواردة
        """
        start_time = datetime.utcnow()
        
        # Add request ID for tracking
        request_id = secrets.token_hex(8)
        request.state.request_id = request_id
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-API-Version"] = "1.0"
        
        return response

class APIRateLimiter:
    """
    Advanced rate limiting for API endpoints
    تحديد المعدل المتقدم لنقاط النهاية للواجهة البرمجية
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.rate_limit_prefix = "rate_limit:"
        
    async def check_rate_limit(self, identifier: str, limit: int, window: int) -> Dict[str, Any]:
        """
        Check if request exceeds rate limit
        فحص ما إذا كان الطلب يتجاوز حد المعدل
        """
        current_time = int(datetime.utcnow().timestamp())
        window_start = current_time - window
        
        key = f"{self.rate_limit_prefix}{identifier}"
        
        try:
            # Remove old entries outside the window
            self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            current_requests = self.redis_client.zcard(key)
            
            if current_requests >= limit:
                # Get time until window resets
                oldest_request = self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_request:
                    reset_time = int(oldest_request[0][1]) + window
                    return {
                        "allowed": False,
                        "limit": limit,
                        "remaining": 0,
                        "reset_time": reset_time
                    }
            
            # Add current request
            self.redis_client.zadd(key, {f"{current_time}:{secrets.token_hex(4)}": current_time})
            self.redis_client.expire(key, window)
            
            return {
                "allowed": True,
                "limit": limit,
                "remaining": limit - current_requests - 1,
                "reset_time": current_time + window
            }
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # Allow request on error to prevent service disruption
            return {
                "allowed": True,
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": current_time + window
            }

class APIDocumentationGenerator:
    """
    Automatic API documentation generator
    مولد التوثيق التلقائي للواجهة البرمجية
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        
    def generate_endpoint_docs(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """
        Generate documentation for API endpoint
        إنشاء التوثيق لنقطة النهاية للواجهة البرمجية
        """
        return {
            "path": endpoint.path,
            "method": endpoint.method.value,
            "description": endpoint.description,
            "tags": endpoint.tags,
            "status": endpoint.status.value,
            "auth_required": endpoint.auth_required,
            "rate_limit": endpoint.rate_limit,
            "cache_ttl": endpoint.cache_ttl,
            "version": endpoint.version
        }
    
    def generate_api_spec(self, endpoints: List[APIEndpoint]) -> Dict[str, Any]:
        """
        Generate OpenAPI specification
        إنشاء مواصفات OpenAPI
        """
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Advanced RESTful API",
                "version": "1.0.0",
                "description": "Professional API built with FastAPI"
            },
            "servers": [
                {"url": "/api/v1", "description": "Version 1"}
            ],
            "paths": {},
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    },
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key"
                    }
                }
            }
        }
        
        # Add endpoint documentation
        for endpoint in endpoints:
            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}
            
            spec["paths"][endpoint.path][endpoint.method.value.lower()] = {
                "summary": endpoint.description,
                "tags": endpoint.tags,
                "security": [{"BearerAuth": []}] if endpoint.auth_required else [],
                "responses": {
                    "200": {"description": "Successful response"},
                    "400": {"description": "Bad request"},
                    "401": {"description": "Unauthorized"},
                    "429": {"description": "Rate limit exceeded"},
                    "500": {"description": "Internal server error"}
                }
            }
        
        return spec

# ==================== SECTION 5: Advanced API Features ====================

class APIWebSocketManager:
    """
    WebSocket connection manager for real-time features
    مدير اتصال WebSocket للميزات في الوقت الفعلي
    """
    
    def __init__(self):
        self.active_connections: Dict[str, Any] = {}
        self.user_connections: Dict[int, List[str]] = {}
        
    async def connect(self, websocket, user_id: int, connection_id: str):
        """
        Accept WebSocket connection
        قبول اتصال WebSocket
        """
        await websocket.accept()
        self.active_connections[connection_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "connected_at": datetime.utcnow()
        }
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
    
    def disconnect(self, connection_id: str):
        """
        Remove WebSocket connection
        إزالة اتصال WebSocket
        """
        if connection_id in self.active_connections:
            user_id = self.active_connections[connection_id]["user_id"]
            del self.active_connections[connection_id]
            
            if user_id in self.user_connections:
                self.user_connections[user_id] = [
                    conn for conn in self.user_connections[user_id] 
                    if conn != connection_id
                ]
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: str, user_id: int):
        """
        Send message to specific user
        إرسال رسالة إلى مستخدم محدد
        """
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.active_connections:
                    websocket = self.active_connections[connection_id]["websocket"]
                    try:
                        await websocket.send_text(message)
                    except:
                        self.disconnect(connection_id)
    
    async def broadcast(self, message: str):
        """
        Broadcast message to all connected users
        بث رسالة لجميع المستخدمين المتصلين
        """
        disconnected = []
        for connection_id, connection in self.active_connections.items():
            try:
                await connection["websocket"].send_text(message)
            except:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(connection_id)

class APIBackgroundTasks:
    """
    Background task management for API operations
    إدارة المهام الخلفية لعمليات الواجهة البرمجية
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.task_queue = "api_tasks"
        
    async def enqueue_task(self, task_name: str, task_data: Dict[str, Any], 
                          delay: Optional[int] = None) -> str:
        """
        Add task to background queue
        إضافة مهمة إلى قائمة انتظار الخلفية
        """
        task_id = secrets.token_hex(16)
        
        task_payload = {
            "id": task_id,
            "name": task_name,
            "data": task_data,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        
        if self.redis_client:
            if delay:
                # Schedule task for later execution
                execute_at = datetime.utcnow() + timedelta(seconds=delay)
                self.redis_client.zadd(
                    f"{self.task_queue}:scheduled",
                    {json.dumps(task_payload): execute_at.timestamp()}
                )
            else:
                # Add to immediate execution queue
                self.redis_client.lpush(self.task_queue, json.dumps(task_payload))
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of background task
        الحصول على حالة المهمة الخلفية
        """
        if not self.redis_client:
            return None
            
        # Check if task is completed
        result = self.redis_client.get(f"task_result:{task_id}")
        if result:
            return json.loads(result.decode('utf-8'))
        
        return {"id": task_id, "status": "processing"}
    
    async def process_scheduled_tasks(self):
        """
        Process scheduled tasks that are due
        معالجة المهام المجدولة المستحقة
        """
        if not self.redis_client:
            return
            
        current_time = datetime.utcnow().timestamp()
        
        # Get tasks that are due
        due_tasks = self.redis_client.zrangebyscore(
            f"{self.task_queue}:scheduled",
            0, current_time
        )
        
        for task_data in due_tasks:
            # Move to immediate execution queue
            self.redis_client.lpush(self.task_queue, task_data)
            
            # Remove from scheduled queue
            self.redis_client.zrem(f"{self.task_queue}:scheduled", task_data)

class APIHealthChecker:
    """
    Health checking system for API services
    نظام فحص الصحة لخدمات الواجهة البرمجية
    """
    
    def __init__(self, db_session: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db_session
        self.redis_client = redis_client
        
    async def check_database_health(self) -> Dict[str, Any]:
        """
        Check database connectivity and performance
        فحص اتصال قاعدة البيانات والأداء
        """
        try:
            start_time = datetime.utcnow()
            
            # Simple query to test connection
            result = self.db.execute("SELECT 1").fetchone()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "connection": "active"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """
        Check Redis connectivity and performance
        فحص اتصال Redis والأداء
        """
        if not self.redis_client:
            return {"status": "not_configured"}
            
        try:
            start_time = datetime.utcnow()
            
            # Test Redis connection
            self.redis_client.ping()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Get Redis info
            info = self.redis_client.info()
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health report
        الحصول على تقرير صحة النظام الشامل
        """
        health_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "services": {}
        }
        
        # Check database
        db_health = await self.check_database_health()
        health_report["services"]["database"] = db_health
        
        # Check Redis
        redis_health = await self.check_redis_health()
        health_report["services"]["redis"] = redis_health
        
        # Determine overall status
        unhealthy_services = [
            service for service, status in health_report["services"].items()
            if status.get("status") == "unhealthy"
        ]
        
        if unhealthy_services:
            health_report["overall_status"] = "unhealthy"
            health_report["unhealthy_services"] = unhealthy_services
        
        return health_report
