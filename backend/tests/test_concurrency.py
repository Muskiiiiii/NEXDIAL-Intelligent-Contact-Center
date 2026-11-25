import pytest
import asyncio
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.enums import AgentStatus, BorrowerStatus
from app.services.agent_service import AgentService
from app.services.borrower_service import BorrowerService

@pytest.mark.asyncio
async def test_two_workers_cannot_reserve_same_agent(test_db):
    """
    CRITICAL CONCURRENCY TEST:
    Simultaneous workers compete to reserve the exact same agent.
    Proves that atomic UPDATE ... WHERE status = 'AVAILABLE' permits exactly 1 winner.
    """
    agent = Agent(name="Concurrent-Target-Agent", status=AgentStatus.AVAILABLE)
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)

    # Worker 1 and Worker 2 attempt to reserve the same agent simultaneously
    res1, res2 = await asyncio.gather(
        AgentService.reserve_agent_atomic(test_db, agent.id),
        AgentService.reserve_agent_atomic(test_db, agent.id)
    )

    # Exactly one must succeed, and one must fail
    results = [res1, res2]
    assert results.count(True) == 1
    assert results.count(False) == 1

    # Verify database state
    ag_db = await AgentService.get_agent(test_db, agent.id)
    assert ag_db.status == AgentStatus.RESERVED

@pytest.mark.asyncio
async def test_two_workers_cannot_reserve_same_borrower(test_db):
    """
    Proves that two workers competing for the same borrower results in exactly 1 claim.
    """
    borrower = Borrower(
        name="Concurrent-Target-Borrower",
        phone_number="+1-555-9999",
        status=BorrowerStatus.QUEUED,
        eligible_for_call=True
    )
    test_db.add(borrower)
    await test_db.commit()
    await test_db.refresh(borrower)

    res1, res2 = await asyncio.gather(
        BorrowerService.reserve_borrower_atomic(test_db, borrower.id),
        BorrowerService.reserve_borrower_atomic(test_db, borrower.id)
    )

    results = [res1, res2]
    assert results.count(True) == 1
    assert results.count(False) == 1

    bw_db = await BorrowerService.get_borrower(test_db, borrower.id)
    assert bw_db.status == BorrowerStatus.RESERVED
