#!/usr/bin/env python3
import os
import shutil

services = [
    'user-service', 'homework-service', 'material-service', 
    'notification-service', 'analytics-service', 'student-service', 'api-gateway'
]

# Template files
env_template = '''from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from app.models import Base
except ImportError:
    # Fallback if models don't exist yet
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def get_url():
    service_name = "{service_db_name}"
    return os.getenv(f"DATABASE_URL_{service_name.upper()}", "postgresql://user:pass@localhost/dbname")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

script_template = '''"""${{message}}

Revision ID: ${{up_revision}}
Revises: ${{down_revision | comma,n}}
Create Date: ${{create_date}}

"""
from alembic import op
import sqlalchemy as sa
${{imports if imports else ""}}

# revision identifiers, used by Alembic.
revision = ${{repr(up_revision)}}
down_revision = ${{repr(down_revision)}}
branch_labels = ${{repr(branch_labels)}}
depends_on = ${{repr(depends_on)}}


def upgrade() -> None:
    ${{upgrades if upgrades else "pass"}}


def downgrade() -> None:
    ${{downgrades if downgrades else "pass"}}
'''

readme_content = "Generic single-database configuration."

# Service name mapping for database URLs
service_db_mapping = {
    'user-service': 'USER',
    'homework-service': 'HOMEWORK', 
    'material-service': 'MATERIAL',
    'notification-service': 'NOTIFICATION',
    'analytics-service': 'ANALYTICS',
    'student-service': 'STUDENT',
    'api-gateway': 'GATEWAY'
}

for service in services:
    alembic_dir = f"services/{service}/alembic"
    versions_dir = f"{alembic_dir}/versions"
    
    # Create directories
    os.makedirs(alembic_dir, exist_ok=True)
    os.makedirs(versions_dir, exist_ok=True)
    
    # Create env.py with service-specific database name
    db_name = service_db_mapping.get(service, service.upper().replace('-', '_'))
    env_content = env_template.replace('{service_db_name}', db_name)
    
    with open(f"{alembic_dir}/env.py", 'w') as f:
        f.write(env_content)
    
    # Create script.py.mako
    with open(f"{alembic_dir}/script.py.mako", 'w') as f:
        f.write(script_template)
    
    # Create README
    with open(f"{alembic_dir}/README", 'w') as f:
        f.write(readme_content)
    
    print(f"Created alembic structure for {service}")

print("All alembic structures created!")