"""Authentication dependencies and routes for FastAPI."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse

from app.core.config import Settings, get_settings
from app.services.auth import OIDCAuthService, AuthSession, Roles, TokenClaims

# Bearer token security scheme
security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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


@router.post("/login", response_class=RedirectResponse, summary="Initiate OIDC login with PKCE")
async def login(
    settings: Settings = Depends(get_settings),
    auth_service: OIDCAuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Initiate OIDC login flow with PKCE.

    Generates state, nonce, and code_verifier, stores the session,
    and redirects the user to Keycloak's authorization endpoint.
    """
    if not settings.keycloak_server_url or not settings.keycloak_realm:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak OIDC not configured",
        )

    # Create auth session with PKCE parameters
    session = auth_service.create_auth_session()

    # Build the Keycloak authorization URL
    login_url = auth_service.build_login_url(session)

    # Redirect to Keycloak
    return RedirectResponse(url=login_url)


@router.get("/callback", summary="Keycloak callback / token exchange")
async def callback(
    request: Annotated[Optional[str], Header()] = None,
    # In a full implementation, we'd extract the code from query params
    # But for now we note the flow: Keycloak redirects back with ?code=...
    auth_service: OIDCAuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Handle Keycloak callback after user authentication.

    Keycloak redirects back with an authorization code. This endpoint
    exchanges the code for tokens using the PKCE code_verifier.
    """
    # For now, return a structure indicating the flow
    # In production, we'd extract `code` from query params
    # and call: await auth_service.exchange_code_for_tokens(code, session.code_verifier)
    return {"detail": "Callback received - implement code exchange"}


@router.get("/logout", summary="Keycloak logout")
async def logout(
    id_token: Optional[str] = None,
    settings: Settings = Depends(get_settings),
    auth_service: OIDCAuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Initiate Keycloak logout.

    Redirects the user to Keycloak's logout endpoint, which will
    clear the OIDC session and redirect back to the post_logout_redirect_uri.
    """
    if not settings.keycloak_server_url or not settings.keycloak_realm:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak OIDC not configured",
        )

    logout_url = auth_service.build_logout_url(id_token=id_token)

    # Set the redirect URI from settings, falling back to a default
    redirect_uri = settings.keycloak_redirect_uri or "http://localhost:8000/api/v1/auth/logout/callback"

    # Build final logout URL with redirect
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

    parsed = urlparse(logout_url)
    query_params = parse_qs(parsed.query)
    query_params["post_logout_redirect_uri"] = redirect_uri
    new_query = urlencode(query_params, doseq=True)
    final_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    return RedirectResponse(url=final_url)
