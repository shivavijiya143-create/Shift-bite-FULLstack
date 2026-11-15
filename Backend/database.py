
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker, DeclarativeBase


# =====================================================
# PROJECT PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent


# =====================================================
# LOAD ENVIRONMENT VARIABLES
# =====================================================

# Load local .env without overriding hosting variables
load_dotenv(BASE_DIR / ".env", override=False)


# =====================================================
# TIDB CLOUD DATABASE CONFIGURATION
# =====================================================

TIDB_HOST = os.getenv("TIDB_HOST")

if TIDB_HOST:
    required_variables = [
        "TIDB_USER",
        "TIDB_PASSWORD",
        "TIDB_DB_NAME",
    ]

    missing_variables = [
        name for name in required_variables if not os.getenv(name)
    ]

    if missing_variables:
        raise RuntimeError(
            "Missing database environment variables: "
            + ", ".join(missing_variables)
        )

    DATABASE_URL = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("TIDB_USER"),
        password=os.getenv("TIDB_PASSWORD"),
        host=TIDB_HOST,
        port=int(os.getenv("TIDB_PORT", "4000")),
        database=os.getenv("TIDB_DB_NAME"),
    )

else:
    # Optional fallback for local development
    DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise RuntimeError("Database configuration is missing")


# =====================================================
# SSL CONFIGURATION
# =====================================================

connect_args = {}

if os.getenv("DB_SSL", "false").lower() == "true":

    ca_path_value = os.getenv("CA_PATH")

    if not ca_path_value:
        raise RuntimeError(
            "CA_PATH is missing from environment"
        )

    ca_path = Path(ca_path_value)

    if not ca_path.is_absolute():
        ca_path = BASE_DIR / ca_path

    ca_path = ca_path.resolve()

    if not ca_path.is_file():
        raise RuntimeError(
            f"TiDB CA certificate not found: {ca_path}"
        )

    connect_args = {
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
        "ssl_ca": str(ca_path),
    }


# =====================================================
# DATABASE ENGINE
# =====================================================

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
)


# =====================================================
# DATABASE SESSION
# =====================================================

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# =====================================================
# SQLALCHEMY BASE
# =====================================================

class Base(DeclarativeBase):
    pass


# =====================================================
# FASTAPI DATABASE DEPENDENCY
# =====================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
