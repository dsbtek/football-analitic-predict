"""
Security utilities for the Football Analytics Predictor.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import secrets
import time
from collections import defaultdict


# Security Configuration
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Rate limiting storage (in production, use Redis)
rate_limit_storage = defaultdict(list)

security = HTTPBearer()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class User(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
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


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    return {"email": email, "user_id": payload.get("user_id")}


def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Rate limiting decorator."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get client IP (in production, use proper IP detection)
            client_ip = "127.0.0.1"  # Simplified for demo

            current_time = time.time()
            window_start = current_time - window_seconds

            # Clean old requests
            rate_limit_storage[client_ip] = [
                req_time for req_time in rate_limit_storage[client_ip]
                if req_time > window_start
            ]

            # Check rate limit
            if len(rate_limit_storage[client_ip]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )

            # Record this request
            rate_limit_storage[client_ip].append(current_time)

            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_api_key(api_key: str) -> bool:
    """Validate API key for external integrations."""
    # In production, store API keys in database with proper hashing
    valid_keys = os.getenv('VALID_API_KEYS', '').split(',')
    return api_key in valid_keys


def sanitize_input(input_string: str, max_length: int = 255) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not isinstance(input_string, str):
        raise ValueError("Input must be a string")

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
    sanitized = input_string

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')

    # Limit length
    return sanitized[:max_length].strip()


def get_security_headers(environment: str = "development") -> Dict[str, str]:
    """Get security headers for HTTP responses."""

    # Base CSP for development (more permissive for API docs)
    if environment == "development":
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self' ws: wss: http://localhost:* https://localhost:*; "
            "frame-ancestors 'none'"
        )
    else:
        # Stricter CSP for production
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self' wss:; "
            "frame-ancestors 'none'"
        )

    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Content-Security-Policy": csp,
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

    # Only add HSTS in production
    if environment == "production":
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return headers


# Optional: User database model (simplified)
class UserDB:
    """Simplified user database for demo purposes."""

    def __init__(self):
        self.users = {}  # In production, use proper database
        self.next_id = 1

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        if user_data.email in [u['email'] for u in self.users.values()]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        user_id = self.next_id
        self.next_id += 1

        user = {
            'id': user_id,
            'email': user_data.email,
            'full_name': user_data.full_name,
            'password_hash': hash_password(user_data.password),
            'is_active': True,
            'created_at': datetime.utcnow()
        }

        self.users[user_id] = user
        return User(**{k: v for k, v in user.items() if k != 'password_hash'})

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        user = next((u for u in self.users.values()
                    if u['email'] == email), None)
        if not user or not verify_password(password, user['password_hash']):
            return None

        return User(**{k: v for k, v in user.items() if k != 'password_hash'})

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user = next((u for u in self.users.values()
                    if u['email'] == email), None)
        if not user:
            return None

        return User(**{k: v for k, v in user.items() if k != 'password_hash'})


# Global user database instance
user_db = UserDB()
