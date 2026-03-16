"""2026031511_QSM_038

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a
Create Date: 2026-03-15 11:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "qsmith_service"
TABLE_NAME = "operations"


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name, schema=SCHEMA)


def upgrade() -> None:
    if _has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME, schema=SCHEMA)


def downgrade() -> None:
    if _has_table(TABLE_NAME):
        return
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
