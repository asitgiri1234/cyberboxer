"""initial schema

Creates the full initial schema for the Insurance Claims API:
customers, policies and claims — including primary keys, foreign keys
(ON DELETE CASCADE), indexes, unique constraints, numeric money columns,
a boolean fraud flag and server-defaulted timestamps.

Revision ID: 575cd8fc6a0b
Revises:
Create Date: 2026-07-04 19:41:34.103265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '575cd8fc6a0b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Tables are created in dependency order: customers -> policies -> claims.
    op.create_table('customers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.String(length=50), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=30), nullable=True),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_city'), 'customers', ['city'], unique=False)
    op.create_index(op.f('ix_customers_customer_id'), 'customers', ['customer_id'], unique=True)
    op.create_index(op.f('ix_customers_email'), 'customers', ['email'], unique=False)
    op.create_index(op.f('ix_customers_state'), 'customers', ['state'], unique=False)
    op.create_table('policies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('policy_id', sa.String(length=50), nullable=False),
    sa.Column('customer_id', sa.String(length=50), nullable=False),
    sa.Column('policy_type', sa.String(length=50), nullable=True),
    sa.Column('issue_date', sa.Date(), nullable=True),
    sa.Column('expiry_date', sa.Date(), nullable=True),
    sa.Column('coverage_limit', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('premium_amount', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('status', sa.String(length=30), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policies_customer_id'), 'policies', ['customer_id'], unique=False)
    op.create_index(op.f('ix_policies_policy_id'), 'policies', ['policy_id'], unique=True)
    op.create_table('claims',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('claim_id', sa.String(length=50), nullable=False),
    sa.Column('policy_id', sa.String(length=50), nullable=False),
    sa.Column('cause', sa.String(length=255), nullable=True),
    sa.Column('loss_date', sa.Date(), nullable=True),
    sa.Column('claim_date', sa.Date(), nullable=True),
    sa.Column('loss_amount', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('payout_amount', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('fraud_flag', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('status', sa.String(length=30), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['policy_id'], ['policies.policy_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_claims_cause'), 'claims', ['cause'], unique=False)
    op.create_index(op.f('ix_claims_claim_id'), 'claims', ['claim_id'], unique=True)
    op.create_index(op.f('ix_claims_loss_date'), 'claims', ['loss_date'], unique=False)
    op.create_index(op.f('ix_claims_payout_amount'), 'claims', ['payout_amount'], unique=False)
    op.create_index(op.f('ix_claims_policy_id'), 'claims', ['policy_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Dropped in reverse dependency order: claims -> policies -> customers.
    op.drop_index(op.f('ix_claims_policy_id'), table_name='claims')
    op.drop_index(op.f('ix_claims_payout_amount'), table_name='claims')
    op.drop_index(op.f('ix_claims_loss_date'), table_name='claims')
    op.drop_index(op.f('ix_claims_claim_id'), table_name='claims')
    op.drop_index(op.f('ix_claims_cause'), table_name='claims')
    op.drop_table('claims')
    op.drop_index(op.f('ix_policies_policy_id'), table_name='policies')
    op.drop_index(op.f('ix_policies_customer_id'), table_name='policies')
    op.drop_table('policies')
    op.drop_index(op.f('ix_customers_state'), table_name='customers')
    op.drop_index(op.f('ix_customers_email'), table_name='customers')
    op.drop_index(op.f('ix_customers_customer_id'), table_name='customers')
    op.drop_index(op.f('ix_customers_city'), table_name='customers')
    op.drop_table('customers')
