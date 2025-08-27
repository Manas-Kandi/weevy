from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_session
from ..database.models import WorkflowExecution, Project

router = APIRouter(prefix="/api", tags=["executions"])


# --------- Schemas ---------
class ExecutionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    results: Optional[Dict[str, Any]]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class StartExecutionRequest(BaseModel):
    # Allows starting execution either with a project_id or a full workflow payload (fallback)
    project_id: Optional[uuid.UUID] = None
    parameters: Optional[Dict[str, Any]] = None


# --------- Endpoints ---------
@router.get("/projects/{project_id}/executions", response_model=List[ExecutionOut])
async def list_executions(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(WorkflowExecution).where(WorkflowExecution.project_id == project_id).order_by(WorkflowExecution.started_at.desc()))
    return res.scalars().all()


@router.post("/projects/{project_id}/executions", response_model=ExecutionOut, status_code=status.HTTP_201_CREATED)
async def start_execution(project_id: uuid.UUID, payload: StartExecutionRequest | None = None, session: AsyncSession = Depends(get_session)):
    # Ensure project exists
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    exe = WorkflowExecution(project_id=project_id, status="running")
    session.add(exe)
    await session.commit()
    await session.refresh(exe)
    # Actual run is initiated over websocket in this app; return execution record
    return exe


@router.get("/executions/{execution_id}", response_model=ExecutionOut)
async def get_execution(execution_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    exe = await session.get(WorkflowExecution, execution_id)
    if not exe:
        raise HTTPException(status_code=404, detail="Execution not found")
    return exe


@router.delete("/executions/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_or_delete_execution(execution_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    exe = await session.get(WorkflowExecution, execution_id)
    if not exe:
        raise HTTPException(status_code=404, detail="Execution not found")
    # For now, just delete or mark as cancelled if running
    await session.delete(exe)
    await session.commit()
    return None
