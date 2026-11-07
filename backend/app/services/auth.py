"""OIDC authentication service: JWT validation, role extraction, Keycloak integration."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from jose import jwt, JWTError
from jose.utils import base64url_decode

from app.core.config import Settings


@dataclass
class TokenClaims:
    """Validated token claims with role information."""
    sub: str
    username: str
    email: str
    roles: List[str]
    realm_roles: List[str]
    client_roles: Dict[str, List[str]]
    exp: int
    iat: int
    iss: str
    aud: List[str]


class OIDCAuthService:
    """Validates OIDC tokens from Keycloak and extracts user roles."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._jwks_fetched_at: float = 0
        self._jwks_ttl = 3600  # 1 hour cache TTL

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Keycloak OIDC discovery endpoint."""
        if not self.settings.keycloak_server_url or not self.settings.keycloak_realm:
            raise RuntimeError("Keycloak OIDC not configured")

        # Check cache
        now = time.time()
        if self._jwks_cache and (now - self._jwks_fetched_at) < self._jwks_ttl:
            return self._jwks_cache

        # Build JWKS URL from server URL and realm
        jwks_url = f"{self.settings.keycloak_server_url.rstrip('/')}/realms/{self.settings.keycloak_realm}/protocol/openid-connect/certs"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_fetched_at = now
            return self._jwks_cache

    def _get_key_from_jwks(self, jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, Any]]:
        """Extract the signing key matching the kid from JWKS."""
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None

    async def validate_token(self, token: str) -> TokenClaims:
        """Validate a JWT token and extract claims with roles.

        Raises:
            JWTError: If token is invalid, expired, or signature verification fails.
            RuntimeError: If OIDC is not configured.
        """
        if not self.settings.keycloak_server_url or not self.settings.keycloak_realm:
            raise RuntimeError("Keycloak OIDC not configured")

        # Decode header to get kid
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as e:
            raise JWTError(f"Invalid token header: {e}")

        kid = header.get("kid")
        if not kid:
            raise JWTError("Token missing kid in header")

        # Fetch JWKS and get the signing key
        jwks = await self._fetch_jwks()
        key_data = self._get_key_from_jwks(jwks, kid)
        if not key_data:
            # Refresh cache once and retry
            self._jwks_cache = None
            jwks = await self._fetch_jwks()
            key_data = self._get_key_from_jwks(jwks, kid)
            if not key_data:
                raise JWTError(f"Signing key not found for kid: {kid}")

        # Construct public key from JWK
        public_key = self._jwk_to_public_key(key_data)

        # Validate token
        expected_aud = self.settings.keycloak_client_id or "account"

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=expected_aud,
                issuer=f"{self.settings.keycloak_server_url.rstrip('/')}/realms/{self.settings.keycloak_realm}",
                options={"verify_aud": True, "verify_exp": True},
            )
        except JWTError as e:
            raise JWTError(f"Token validation failed: {e}")

        # Extract roles from Keycloak token format
        realm_access = payload.get("realm_access", {})
        resource_access = payload.get("resource_access", {})

        realm_roles = realm_access.get("roles", [])
        client_roles = {}
        for client, access in resource_access.items():
            client_roles[client] = access.get("roles", [])

        # Combine all roles
        all_roles = list(set(realm_roles))
        for roles in client_roles.values():
            all_roles.extend(roles)
        all_roles = list(set(all_roles))

        return TokenClaims(
            sub=payload.get("sub", ""),
            username=payload.get("preferred_username", ""),
            email=payload.get("email", ""),
            roles=all_roles,
            realm_roles=realm_roles,
            client_roles=client_roles,
            exp=payload.get("exp", 0),
            iat=payload.get("iat", 0),
            iss=payload.get("iss", ""),
            aud=payload.get("aud", []) if isinstance(payload.get("aud"), list) else [payload.get("aud")],
        )

    def _jwk_to_public_key(self, jwk: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JWK to format suitable for python-jose."""
        if jwk.get("kty") != "RSA":
            raise ValueError(f"Unsupported key type: {jwk.get('kty')}")
        return jwk

    def has_role(self, claims: TokenClaims, required_role: str) -> bool:
        """Check if user has a specific role."""
        return required_role in claims.roles

    def has_any_role(self, claims: TokenClaims, required_roles: List[str]) -> bool:
        """Check if user has any of the required roles."""
        return any(role in claims.roles for role in required_roles)


# Role constants
class Roles:
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"

    # Hierarchy: admin > analyst > viewer
    HIERARCHY = {VIEWER: 1, ANALYST: 2, ADMIN: 3}

    @classmethod
    def satisfies(cls, user_roles: List[str], required: str) -> bool:
        """Check if user roles satisfy the required role (hierarchy-aware)."""
        user_max = max((cls.HIERARCHY.get(r, 0) for r in user_roles), default=0)
        required_level = cls.HIERARCHY.get(required, 0)
        return user_max >= required_level
