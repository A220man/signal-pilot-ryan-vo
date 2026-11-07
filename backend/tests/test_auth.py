"""Tests for OIDC authentication service and dependencies."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.api.auth import get_current_user, require_role
from app.services.auth import OIDCAuthService, Roles, TokenClaims
from app.core.config import Settings


class TestOIDCAuthService:
    @pytest.fixture
    def settings(self):
        return Settings(
            demo_mode=False,
            keycloak_server_url="https://keycloak.example.com",
            keycloak_realm="test-realm",
            keycloak_client_id="test-client",
        )

    @pytest.fixture
    def auth_service(self, settings):
        return OIDCAuthService(settings)

    def test_init_without_config_raises(self):
        """OIDCAuthService raises if Keycloak not configured."""
        settings = Settings(demo_mode=False)
        service = OIDCAuthService(settings)
        # Should not raise on init, only on validate_token

    @pytest.mark.asyncio
    async def test_validate_token_without_config_raises(self, auth_service):
        """validate_token raises RuntimeError if OIDC not configured."""
        settings = Settings(demo_mode=False)
        service = OIDCAuthService(settings)
        with pytest.raises(RuntimeError, match="Keycloak OIDC not configured"):
            await service.validate_token("some-token")

    @pytest.mark.asyncio
    async def test_validate_token_success(self, auth_service):
        """validate_token returns TokenClaims on valid token."""
        # Mock JWKS fetch
        mock_jwks = {
            "keys": [{
                "kty": "RSA",
                "kid": "test-key-id",
                "n": "test-modulus",
                "e": "AQAB",
            }]
        }
        
        payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "realm_access": {"roles": ["viewer", "analyst"]},
            "resource_access": {
                "test-client": {"roles": ["admin"]}
            },
            "exp": 9999999999,
            "iat": 1000000000,
            "iss": "https://keycloak.example.com/realms/test-realm",
            "aud": ["test-client"],
        }
        
        with patch.object(auth_service, "_fetch_jwks", AsyncMock(return_value=mock_jwks)):
            with patch("app.services.auth.jwt.get_unverified_header", return_value={"kid": "test-key-id"}):
                with patch("app.services.auth.jwt.decode", return_value=payload):
                    claims = await auth_service.validate_token("any-token")
                    
                    assert claims.sub == "user-123"
                    assert claims.username == "testuser"
                    assert claims.email == "test@example.com"
                    assert "viewer" in claims.roles
                    assert "analyst" in claims.roles
                    assert "admin" in claims.roles

    def test_has_role(self, auth_service):
        """has_role checks for specific role."""
        claims = TokenClaims(
            sub="user-1", username="u", email="e@e.com",
            roles=["viewer", "analyst"], realm_roles=[], client_roles={},
            exp=0, iat=0, iss="", aud=[]
        )
        assert auth_service.has_role(claims, "viewer")
        assert auth_service.has_role(claims, "analyst")
        assert not auth_service.has_role(claims, "admin")

    def test_has_any_role(self, auth_service):
        """has_any_role checks for any of required roles."""
        claims = TokenClaims(
            sub="user-1", username="u", email="e@e.com",
            roles=["viewer"], realm_roles=[], client_roles={},
            exp=0, iat=0, iss="", aud=[]
        )
        assert auth_service.has_any_role(claims, ["viewer", "admin"])
        assert not auth_service.has_any_role(claims, ["analyst", "admin"])

    def test_roles_hierarchy(self):
        """Roles.satisfies respects hierarchy."""
        assert Roles.satisfies(["admin"], "viewer")
        assert Roles.satisfies(["admin"], "analyst")
        assert Roles.satisfies(["admin"], "admin")
        assert Roles.satisfies(["analyst"], "viewer")
        assert Roles.satisfies(["analyst"], "analyst")
        assert not Roles.satisfies(["analyst"], "admin")
        assert Roles.satisfies(["viewer"], "viewer")
        assert not Roles.satisfies(["viewer"], "analyst")
        assert not Roles.satisfies([], "viewer")


class TestAuthDependencies:
    @pytest.fixture
    def demo_settings(self):
        return Settings(demo_mode=True)

    @pytest.mark.asyncio
    async def test_get_current_user_demo_mode(self, demo_settings):
        """get_current_user returns demo user in demo mode."""
        from app.core.config import get_settings
        # Patch get_settings to return demo settings
        with patch("app.api.auth.get_settings", return_value=demo_settings):
            with patch("app.api.auth.security") as mock_security:
                mock_security.return_value = None  # No credentials
                user = await get_current_user(None, OIDCAuthService(demo_settings))
                assert user.username == "demo"
                assert Roles.ADMIN in user.roles

    @pytest.mark.asyncio
    async def test_require_role_allows_sufficient(self, demo_settings):
        """require_role allows user with sufficient role."""
        from app.core.config import get_settings
        with patch("app.api.auth.get_settings", return_value=demo_settings):
            checker = require_role(Roles.VIEWER)
            user = TokenClaims(
                sub="u", username="u", email="e",
                roles=[Roles.ADMIN], realm_roles=[], client_roles={},
                exp=0, iat=0, iss="", aud=[]
            )
            result = await checker(user)
            assert result == user

    @pytest.mark.asyncio
    async def test_require_role_denies_insufficient(self, demo_settings):
        """require_role denies user with insufficient role."""
        checker = require_role(Roles.ADMIN)
        user = TokenClaims(
            sub="u", username="u", email="e",
            roles=[Roles.VIEWER], realm_roles=[], client_roles={},
            exp=0, iat=0, iss="", aud=[]
        )
        with pytest.raises(Exception) as exc_info:
            await checker(user)
        assert "Role 'admin' required" in str(exc_info.value)
