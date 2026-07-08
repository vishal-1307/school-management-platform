"""Unit tests: URL normalization, password hashing, session tokens, lockout."""

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


class TestPasswordHashing:
    def test_roundtrip(self):
        from app.services.security import hash_password, verify_password

        hashed = hash_password("S3cret!pass")
        assert hashed != "S3cret!pass"
        assert hashed.startswith("$2")  # bcrypt marker, salted per-hash
        assert verify_password("S3cret!pass", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_unusable_sentinel_never_matches(self):
        from app.services.security import UNUSABLE_HASH, verify_password

        assert verify_password("anything", UNUSABLE_HASH) is False

    def test_hashes_are_salted_uniquely(self):
        from app.services.security import hash_password

        assert hash_password("same") != hash_password("same")


class TestSessionTokens:
    def test_roundtrip_claims(self):
        from app.services.security import create_access_token, decode_token

        token, expires_at = create_access_token(42, "teacher", token_version=3)
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "teacher"
        assert payload["tv"] == 3
        assert expires_at is not None

    def test_tampered_token_rejected(self):
        from app.services.security import JWTError, create_access_token, decode_token

        token, _ = create_access_token(1, "student", token_version=0)
        with pytest.raises(JWTError):
            decode_token(token[:-4] + "AAAA")

    def test_wrong_key_rejected(self, monkeypatch):
        from app.config import settings
        from app.services.security import JWTError, create_access_token, decode_token

        token, _ = create_access_token(1, "student", token_version=0)
        monkeypatch.setattr(settings, "secret_key", "a-different-secret")
        with pytest.raises(JWTError):
            decode_token(token)


class TestRazorpayWebhookHMAC:
    """Finding #4: signature must be over the raw body bytes, not a re-dump."""

    @pytest.mark.asyncio
    async def test_valid_signature_over_raw_bytes(self, monkeypatch):
        import hashlib
        import hmac

        from app.config import settings
        from app.services.razorpay import process_webhook

        monkeypatch.setattr(settings, "razorpay_webhook_secret", "whsec_test")
        # Deliberately non-canonical key order + spacing — a re-serialization
        # via json.dumps(json.loads(body)) would NOT byte-match this.
        raw_body = b'{"event": "payment.captured",   "payload": {}}'
        signature = hmac.new(b"whsec_test", raw_body, hashlib.sha256).hexdigest()

        event = await process_webhook(raw_body, signature)
        assert event == {"event": "payment.captured", "payload": {}}

    @pytest.mark.asyncio
    async def test_tampered_body_rejected(self, monkeypatch):
        import hashlib
        import hmac

        from app.config import settings
        from app.services.razorpay import process_webhook

        monkeypatch.setattr(settings, "razorpay_webhook_secret", "whsec_test")
        raw_body = b'{"event": "payment.captured"}'
        signature = hmac.new(b"whsec_test", raw_body, hashlib.sha256).hexdigest()

        tampered = b'{"event": "payment.refunded"}'
        assert await process_webhook(tampered, signature) is None


@pytest.mark.asyncio
async def test_public_form_rate_limited(client):
    """Finding #7: public POSTs are capped per IP."""
    from app.services.ratelimit import PUBLIC_FORM_LIMITER

    PUBLIC_FORM_LIMITER._events.clear()
    for _ in range(5):
        response = await client.post(
            "/api/public/contact", json={"name": "Spammer", "message": "hi"}
        )
        assert response.status_code == 201

    sixth = await client.post(
        "/api/public/contact", json={"name": "Spammer", "message": "hi"}
    )
    assert sixth.status_code == 429
    PUBLIC_FORM_LIMITER._events.clear()


@pytest.mark.asyncio
async def test_login_lockout_after_five_failures(client):
    """Finding #1: per-ID lockout kicks in after 5 failed attempts."""
    from app.services.ratelimit import LOGIN_ID_FAILURES, LOGIN_IP_ATTEMPTS

    login_id = "EMP-001"  # real user, wrong password every time
    LOGIN_ID_FAILURES.clear(login_id.lower())

    for _ in range(5):
        response = await client.post(
            "/api/auth/login", json={"login_id": login_id, "password": "wrong"}
        )
        assert response.status_code == 401

    # Sixth attempt is refused even with the CORRECT password
    from tests.conftest import TEST_PASSWORD

    response = await client.post(
        "/api/auth/login", json={"login_id": login_id, "password": TEST_PASSWORD}
    )
    assert response.status_code == 429

    # Cleanup so other tests can use this account
    LOGIN_ID_FAILURES.clear(login_id.lower())
    LOGIN_IP_ATTEMPTS._events.clear()


@pytest.mark.asyncio
async def test_password_change_revokes_old_token(client):
    """Finding #6: token_version bump kills outstanding sessions."""
    from tests.conftest import TEST_PASSWORD

    login = await client.post(
        "/api/auth/login", json={"login_id": "ADM-00001", "password": TEST_PASSWORD}
    )
    assert login.status_code == 200
    old_token = login.json()["token"]
    old_headers = {"Authorization": f"Bearer {old_token}"}

    assert (await client.get("/api/auth/me", headers=old_headers)).status_code == 200

    change = await client.post(
        "/api/auth/change-password",
        headers=old_headers,
        json={"current_password": TEST_PASSWORD, "new_password": "NewPass@123"},
    )
    assert change.status_code == 200
    new_token = change.json()["token"]

    # Old token dead, new token alive
    assert (await client.get("/api/auth/me", headers=old_headers)).status_code == 401
    assert (
        await client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    ).status_code == 200

    # Restore original password AND token_version so the module-level
    # minted STUDENT header (tv=0) keeps working in other tests.
    from app.database import async_session_factory
    from app.models.user import User
    from app.services.security import hash_password

    async with async_session_factory() as session:
        user = await session.get(User, 3)
        user.password_hash = hash_password(TEST_PASSWORD)
        user.token_version = 0
        await session.commit()