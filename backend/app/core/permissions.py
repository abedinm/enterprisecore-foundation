"""
Role-based access control.

Hierarchy (high → low privilege):
    ADMIN > MANAGER > EMPLOYEE
    DEVELOPER (parallel — full API access, no people-management)

Usage in a route:
    @router.get(..., dependencies=[Depends(require_role(UserRole.ADMIN))])
"""

from typing import Callable, Iterable
from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User, UserRole


# Sets that each role grants access to.
_ROLE_INCLUSIONS = {
    UserRole.ADMIN:     {UserRole.ADMIN, UserRole.MANAGER, UserRole.EMPLOYEE, UserRole.DEVELOPER},
    UserRole.MANAGER:   {UserRole.MANAGER, UserRole.EMPLOYEE},
    UserRole.EMPLOYEE:  {UserRole.EMPLOYEE},
    UserRole.DEVELOPER: {UserRole.DEVELOPER, UserRole.EMPLOYEE},
}


def role_includes(user_role: UserRole, allowed: Iterable[UserRole]) -> bool:
    """Does the user's effective role grant any of `allowed`?"""
    granted = _ROLE_INCLUSIONS.get(user_role, set())
    return any(r in granted for r in allowed)


def require_role(*allowed: UserRole) -> Callable:
    """
    Dependency factory.

    `require_role(UserRole.ADMIN)` → only admins.
    `require_role(UserRole.ADMIN, UserRole.MANAGER)` → admins or managers.
    """
    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if not role_includes(current_user.role, allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in allowed]}",
            )
        return current_user

    return _checker


# Convenience shortcuts
require_admin = require_role(UserRole.ADMIN)
require_manager = require_role(UserRole.ADMIN, UserRole.MANAGER)
require_developer = require_role(UserRole.ADMIN, UserRole.DEVELOPER)
