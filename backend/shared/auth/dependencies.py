"""
FastAPI Authentication Dependencies
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from .jwt_handler import AuthHandler, TokenData, RolePermissions

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = AuthHandler.verify_token(token)
    
    user_id = payload.get("user_id")
    email = payload.get("email")
    role = payload.get("role")
    permissions = payload.get("permissions", [])
    
    if user_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenData(user_id=user_id, email=email, role=role, permissions=permissions)

async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Get current active user (can be extended with user status check)"""
    return current_user

def require_permissions(required_permissions: List[str]):
    """Decorator to require specific permissions"""
    async def permission_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not RolePermissions.validate_permissions(required_permissions, current_user.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return permission_checker

def require_role(required_role: str):
    """Decorator to require specific role"""
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role privileges"
            )
        return current_user
    return role_checker

# Common permission dependencies
require_content_create = require_permissions(["content:create"])
require_content_read = require_permissions(["content:read"])
require_content_update = require_permissions(["content:update"])
require_content_delete = require_permissions(["content:delete"])
require_domain_admin = require_permissions(["domain:create", "domain:update", "domain:delete"])
require_user_admin = require_permissions(["user:create", "user:update", "user:delete"])
require_system_admin = require_role("admin")