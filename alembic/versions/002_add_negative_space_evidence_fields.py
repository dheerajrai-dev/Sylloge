"""002_add_negative_space_evidence_fields

Revision ID: 002_add_negative_space_evidence_fields
Revises: 001_initial_schema
Create Date: 2026-09-20 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

from shared.db.base import JSONType

# revision identifiers, used by Alembic.
revision: str = '002_add_negative_space_evidence_fields'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'negative_space_findings',
        sa.Column('raw_evidence_refs', JSONType, nullable=False, server_default='[]')
    )
    op.add_column(
        'negative_space_findings',
        sa.Column('metric_values', JSONType, nullable=False, server_default='{}')
    )


def downgrade() -> None:
    op.drop_column('negative_space_findings', 'metric_values')
    op.drop_column('negative_space_findings', 'raw_evidence_refs')
