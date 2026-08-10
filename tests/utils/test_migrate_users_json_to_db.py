"""Tests for scripts/migrate_users_json_to_db.py — idempotent JSON→DB seed.

Strict TDD: the core function ``migrate_users_json_to_db()`` is described
here BEFORE the script is implemented (RED). Uses an in-memory SQLite
engine + a temp users.json so no PostgreSQL server or real data is needed.

Covers (task 1.4):
- upsert by username preserving password_hash
- idempotency (second run: no duplicates, zero inserts)
- backup of instance/users.json created
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import Base
from app.models import User
import app.models  # noqa: F401

sys.path.insert(0, str(Path("scripts").resolve()))
import migrate_users_json_to_db as migrator  # noqa: E402


@pytest.fixture
def db_session():
    """In-memory SQLite sessionmaker + schema."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _write_users_json(tmp_path: Path, users: list) -> Path:
    path = tmp_path / "users.json"
    path.write_text(json.dumps(users, ensure_ascii=False), encoding="utf-8")
    return path


def _sample_users() -> list:
    return [
        {
            "username": "admin",
            "password_hash": generate_password_hash("admin123"),
            "rol": "admin",
            "permisos": ["*"],
            "primer_nombre": "Alexis",
            "segundo_nombre": "",
            "apellido_1": "Aguirre",
            "apellido_2": "",
        },
        {
            "username": "LORENYA",
            "password_hash": generate_password_hash("loreny123"),
            "rol": "facturador",
            "permisos": ["urgencias", "control_urgencias", "facturas_abiertas"],
            "primer_nombre": "LORENY ",
            "segundo_nombre": "ALEJANDRA",
            "apellido_1": "ESPAÑA ",
            "apellido_2": "DIAZ ",
        },
    ]


class TestMigrateUsersJsonToDb:
    """Task 1.4: idempotent upsert preserving password_hash + backup."""

    def test_seeds_users_preserving_hash(self, db_session, tmp_path):
        """Users inserted; password_hash equals the JSON hash (checkable)."""
        users = _sample_users()
        json_path = _write_users_json(tmp_path, users)

        result = migrator.migrate_users_json_to_db(json_path, session_factory=db_session)

        assert result["inserted"] == 2
        assert result["updated"] == 0

        db = db_session()
        try:
            admin = db.query(User).filter(User.username == "admin").first()
            assert admin is not None
            assert admin.password_hash == users[0]["password_hash"]
            assert check_password_hash(admin.password_hash, "admin123")
            assert admin.rol == "admin"
            assert admin.permisos == ["*"]
            assert admin.primer_nombre == "Alexis"
            assert admin.segundo_nombre == ""
            assert admin.apellido_1 == "Aguirre"
            assert admin.apellido_2 == ""

            lorenya = db.query(User).filter(User.username == "LORENYA").first()
            assert lorenya is not None
            assert lorenya.rol == "facturador"
            assert lorenya.primer_nombre == "LORENY "
            assert lorenya.apellido_1 == "ESPAÑA "
        finally:
            db.close()

    def test_idempotent_second_run(self, db_session, tmp_path):
        """Running twice: no duplicates, zero inserts on the second run."""
        users = _sample_users()
        json_path = _write_users_json(tmp_path, users)

        first = migrator.migrate_users_json_to_db(json_path, session_factory=db_session)
        second = migrator.migrate_users_json_to_db(json_path, session_factory=db_session)

        assert first["inserted"] == 2
        assert second["inserted"] == 0
        assert second["updated"] == 0

        db = db_session()
        try:
            assert db.query(User).count() == 2
        finally:
            db.close()

    def test_upsert_updates_existing_row(self, db_session, tmp_path):
        """Existing username with changed fields → updated, not duplicated."""
        users = _sample_users()
        json_path = _write_users_json(tmp_path, users)
        migrator.migrate_users_json_to_db(json_path, session_factory=db_session)

        # Cambiar rol en el JSON y volver a migrar
        users[1]["rol"] = "validador"
        json_path.write_text(json.dumps(users, ensure_ascii=False), encoding="utf-8")
        result = migrator.migrate_users_json_to_db(json_path, session_factory=db_session)

        assert result["inserted"] == 0
        assert result["updated"] == 1

        db = db_session()
        try:
            lorenya = db.query(User).filter(User.username == "LORENYA").first()
            assert lorenya.rol == "validador"
            assert db.query(User).count() == 2
        finally:
            db.close()

    def test_upsert_does_not_delete_users_missing_from_json(self, db_session, tmp_path):
        """Provisioning is additive/upsert-only, never a destructive sync."""
        users = _sample_users()
        json_path = _write_users_json(tmp_path, users[:1])
        db = db_session()
        try:
            db.add(User(
                username=users[0]["username"],
                password_hash=users[0]["password_hash"],
                rol=users[0]["rol"],
                permisos=users[0]["permisos"],
                primer_nombre=users[0]["primer_nombre"],
                segundo_nombre=users[0]["segundo_nombre"],
                apellido_1=users[0]["apellido_1"],
                apellido_2=users[0]["apellido_2"],
            ))
            db.add(User(
                username="existing_only_in_db",
                password_hash="existing-hash",
                rol="usuario",
                permisos=[],
            ))
            db.commit()
        finally:
            db.close()

        result = migrator.migrate_users_json_to_db(json_path, session_factory=db_session)

        assert result["inserted"] == 0
        assert result["updated"] == 0
        db = db_session()
        try:
            assert db.query(User).count() == 2
            assert db.query(User).filter_by(username="existing_only_in_db").one()
        finally:
            db.close()

    def test_creates_backup_of_json(self, db_session, tmp_path):
        """Backup file (users.json.bak) created next to the source JSON."""
        users = _sample_users()
        json_path = _write_users_json(tmp_path, users)

        migrator.migrate_users_json_to_db(json_path, session_factory=db_session)

        backup = json_path.with_name("users.json.bak")
        assert backup.exists()
        backup_data = json.loads(backup.read_text(encoding="utf-8"))
        assert len(backup_data) == 2
        # El backup conserva el password_hash original
        assert backup_data[0]["password_hash"] == users[0]["password_hash"]

    def test_empty_json_migrates_zero(self, db_session, tmp_path):
        """Empty list → zero inserted, backup still created."""
        json_path = _write_users_json(tmp_path, [])
        result = migrator.migrate_users_json_to_db(json_path, session_factory=db_session)

        assert result["inserted"] == 0
        assert json_path.with_name("users.json.bak").exists()
