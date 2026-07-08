"""Unit tests: URL normalization, CORS parsing, webhook HMAC, JWKS RS256."""

import base64
import hashlib
import hmac

import pytest

from app.config import normalize_database_url


class TestNormalizeDatabaseUrl:
    def test_neon_url_params_stripped(self):
        url, ssl = normalize_database_url(
            "postgresql://u:p@ep-x-pooler.aws.neon.tech/db?sslmode=require&channel_binding=require"
        )
        assert url == "postgresql+asyncpg://u:p@ep-x-pooler.aws.neon.tech/db"
        assert ssl is True

    def test_heroku_scheme(self):
        url, ssl = normalize_database_url("postgres://u:p@host/db")
        assert url.startswith("postgresql+asyncpg://")
        assert ssl is False

    def test_sslmode_disable(self):
        _, ssl = normalize_database_url("postgresql://u:p@host/db?sslmode=disable")
        assert ssl is False

    def test_other_params_kept(self):
        url, _ = normalize_database_url(
            "postgresql://u:p@host/db?sslmode=require&application_name=school"
        )
        assert "application_name=school" in url
        assert "sslmode" not in url

    def test_sqlite_untouched(self):
        url, ssl = normalize_database_url("sqlite+aiosqlite:///./school.db")
        assert url == "sqlite+aiosqlite:///./school.db"
        assert ssl is False


class TestClerkWebhookVerify:
    def _make(self, secret_bytes: bytes, body: bytes, msg_id="msg_1", ts="1720000000"):
        signed = f"{msg_id}.{ts}.".encode() + body
        return base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()

    def test_valid_signature(self, monkeypatch):
        from app.config import settings
        from app.services.clerk import verify_webhook

        secret = b"super-secret"
        monkeypatch.setattr(
            settings, "clerk_webhook_secret", "whsec_" + base64.b64encode(secret).decode()
        )
        body = b'{"type":"user.updated"}'
        signature = self._make(secret, body)
        headers = {"svix-id": "msg_1", "svix-timestamp": "1720000000", "svix-signature": f"v1,{signature}"}
        assert verify_webhook(headers, body) is True

    def test_invalid_signature(self, monkeypatch):
        from app.config import settings
        from app.services.clerk import verify_webhook

        monkeypatch.setattr(
            settings, "clerk_webhook_secret", "whsec_" + base64.b64encode(b"k").decode()
        )
        headers = {"svix-id": "m", "svix-timestamp": "1", "svix-signature": "v1,AAAA"}
        assert verify_webhook(headers, b"{}") is False

    def test_unconfigured(self, monkeypatch):
        from app.config import settings
        from app.services.clerk import verify_webhook

        monkeypatch.setattr(settings, "clerk_webhook_secret", "")
        assert verify_webhook({}, b"{}") is False


@pytest.mark.asyncio
async def test_jwks_rs256_verification(monkeypatch, client):
    """Full RS256 path: local keypair, patched JWKS fetch, real user lookup."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jose import jwt
    from jose.backends.cryptography_backend import CryptographyRSAKey
    from jose.constants import ALGORITHMS

    import app.middleware.auth as auth_module
    from app.config import settings

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

    public_jwk = CryptographyRSAKey(private_key.public_key(), ALGORITHMS.RS256).to_dict()
    public_jwk["kid"] = "test-key"

    async def fake_fetch(force: bool = False):
        return [public_jwk]

    monkeypatch.setattr(auth_module, "_fetch_jwks", fake_fetch)
    # Real-Clerk path requires dev-auth to be off for JWT branch coverage
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test_dummy")
    monkeypatch.setattr(settings, "clerk_issuer", "")

    token = jwt.encode(
        {"sub": "dev-admin"}, private_pem, algorithm="RS256", headers={"kid": "test-key"}
    )
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "super_admin"

    # Tampered token fails
    bad = token[:-4] + "AAAA"
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"})
    assert response.status_code == 401
