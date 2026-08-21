"""Contract test for the production API-token migration."""

from pathlib import Path

from app.models import ApiToken
from scripts.provision_db import ALL_TABLES


MIGRATION = Path(__file__).parents[2] / "migrations" / "004_api_tokens.sql"


def test_api_tokens_migration_matches_model_and_provisioning() -> None:
    sql = " ".join(MIGRATION.read_text(encoding="utf-8").split()).lower()

    assert "create table if not exists api_tokens" in sql
    assert "id serial primary key" in sql
    assert "token_hash varchar(64) not null unique" in sql
    assert "user_id integer not null references users(id) on delete cascade" in sql
    assert "created_at timestamp not null" in sql
    assert "expires_at timestamp not null" in sql
    assert "revoked_at timestamp null" in sql

    assert "api_tokens" in ALL_TABLES
    assert ApiToken.__tablename__ == "api_tokens"
    assert {
        column.name
        for column in ApiToken.__table__.columns
    } == {"id", "token_hash", "user_id", "created_at", "expires_at", "revoked_at"}
    assert ApiToken.__table__.c.token_hash.unique is True
    assert ApiToken.__table__.c.token_hash.nullable is False
    assert ApiToken.__table__.c.user_id.nullable is False
    assert ApiToken.__table__.c.created_at.nullable is False
    assert ApiToken.__table__.c.expires_at.nullable is False
    assert ApiToken.__table__.c.revoked_at.nullable is True
