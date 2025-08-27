import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# Users & Authentication
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="owner")
    # Billing relationships
    subscription: Mapped[Optional["UserSubscription"]] = relationship(
        "UserSubscription", back_populates="user", uselist=False
    )
    token_usages: Mapped[list["TokenUsage"]] = relationship(
        "TokenUsage", back_populates="user"
    )


# Projects (Workflow Containers)
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canvas_data: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    owner: Mapped[Optional[User]] = relationship("User", back_populates="projects")
    nodes: Mapped[list["WorkflowNode"]] = relationship(
        "WorkflowNode", back_populates="project", cascade="all, delete-orphan"
    )
    connections: Mapped[list["NodeConnection"]] = relationship(
        "NodeConnection", back_populates="project", cascade="all, delete-orphan"
    )
    executions: Mapped[list["WorkflowExecution"]] = relationship(
        "WorkflowExecution", back_populates="project", cascade="all, delete-orphan"
    )


# Workflow Nodes
class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    configuration: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[Project] = relationship("Project", back_populates="nodes")
    outgoing_connections: Mapped[list["NodeConnection"]] = relationship(
        "NodeConnection",
        foreign_keys=lambda: [NodeConnection.from_node_id],
        back_populates="from_node",
        cascade="all, delete-orphan",
    )
    incoming_connections: Mapped[list["NodeConnection"]] = relationship(
        "NodeConnection",
        foreign_keys=lambda: [NodeConnection.to_node_id],
        back_populates="to_node",
        cascade="all, delete-orphan",
    )


# Node Connections
class NodeConnection(Base):
    __tablename__ = "node_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    from_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False)
    to_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship("Project", back_populates="connections")
    from_node: Mapped[WorkflowNode] = relationship("WorkflowNode", foreign_keys=[from_node_id], back_populates="outgoing_connections")
    to_node: Mapped[WorkflowNode] = relationship("WorkflowNode", foreign_keys=[to_node_id], back_populates="incoming_connections")


# Workflow Executions
class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="executions")
    user: Mapped[Optional[User]] = relationship("User")


# Billing & Model Provider Tables
class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), default="free", nullable=False)  # e.g., free, pro, enterprise
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    monthly_token_limit: Mapped[int | None] = mapped_column(nullable=True)  # null means unlimited
    hard_limit_tokens: Mapped[int | None] = mapped_column(nullable=True)
    soft_limit_tokens: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship("User", back_populates="subscription")


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    execution_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., openai, anthropic, google, nvidia
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    input_tokens: Mapped[int] = mapped_column(nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="token_usages")
    execution: Mapped[Optional[WorkflowExecution]] = relationship("WorkflowExecution")


class ModelProvider(Base):
    __tablename__ = "model_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)  # provider key e.g., openai
    model: Mapped[str] = mapped_column(String(128), nullable=False)  # model name e.g., gpt-4o-mini
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_free_tier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    context_window: Mapped[int | None] = mapped_column(nullable=True)
    input_token_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_token_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pricing_config: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # 'metadata' is reserved on Declarative models; map attribute 'meta' to DB column 'metadata'.
    meta: Mapped[Dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
