import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ── Database URL ───────────────────────────────────────────────────────────────
# On Render, set DATABASE_URL to point to a persistent disk path or PostgreSQL:
#   SQLite on disk:  sqlite:////data/health_vault.db
#   PostgreSQL:      postgresql://user:pass@host/dbname
#
# Falls back to local SQLite in backend/data/ for development.
DATABASE_URL_ENV = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL_ENV:
    # Supabase / cloud providers often provide 'postgres://', which SQLAlchemy 1.4+ expects as 'postgresql://'
    if DATABASE_URL_ENV.startswith("postgres://"):
        DATABASE_URL_ENV = DATABASE_URL_ENV.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URL = DATABASE_URL_ENV
    # Ensure parent directory exists for SQLite file-based URLs on persistent disk
    if DATABASE_URL_ENV.startswith("sqlite:///"):
        sqlite_path = DATABASE_URL_ENV.replace("sqlite:///", "", 1)
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
else:
    # Local development default: store inside backend/data/
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH = DATA_DIR / "health_vault.db"
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLite needs check_same_thread=False; PostgreSQL does not need it
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

