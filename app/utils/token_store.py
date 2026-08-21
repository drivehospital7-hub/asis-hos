"""Almacenamiento de tokens de integración en la base de datos.

Tokens de bearer para la integración LAN JSON de control-novedades. Solo se
persiste el hash SHA-256 del token; el valor en claro se devuelve una única
vez al emitir o rotar. API pública: issue_token / rotate_token / revoke_token
/ list_tokens / get_user_for_token.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from app.constants.base import API_TOKEN_TTL_DAYS
from app.database import SessionLocal
from app.models import ApiToken, User

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Fecha/hora UTC actual (naive) para persistir en columnas DateTime.

    Reemplaza el obsoleto ``datetime.utcnow()`` usando el reloj con zona horaria
    ``datetime.now(timezone.utc)`` y luego quitando el tzinfo: SQLite y
    PostgreSQL ``TIMESTAMP WITHOUT TIME ZONE`` devuelven valores naive al leer,
    así que guardamos naive-UTC para que las comparaciones (``expires_at < now``)
    sean siempre consistentes y no arrojen TypeError entre aware y naive.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_token(raw: str) -> str:
    """SHA-256 del token en claro (los tokens son secretos de alta entropía)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_raw_token() -> str:
    """Genera un token en claro de alta entropía."""
    return secrets.token_urlsafe(48)


def _user_dict(user: User) -> dict:
    """Serializa el usuario dueño del token (sin password_hash)."""
    return {
        "id": user.id,
        "username": user.username,
        "rol": user.rol,
        "permisos": user.permisos or [],
        "primer_nombre": user.primer_nombre or "",
        "segundo_nombre": user.segundo_nombre or "",
        "apellido_1": user.apellido_1 or "",
        "apellido_2": user.apellido_2 or "",
    }


def issue_token(username: str, ttl_days: int | None = None) -> tuple[str, dict]:
    """Emite un token nuevo para el usuario, devolviendo el valor en claro una vez.

    Returns:
        (raw_token, record_dict). Solo el hash se persiste; el valor en claro
        no puede recuperarse después.
    """
    ttl_days = ttl_days or API_TOKEN_TTL_DAYS
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise ValueError(f"Usuario no encontrado: {username}")

        raw = _generate_raw_token()
        now = _utcnow()
        record = ApiToken(
            token_hash=_hash_token(raw),
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(days=ttl_days),
            revoked_at=None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        data = record.to_dict()
        data["username"] = user.username
        logger.info("[BACK] Token emitido para '%s' (id=%s)", username, record.id)
        return raw, data
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _record_dict(record: ApiToken, username: str | None = None) -> dict:
    data = record.to_dict()
    if username:
        data["username"] = username
    return data


def rotate_token(token_id: int) -> tuple[str, dict]:
    """Rota un token: revoca el actual y emite uno nuevo para el mismo usuario.

    Returns:
        (new_raw_token, new_record_dict). El token anterior queda revocado.
    """
    db = SessionLocal()
    try:
        record = db.query(ApiToken).filter(ApiToken.id == token_id).first()
        if record is None:
            raise ValueError(f"Token no encontrado: {token_id}")

        user = db.query(User).filter(User.id == record.user_id).first()
        username = user.username if user else None

        # Revocar el token actual
        record.revoked_at = _utcnow()
        db.flush()

        # Emitir uno nuevo
        raw = _generate_raw_token()
        now = _utcnow()
        new_record = ApiToken(
            token_hash=_hash_token(raw),
            user_id=record.user_id,
            created_at=now,
            expires_at=now + timedelta(days=API_TOKEN_TTL_DAYS),
            revoked_at=None,
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        logger.info("[BACK] Token %s rotado → nuevo id=%s", token_id, new_record.id)
        return raw, _record_dict(new_record, username)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def revoke_token(token_id: int) -> bool:
    """Revoca un token activo para que sea rechazado de inmediato."""
    db = SessionLocal()
    try:
        record = db.query(ApiToken).filter(ApiToken.id == token_id).first()
        if record is None or record.revoked_at is not None:
            return False
        record.revoked_at = _utcnow()
        db.commit()
        logger.info("[BACK] Token %s revocado", token_id)
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_tokens() -> list[dict]:
    """Lista los tokens activos sin exponer hashes."""
    db = SessionLocal()
    try:
        records = db.query(ApiToken).order_by(ApiToken.created_at).all()
        result = []
        for record in records:
            user = db.query(User).filter(User.id == record.user_id).first()
            result.append(_record_dict(record, user.username if user else None))
        return result
    finally:
        db.close()


def get_user_for_token(raw_token: str) -> dict | None:
    """Resuelve un token en claro al usuario dueño, o None si inválido.

    Rechaza tokens desconocidos, revocados o vencidos.
    """
    if not raw_token:
        return None
    token_hash = _hash_token(raw_token)
    db = SessionLocal()
    try:
        record = (
            db.query(ApiToken)
            .filter(ApiToken.token_hash == token_hash)
            .first()
        )
        if record is None:
            return None
        now = _utcnow()
        if record.revoked_at is not None:
            return None
        if record.expires_at is None or record.expires_at < now:
            return None
        user = db.query(User).filter(User.id == record.user_id).first()
        if user is None:
            return None
        return _user_dict(user)
    finally:
        db.close()
