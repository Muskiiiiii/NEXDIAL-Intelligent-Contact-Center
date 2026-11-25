from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.models.enums import AgentStatus
from app.schemas.agent import AgentCreate, AgentUpdateStatus, AgentResponse, AgentListResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("", response_model=AgentListResponse)
async def list_agents(
    status: Optional[AgentStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    if status:
        agents = await AgentService.get_agents_by_status(db, status)
        total = len(agents)
    else:
        agents, total = await AgentService.get_all_agents(db, skip, limit)

    all_agents, _ = await AgentService.get_all_agents(db, 0, 1000)
    avail = sum(1 for a in all_agents if a.status == AgentStatus.AVAILABLE)
    res = sum(1 for a in all_agents if a.status == AgentStatus.RESERVED)
    conn = sum(1 for a in all_agents if a.status == AgentStatus.CONNECTED)
    off = sum(1 for a in all_agents if a.status == AgentStatus.OFFLINE)

    return AgentListResponse(
        agents=[AgentResponse.model_validate(a.to_dict()) for a in agents],
        total=total,
        available_count=avail,
        reserved_count=res,
        connected_count=conn,
        offline_count=off
    )

@router.post("", response_model=AgentResponse)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = await AgentService.create_agent(db, payload.name, payload.status)
    return AgentResponse.model_validate(agent.to_dict())

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await AgentService.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent.to_dict())

@router.patch("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: str,
    payload: AgentUpdateStatus,
    db: AsyncSession = Depends(get_db)
):
    try:
        agent = await AgentService.update_agent_status(db, agent_id, payload.status)
        return AgentResponse.model_validate(agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{agent_id}/pause", response_model=AgentResponse)
async def pause_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    try:
        agent = await AgentService.update_agent_status(db, agent_id, AgentStatus.PAUSED)
        return AgentResponse.model_validate(agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{agent_id}/resume", response_model=AgentResponse)
async def resume_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    try:
        agent = await AgentService.update_agent_status(db, agent_id, AgentStatus.AVAILABLE)
        return AgentResponse.model_validate(agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{agent_id}/online", response_model=AgentResponse)
async def online_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    try:
        agent = await AgentService.update_agent_status(db, agent_id, AgentStatus.AVAILABLE)
        return AgentResponse.model_validate(agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{agent_id}/offline", response_model=AgentResponse)
async def offline_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    try:
        agent = await AgentService.update_agent_status(db, agent_id, AgentStatus.OFFLINE)
        return AgentResponse.model_validate(agent.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
