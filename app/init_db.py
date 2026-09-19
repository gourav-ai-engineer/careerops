from app.database import Base, engine
from app.migration_runner import apply_migrations
from app import models  # noqa: F401 - register SQLAlchemy models before create_all


def main() -> None:
    Base.metadata.create_all(bind=engine)
    applied = apply_migrations(engine)
    print(f"CareerOps database initialized. Applied migrations: {applied}")


if __name__ == "__main__":
    main()
