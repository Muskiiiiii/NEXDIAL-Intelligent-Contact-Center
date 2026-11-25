from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import List, Optional, Tuple
import datetime
import uuid

from app.models.agent import Agent
from app.models.enums import AgentStatus
from app.models.audit import AuditLog
from app.core.websocket_manager import ws_manager

VALID_AGENT_TRANSITIONS = {
    AgentStatus.OFFLINE: {AgentStatus.AVAILABLE},
    AgentStatus.AVAILABLE: {AgentStatus.RESERVED, AgentStatus.PAUSED, AgentStatus.OFFLINE},
    AgentStatus.RESERVED: {AgentStatus.DIALING, AgentStatus.AVAILABLE, AgentStatus.OFFLINE},
    AgentStatus.DIALING: {AgentStatus.CONNECTED, AgentStatus.WRAP_UP, AgentStatus.AVAILABLE, AgentStatus.OFFLINE},
    AgentStatus.CONNECTED: {AgentStatus.WRAP_UP, AgentStatus.AVAILABLE, AgentStatus.OFFLINE},
    AgentStatus.WRAP_UP: {AgentStatus.AVAILABLE, AgentStatus.PAUSED, AgentStatus.OFFLINE},
    AgentStatus.PAUSED: {AgentStatus.AVAILABLE, AgentStatus.OFFLINE},
}

class AgentService:
    @staticmethod
    async def create_agent(db: AsyncSession, name: str, status: AgentStatus = AgentStatus.OFFLINE) -> Agent:
        agent = Agent(name=name, status=status)
        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        # Broadcast creation
        await ws_manager.broadcast("AGENT_CREATED", agent.to_dict())
        return agent

    @staticmethod
    async def get_agent(db: AsyncSession, agent_id: str) -> Optional[Agent]:
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_agents(db: AsyncSession, skip: int = 0, limit: int = 100) -> Tuple[List[Agent], int]:
        count_stmt = select(func.count(Agent.id))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Agent).order_by(Agent.name).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_agents_by_status(db: AsyncSession, status: AgentStatus) -> List[Agent]:
        stmt = select(Agent).where(Agent.status == status)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_agent_status(
        db: AsyncSession,
        agent_id: str,
        new_status: AgentStatus,
        current_call_id: Optional[str] = None,
        force: bool = False
    ) -> Agent:
        """
        Transition an agent to a new status following valid state transitions.
        """
        agent = await AgentService.get_agent(db, agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        old_status = agent.status
        if not force and new_status not in VALID_AGENT_TRANSITIONS.get(old_status, set()):
            raise ValueError(
                f"Invalid agent state transition from {old_status.value} to {new_status.value}"
            )

        agent.status = new_status
        agent.last_status_change = func.now()
        if current_call_id is not None:
            agent.current_call_id = current_call_id
        elif new_status in (AgentStatus.AVAILABLE, AgentStatus.OFFLINE, AgentStatus.PAUSED):
            agent.current_call_id = None

        # Record audit log
        audit = AuditLog(
            event_type="AGENT_STATUS_CHANGED",
            entity_type="Agent",
            entity_id=agent.id,
            message=f"Agent '{agent.name}' transitioned from {old_status.value} to {new_status.value}",
            metadata_json={"old_status": old_status.value, "new_status": new_status.value, "call_id": current_call_id}
        )
        db.add(audit)
        await db.commit()
        await db.refresh(agent)

        await ws_manager.broadcast("AGENT_UPDATED", agent.to_dict())
        return agent

    @staticmethod
    async def reserve_agent_atomic(db: AsyncSession, agent_id: str, call_id: Optional[str] = None) -> bool:
        """
        CRITICAL CONCURRENCY REQUIREMENT:
        Atomically reserve an agent only if current status is strictly AVAILABLE.
        Returns True if reservation was acquired, False if another worker took it or agent unavailable.
        """
        stmt = (
            update(Agent)
            .where(
                and_(
                    Agent.id == agent_id,
                    Agent.status == AgentStatus.AVAILABLE
                )
            )
            .values(
                status=AgentStatus.RESERVED,
                current_call_id=call_id,
                last_status_change=func.now()
            )
        )
        result = await db.execute(stmt)
        await db.commit()

        acquired = (result.rowcount > 0)
        if acquired:
            agent = await AgentService.get_agent(db, agent_id)
            if agent:
                await ws_manager.broadcast("AGENT_UPDATED", agent.to_dict())
        return acquired

    @staticmethod
    async def reserve_available_agents_batch(
        db: AsyncSession,
        limit: int
    ) -> List[Agent]:
        """
        Atomically reserve up to `limit` AVAILABLE agents without race conditions.
        """
        if limit <= 0:
            return []

        # Find candidates
        candidates_stmt = (
            select(Agent.id)
            .where(Agent.status == AgentStatus.AVAILABLE)
            .limit(limit)
        )
        candidate_ids = (await db.execute(candidates_stmt)).scalars().all()

        reserved_agents: List[Agent] = []
        for aid in candidate_ids:
            # Atomic conditional update per agent guarantees no double allocation
            acquired = await AgentService.reserve_agent_atomic(db, aid)
            if acquired:
                agent = await AgentService.get_agent(db, aid)
                if agent:
                    reserved_agents.append(agent)

        return reserved_agents

    @staticmethod
    async def release_agent(db: AsyncSession, agent_id: str, reason: str = "Call finished or aborted") -> bool:
        """
        Safely returns an agent to AVAILABLE status if currently RESERVED, DIALING, CONNECTED, or WRAP_UP.
        """
        agent = await AgentService.get_agent(db, agent_id)
        if not agent:
            return False

        if agent.status in (AgentStatus.RESERVED, AgentStatus.DIALING, AgentStatus.CONNECTED, AgentStatus.WRAP_UP):
            agent.status = AgentStatus.AVAILABLE
            agent.current_call_id = None
            agent.last_status_change = func.now()
            db.add(agent)

            audit = AuditLog(
                event_type="AGENT_RELEASED",
                entity_type="Agent",
                entity_id=agent.id,
                message=f"Agent '{agent.name}' released to AVAILABLE ({reason})",
                metadata_json={"reason": reason}
            )
            db.add(audit)
            await db.commit()
            await db.refresh(agent)
            await ws_manager.broadcast("AGENT_UPDATED", agent.to_dict())
            return True
        return False
