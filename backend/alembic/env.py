from logging.config import fileConfig
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from alembic import context

# Make both 'app' (ManifestCV) and 'mystic_auth' (vendored auth template) importable.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mystic_auth.database.base import Base
from mystic_auth.user_table.user_model import User
from mystic_auth.authorization.models.policy_model import Policy, UserPolicy  # noqa: F401
from mystic_auth.authorization.models.audit_log_model import AuthorizationAuditLog  # noqa: F401
from mystic_auth.authorization.models.policy_history_model import PolicyHistory  # noqa: F401
from mystic_auth.audit_log.audit_log_model import AuditLog  # noqa: F401

# ManifestCV's own models — required here (not just wherever they're first
# imported at runtime) so `alembic revision --autogenerate` sees them even
# when invoked as a bare CLI command with nothing else importing app.* first.
from app.resume_table.resume_model import ResumeDraft  # noqa: F401
from app.career_knowledge_table.career_knowledge_model import CareerKnowledgeBase  # noqa: F401
from app.application_table.application_model import ApplicationRecord  # noqa: F401
from app.resume_document_table.resume_document_model import ResumeDocument  # noqa: F401

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in online mode with async engine."""
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def do_run_migrations(connection: Connection):
    """Run Alembic migrations using a synchronous connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
