"""
JWT Authentication Handler
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import os

# Security Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthHandler:
    """JWT Authentication Handler"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Get password hash"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for testing)"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

class TokenData:
    """Token data structure"""
    def __init__(self, user_id: str, email: str, role: str, permissions: list = None):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.permissions = permissions or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "permissions": self.permissions
        }

# Role-based access control
class RolePermissions:
    """Role-based permissions system"""
    
    ROLES = {
        "admin": [
            "content:create", "content:read", "content:update", "content:delete",
            "domain:create", "domain:read", "domain:update", "domain:delete",
            "user:create", "user:read", "user:update", "user:delete",
            "analytics:read", "system:admin"
        ],
        "content_manager": [
            "content:create", "content:read", "content:update",
            "domain:read", "analytics:read"
        ],
        "content_editor": [
            "content:create", "content:read", "content:update"
        ],
        "viewer": [
            "content:read", "analytics:read"
        ]
    }
    
    @classmethod
    def get_permissions(cls, role: str) -> list:
        """Get permissions for a role"""
        return cls.ROLES.get(role, [])
    
    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """Check if role has specific permission"""
        return permission in cls.get_permissions(role)
    
    @classmethod
    def validate_permissions(cls, required_permissions: list, user_permissions: list) -> bool:
        """Validate if user has required permissions"""
        return all(perm in user_permissions for perm in required_permissions)