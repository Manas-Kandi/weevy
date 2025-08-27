from __future__ import annotations

import uuid
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.connection import get_session
from ..database.models import WorkflowNode, NodeConnection, Project

router = APIRouter(prefix="/api", tags=["nodes"])  # mixed nodes/connections endpoints


# --------- Schemas ---------
class NodeCreate(BaseModel):
    node_type: str
    name: str
    position_x: float = 0.0
    position_y: float = 0.0
    configuration: Optional[Dict[str, Any]] = None


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    configuration: Optional[Dict[str, Any]] = None


class NodeOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    node_type: str
    name: str
    position_x: float
    position_y: float
    configuration: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class ConnectionCreate(BaseModel):
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID


class ConnectionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID

    class Config:
        from_attributes = True


# --------- Node Endpoints ---------
@router.post("/projects/{project_id}/nodes", response_model=NodeOut, status_code=status.HTTP_201_CREATED)
async def create_node(project_id: uuid.UUID, payload: NodeCreate, session: AsyncSession = Depends(get_session)):
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    node = WorkflowNode(
        project_id=project_id,
        node_type=payload.node_type,
        name=payload.name,
        position_x=payload.position_x,
        position_y=payload.position_y,
        configuration=payload.configuration,
    )
    session.add(node)
    await session.commit()
    await session.refresh(node)
    return node


@router.put("/nodes/{node_id}", response_model=NodeOut)
async def update_node(node_id: uuid.UUID, payload: NodeUpdate, session: AsyncSession = Depends(get_session)):
    node = await session.get(WorkflowNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(node, k, v)
    await session.commit()
    await session.refresh(node)
    return node


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(node_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    node = await session.get(WorkflowNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    await session.delete(node)
    await session.commit()
    return None


# --------- Connection Endpoints ---------
@router.post("/projects/{project_id}/connections", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
async def create_connection(project_id: uuid.UUID, payload: ConnectionCreate, session: AsyncSession = Depends(get_session)):
    # validate nodes belong to the same project
    for nid in [payload.from_node_id, payload.to_node_id]:
        n = await session.get(WorkflowNode, nid)
        if not n or n.project_id != project_id:
            raise HTTPException(status_code=400, detail="Nodes must exist and belong to the project")
    conn = NodeConnection(project_id=project_id, from_node_id=payload.from_node_id, to_node_id=payload.to_node_id)
    session.add(conn)
    await session.commit()
    await session.refresh(conn)
    return conn


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(connection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    conn = await session.get(NodeConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await session.delete(conn)
    await session.commit()
    return None
