from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_task_service
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    TaskListResponse,
    TaskStatus,
    TaskPriority,
)
from app.services.task_service import TaskService

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
        task_in: TaskCreate,
        db: AsyncSession = Depends(get_db),
        task_service: TaskService = Depends(get_task_service),
):
    task = await task_service.create_task(db, task_in)
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        db: AsyncSession = Depends(get_db),
        task_service: TaskService = Depends(get_task_service),
):
    tasks, total = await task_service.list_tasks(
        db, page=page, page_size=page_size, status=status, priority=priority
    )
    return TaskListResponse(
        items=tasks,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
        task_id: int,
        db: AsyncSession = Depends(get_db),
        task_service: TaskService = Depends(get_task_service),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
        task_id: int,
        db: AsyncSession = Depends(get_db),
        task_service: TaskService = Depends(get_task_service),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def cancel_task(
        task_id: int,
        db: AsyncSession = Depends(get_db),
        task_service: TaskService = Depends(get_task_service),
):
    success = await task_service.cancel_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or already completed")
    return None
