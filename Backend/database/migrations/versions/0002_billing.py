"""billing tables

Revision ID: 0002_billing
Revises: 0001_initial
Create Date: 2025-08-27 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_billing'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_subscriptions
    op.create_table(
        'user_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tier', sa.String(length=32), server_default=sa.text("'free'"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monthly_token_limit', sa.Integer(), nullable=True),
        sa.Column('hard_limit_tokens', sa.Integer(), nullable=True),
        sa.Column('soft_limit_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ux_user_subscriptions_user_id', 'user_subscriptions', ['user_id'], unique=True)

    # token_usage
    op.create_table(
        'token_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflow_executions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model', sa.String(length=128), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),  # YYYY-MM
        sa.Column('input_tokens', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('output_tokens', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_tokens', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('estimated_cost_usd', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_token_usage_user_period', 'token_usage', ['user_id', 'period'], unique=False)
    op.create_index('ix_token_usage_user_period_model', 'token_usage', ['user_id', 'period', 'model'], unique=False)

    # model_providers
    op.create_table(
        'model_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model', sa.String(length=128), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('is_free_tier', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('context_window', sa.Integer(), nullable=True),
        sa.Column('input_token_cost_usd', sa.Float(), nullable=True),
        sa.Column('output_token_cost_usd', sa.Float(), nullable=True),
        sa.Column('endpoint_url', sa.String(length=1024), nullable=True),
        sa.Column('pricing_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ux_model_provider_key', 'model_providers', ['provider', 'model'], unique=True)


def downgrade() -> None:
    op.drop_index('ux_model_provider_key', table_name='model_providers')
    op.drop_table('model_providers')

    op.drop_index('ix_token_usage_user_period_model', table_name='token_usage')
    op.drop_index('ix_token_usage_user_period', table_name='token_usage')
    op.drop_table('token_usage')

    op.drop_index('ux_user_subscriptions_user_id', table_name='user_subscriptions')
    op.drop_table('user_subscriptions')
