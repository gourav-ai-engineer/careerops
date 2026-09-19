from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _clean_statement(statement: str) -> str:
    return "\n".join(line for line in statement.splitlines() if not line.strip().startswith("--")).strip()


def apply_migrations(engine: Engine) -> list[str]:
    applied: list[str] = []
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
            )
        )
        done = {row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = path.name
            if version in done:
                continue
            statements = [_clean_statement(s) for s in path.read_text(encoding="utf-8").split(";")]
            for statement in statements:
                if statement:
                    connection.execute(text(statement))
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (:version)"), {"version": version})
            applied.append(version)
    return applied
