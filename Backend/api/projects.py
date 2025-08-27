from __future__ import annotations

import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_session
from ..database.models import Project, WorkflowNode, NodeConnection, User

router = APIRouter(prefix="/api/projects", tags=["projects"])


# --------- Schemas ---------
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False
    canvas_data: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    canvas_data: Optional[Dict[str, Any]] = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    is_public: bool
    canvas_data: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class NodeOut(BaseModel):
    id: uuid.UUID
    node_type: str
    name: str
    position_x: float
    position_y: float
    configuration: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class ConnectionOut(BaseModel):
    id: uuid.UUID
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID

    class Config:
        from_attributes = True


class ProjectDetailOut(ProjectOut):
    nodes: List[NodeOut]
    connections: List[ConnectionOut]


class ProjectImport(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False
    canvas_data: Optional[Dict[str, Any]] = None
    nodes: List[Dict[str, Any]] = []
    connections: List[Dict[str, Any]] = []


# --------- Helpers (temporary auth stub) ---------
async def get_or_create_demo_user(session: AsyncSession) -> User:
    res = await session.execute(select(User).where(User.email == "demo@weev.local"))
    user = res.scalar_one_or_none()
    if user:
        return user
    user = User(email="demo@weev.local", username="demo", password_hash="!demo!")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# --------- Endpoints ---------
@router.get("", response_model=List[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_session)):
    user = await get_or_create_demo_user(session)
    res = await session.execute(select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc()))
    return res.scalars().all()


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, session: AsyncSession = Depends(get_session)):
    user = await get_or_create_demo_user(session)
    project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=user.id,
        is_public=payload.is_public,
        canvas_data=payload.canvas_data,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectDetailOut)
async def get_project(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.refresh(proj)
    # prefetch nodes and connections
    nodes_res = await session.execute(select(WorkflowNode).where(WorkflowNode.project_id == project_id))
    conns_res = await session.execute(select(NodeConnection).where(NodeConnection.project_id == project_id))
    nodes = nodes_res.scalars().all()
    conns = conns_res.scalars().all()
    return ProjectDetailOut.model_validate({
        "id": proj.id,
        "name": proj.name,
        "description": proj.description,
        "is_public": proj.is_public,
        "canvas_data": proj.canvas_data,
        "nodes": nodes,
        "connections": conns,
    }, from_attributes=True)


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: uuid.UUID, payload: ProjectUpdate, session: AsyncSession = Depends(get_session)):
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(proj, k, v)
    await session.commit()
    await session.refresh(proj)
    return proj


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.delete(proj)
    await session.commit()
    return None


@router.post("/{project_id}/duplicate", response_model=ProjectDetailOut, status_code=status.HTTP_201_CREATED)
async def duplicate_project(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    orig = await session.get(Project, project_id)
    if not orig:
        raise HTTPException(status_code=404, detail="Project not found")
    user = await get_or_create_demo_user(session)

    dup = Project(
        name=(orig.name + " Copy")[:255],
        description=orig.description,
        owner_id=user.id,
        is_public=False,
        canvas_data=orig.canvas_data,
    )
    session.add(dup)
    await session.flush()  # get dup.id

    # mapping old->new node ids
    res_nodes = await session.execute(select(WorkflowNode).where(WorkflowNode.project_id == project_id))
    old_nodes = res_nodes.scalars().all()
    id_map: dict[uuid.UUID, uuid.UUID] = {}
    for n in old_nodes:
        new_id = uuid.uuid4()
        id_map[n.id] = new_id
        session.add(WorkflowNode(
            id=new_id,
            project_id=dup.id,
            node_type=n.node_type,
            name=n.name,
            position_x=n.position_x,
            position_y=n.position_y,
            configuration=n.configuration,
        ))

    res_conns = await session.execute(select(NodeConnection).where(NodeConnection.project_id == project_id))
    old_conns = res_conns.scalars().all()
    for c in old_conns:
        session.add(NodeConnection(
            project_id=dup.id,
            from_node_id=id_map.get(c.from_node_id, uuid.uuid4()),
            to_node_id=id_map.get(c.to_node_id, uuid.uuid4()),
        ))

    await session.commit()

    # Build output detail
    nodes_res = await session.execute(select(WorkflowNode).where(WorkflowNode.project_id == dup.id))
    conns_res = await session.execute(select(NodeConnection).where(NodeConnection.project_id == dup.id))
    nodes = nodes_res.scalars().all()
    conns = conns_res.scalars().all()
    return ProjectDetailOut.model_validate({
        "id": dup.id,
        "name": dup.name,
        "description": dup.description,
        "is_public": dup.is_public,
        "canvas_data": dup.canvas_data,
        "nodes": nodes,
        "connections": conns,
    }, from_attributes=True)


@router.post("/import", response_model=ProjectDetailOut, status_code=status.HTTP_201_CREATED)
async def import_project(payload: ProjectImport, session: AsyncSession = Depends(get_session)):
    """Import a project from a client payload (e.g., existing localStorage state)."""
    user = await get_or_create_demo_user(session)
    project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=user.id,
        is_public=payload.is_public,
        canvas_data=payload.canvas_data,
    )
    session.add(project)
    await session.flush()

    # Map client node ids (strings) to new UUIDs
    id_map: dict[str, uuid.UUID] = {}
    for n in payload.nodes:
        new_id = uuid.uuid4()
        id_map[str(n.get("node_id") or n.get("id") or new_id)] = new_id
        session.add(WorkflowNode(
            id=new_id,
            project_id=project.id,
            node_type=str(n.get("node_type")),
            name=str(n.get("name") or n.get("node_type") or "Node"),
            position_x=float(n.get("position_x") or n.get("x") or 0.0),
            position_y=float(n.get("position_y") or n.get("y") or 0.0),
            configuration=n.get("configuration") or n.get("user_configuration") or {},
        ))

    for c in payload.connections:
        frm = str(c.get("from") or c.get("from_node_id"))
        to = str(c.get("to") or c.get("to_node_id"))
        if frm in id_map and to in id_map:
            session.add(NodeConnection(
                project_id=project.id,
                from_node_id=id_map[frm],
                to_node_id=id_map[to],
            ))

    await session.commit()

    # Build response
    nodes_res = await session.execute(select(WorkflowNode).where(WorkflowNode.project_id == project.id))
    conns_res = await session.execute(select(NodeConnection).where(NodeConnection.project_id == project.id))
    nodes = nodes_res.scalars().all()
    conns = conns_res.scalars().all()
    return ProjectDetailOut.model_validate({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "is_public": project.is_public,
        "canvas_data": project.canvas_data,
        "nodes": nodes,
        "connections": conns,
    }, from_attributes=True)
