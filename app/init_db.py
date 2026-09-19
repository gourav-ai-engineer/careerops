from sqlalchemy import text

from app.database import Base, engine
from app import models  # noqa: F401


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS linkedin_url TEXT"
        ))
    print("CareerOps database tables created/updated.")
