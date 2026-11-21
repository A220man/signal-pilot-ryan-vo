"""Authentication dependencies and routes for FastAPI."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse

from app.core.config import Settings, get_settings
from app.services.auth import OIDCAuthService, AuthSession, Roles, TokenClaims

# Bearer token security scheme
security = HTTPBearer(auto_error=False)

router = APIRouter(tags=["auth"])


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
    code: Annotated[Optional[str], Query()] = None,
    state: Annotated[Optional[str], Query()] = None,
    auth_service: OIDCAuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Handle Keycloak callback after user authentication.

    Keycloak redirects back with an authorization code. This endpoint
    exchanges the code for tokens using the PKCE code_verifier.
    """
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code and state required",
        )

    # Retrieve and consume the auth session by state (one-time use)
    session = auth_service.get_and_consume_session(state)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    # Exchange the authorization code for tokens
    try:
        token_response = await auth_service.exchange_code_for_tokens(
            code=code,
            code_verifier=session.code_verifier,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {e}",
        )

    # Validate the ID token if present
    id_token = token_response.get("id_token")
    if id_token:
        try:
            claims = await auth_service.validate_token(id_token)
        except Exception:
            # If token validation fails, still return token response
            # but with a warning
            pass
    else:
        # No ID token - we can still get basic user info
        # from the token response or try to validate access token
        pass

    # Extract user info from claims or token response
    user_sub = None
    user_username = None
    if 'claims' in dir() and claims:
        user_sub = claims.sub
        user_username = claims.username
    elif token_response and token_response.get("id_token"):
        # Try to decode the ID token payload
        from jose import jwt as jose_jwt
        try:
            header = jose_jwt.get_unverified_header(token_response["id_token"])
            # We can't fully decode without validation, but return what we have
            user_sub = header.get("typ", None)
        except Exception:
            pass

    return {
        "detail": "Callback successful",
        "token_response": token_response,
        "sub": user_sub,
        "username": user_username,
    }


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
