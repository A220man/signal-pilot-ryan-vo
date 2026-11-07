"""Authentication dependencies for FastAPI routes."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.services.auth import OIDCAuthService, Roles, TokenClaims

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_auth_service(settings: Settings = Depends(get_settings)) -> OIDCAuthService:
    """Dependency: OIDC authentication service."""
    return OIDCAuthService(settings)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    auth_service: OIDCAuthService = Depends(get_auth_service),
) -> TokenClaims:
    """Extract and validate the current user from the Authorization header.

    In demo mode, returns a default admin user for testing.
    In production mode, validates the OIDC token.
    """
    settings = get_settings()

    # Demo mode: allow unauthenticated access with a default user
    if settings.demo_mode:
        return TokenClaims(
            sub="demo-user",
            username="demo",
            email="demo@example.com",
            roles=[Roles.ADMIN, Roles.ANALYST, Roles.VIEWER],
            realm_roles=[Roles.ADMIN, Roles.ANALYST, Roles.VIEWER],
            client_roles={},
            exp=0,
            iat=0,
            iss="demo",
            aud=["demo"],
        )

    # Production mode: require valid token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = await auth_service.validate_token(credentials.credentials)
        return claims
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_role: str):
    """Dependency factory: require a specific role (hierarchy-aware)."""
    async def role_checker(
        user: TokenClaims = Depends(get_current_user),
    ) -> TokenClaims:
        if not Roles.satisfies(user.roles, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user
    return role_checker


# Predefined role dependencies - use these as Depends() directly
RequireViewer = Depends(require_role(Roles.VIEWER))
RequireAnalyst = Depends(require_role(Roles.ANALYST))
RequireAdmin = Depends(require_role(Roles.ADMIN))
