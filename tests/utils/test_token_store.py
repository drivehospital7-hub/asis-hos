"""Strict TDD RED tests for the API token store (Phase 1, task 1.1).

The token store manages DB-backed hashed bearer tokens tied to validator
users, with issue/rotate/revoke lifecycle and expiry. These tests describe
the behavior the store MUST implement.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.utils import token_store
import app.models  # noqa: F401  (registra ApiToken/User en Base.metadata)


@pytest.fixture(autouse=True)
def _token_db():
    """SQLite en memoria parcheado en token_store.SessionLocal.

    Crea la tabla api_tokens y siembra un usuario validador 'ana'.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    from app.models import User
    from werkzeug.security import generate_password_hash

    seed_db = Session()
    try:
        seed_db.add(User(
            username="ana",
            password_hash=generate_password_hash("pass123"),
            rol="validador",
            permisos=["control_urgencias:write"],
            primer_nombre="Ana",
            segundo_nombre="",
            apellido_1="Valdez",
            apellido_2="",
        ))
        seed_db.commit()
    finally:
        seed_db.close()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(token_store, "SessionLocal", Session)
        yield Session


class TestIssue:
    def test_issue_stores_only_hash_not_plaintext(self):
        """Issuing a token MUST NOT persist the raw token anywhere."""
        raw, record = token_store.issue_token("ana")

        # The returned record must NOT leak the raw token
        assert raw not in str(record)

        db = token_store.SessionLocal()
        try:
            from app.models import ApiToken, User
            import hashlib
            user = db.query(User).filter_by(username="ana").one()
            stored = db.query(ApiToken).filter_by(user_id=user.id).first()
            assert stored is not None
            # Only the SHA-256 hash is persisted, never the raw token
            assert stored.token_hash == hashlib.sha256(raw.encode()).hexdigest()
            assert stored.token_hash != raw
            assert raw not in stored.token_hash
        finally:
            db.close()

    def test_issue_links_to_validator_user(self):
        """The token record references the user_id of the validator."""
        db = token_store.SessionLocal()
        try:
            from app.models import User
            user_id = db.query(User).filter_by(username="ana").one().id
        finally:
            db.close()

        raw, record = token_store.issue_token("ana")
        assert record["user_id"] == user_id
        assert record["username"] == "ana"
        assert record["revoked_at"] is None
        assert record["expires_at"] is not None


class TestRotate:
    def test_rotate_rejects_old_and_accepts_new(self):
        """After rotation the old token MUST fail auth and the new MUST pass."""
        old_raw, record = token_store.issue_token("ana")

        # Old token authenticates before rotation
        assert token_store.get_user_for_token(old_raw) is not None

        new_raw, new_record = token_store.rotate_token(record["id"])

        assert new_raw != old_raw
        # Old token now rejected
        assert token_store.get_user_for_token(old_raw) is None
        # New token authenticates
        assert token_store.get_user_for_token(new_raw) is not None


class TestRevoke:
    def test_revoke_immediately_rejects(self):
        """A revoked token MUST be rejected with 401-equivalent (None)."""
        raw, record = token_store.issue_token("ana")
        assert token_store.get_user_for_token(raw) is not None

        ok = token_store.revoke_token(record["id"])
        assert ok is True
        assert token_store.get_user_for_token(raw) is None


class TestExpiry:
    def test_expired_token_rejected(self):
        """A token past its expiry MUST be rejected."""
        db = token_store.SessionLocal()
        try:
            from app.models import User
            user_id = db.query(User).filter_by(username="ana").one().id
        finally:
            db.close()

        from app.models import ApiToken
        import hashlib

        # Craft a token already expired
        raw = "expired-token-value"
        db = token_store.SessionLocal()
        try:
            db.add(ApiToken(
                token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                user_id=user_id,
                created_at=datetime.now(timezone.utc) - timedelta(days=10),
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            ))
            db.commit()
        finally:
            db.close()

        assert token_store.get_user_for_token(raw) is None


class TestTimezoneAware:
    """Timestamps MUST not use the deprecated datetime.utcnow() and must
    remain consistent with what the DB returns on read (naive UTC)."""

    def test_issue_token_does_not_warn_utcnow_deprecation(self):
        """issuing a token must not raise the datetime.utcnow DeprecationWarning."""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            raw, record = token_store.issue_token("ana")

        assert token_store.get_user_for_token(raw) is not None

    def test_issued_timestamps_consistent_and_authenticate(self):
        """issued timestamps are valid UTC with the configured TTL, and the
        token authenticates (DB read-back stays consistent, no TypeError)."""
        raw, record = token_store.issue_token("ana")

        created = datetime.fromisoformat(record["created_at"])
        expires = datetime.fromisoformat(record["expires_at"])
        # TTL is exactly API_TOKEN_TTL_DAYS (90) regardless of tz round-trip
        assert (expires - created).days == 90
        # A freshly issued token still authenticates after the change
        assert token_store.get_user_for_token(raw) is not None

    def test_expired_aware_token_rejected(self):
        """An aware, past-expiry token MUST be rejected (no TypeError)."""
        db = token_store.SessionLocal()
        try:
            from app.models import User
            user_id = db.query(User).filter_by(username="ana").one().id
        finally:
            db.close()

        from app.models import ApiToken
        import hashlib

        raw = "aware-expired-token"
        db = token_store.SessionLocal()
        try:
            db.add(ApiToken(
                token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                user_id=user_id,
                created_at=datetime.now(timezone.utc) - timedelta(days=10),
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            ))
            db.commit()
        finally:
            db.close()

        assert token_store.get_user_for_token(raw) is None


class TestList:
    def test_list_exposes_no_hashes(self):
        """list_tokens MUST NOT expose token hashes."""
        token_store.issue_token("ana")
        tokens = token_store.list_tokens()

        assert len(tokens) == 1
        assert tokens[0]["username"] == "ana"
        assert "token_hash" not in tokens[0]
        assert "hash" not in tokens[0]
