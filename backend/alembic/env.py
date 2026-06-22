from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
import sys
import os
from dotenv import load_dotenv

# .env is in project root: RECRUTIMENT/.env (two levels up from alembic/ folder)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import Base
from app.models import (  # noqa: F401
    Candidate, Experience, Education, Skill,
    CandidateVersion, CandidateNote, SearchLog
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Read DB URL from environment — fallback to hardcoded if .env not found
DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://recruit:recruit_secret@127.0.0.1:5435/recruitment"
)


def run_migrations_offline():
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(DB_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
