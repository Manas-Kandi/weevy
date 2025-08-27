"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-08-26 20:25:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # projects
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('canvas_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index('ix_projects_owner_id', 'projects', ['owner_id'], unique=False)

    # workflow_nodes
    op.create_table(
        'workflow_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_type', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('position_x', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('position_y', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_workflow_nodes_project_id', 'workflow_nodes', ['project_id'], unique=False)

    # node_connections
    op.create_table(
        'node_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflow_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('to_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflow_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_node_connections_project_id', 'node_connections', ['project_id'], unique=False)
    op.create_index('ix_node_connections_from_to', 'node_connections', ['from_node_id', 'to_node_id'], unique=False)

    # workflow_executions
    op.create_table(
        'workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'running'"), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    op.create_index('ix_workflow_exec_project_id', 'workflow_executions', ['project_id'], unique=False)
    op.create_index('ix_workflow_exec_user_id', 'workflow_executions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_workflow_exec_user_id', table_name='workflow_executions')
    op.drop_index('ix_workflow_exec_project_id', table_name='workflow_executions')
    op.drop_table('workflow_executions')

    op.drop_index('ix_node_connections_from_to', table_name='node_connections')
    op.drop_index('ix_node_connections_project_id', table_name='node_connections')
    op.drop_table('node_connections')

    op.drop_index('ix_workflow_nodes_project_id', table_name='workflow_nodes')
    op.drop_table('workflow_nodes')

    op.drop_index('ix_projects_owner_id', table_name='projects')
    op.drop_table('projects')

    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
