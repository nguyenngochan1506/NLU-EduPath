"""relax_score_range_and_bigint_quota

Revision ID: 2feecbc446a5
Revises: 001
Create Date: 2026-03-04 21:51:24.580162+07:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2feecbc446a5'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old constraint
    op.drop_constraint('chk_cutoff_score_range', 'admission_scores', type_='check')
    
    # 2. Add new relaxed constraint (0-100 for composite scores)
    op.create_check_constraint(
        'chk_cutoff_score_range',
        'admission_scores',
        'cutoff_score IS NULL OR (cutoff_score >= 0.0 AND cutoff_score <= 100.0)'
    )
    
    # 3. Alter quota to BigInteger to avoid overflow
    op.alter_column('admission_scores', 'quota',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger())


def downgrade() -> None:
    # 1. Revert quota to Integer
    op.alter_column('admission_scores', 'quota',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER())
    
    # 2. Revert constraint to 10-30
    op.drop_constraint('chk_cutoff_score_range', 'admission_scores', type_='check')
    op.create_check_constraint(
        'chk_cutoff_score_range',
        'admission_scores',
        'cutoff_score IS NULL OR (cutoff_score >= 10.0 AND cutoff_score <= 30.0)'
    )
