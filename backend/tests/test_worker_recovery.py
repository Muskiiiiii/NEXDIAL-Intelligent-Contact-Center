import pytest
import datetime
import uuid
from sqlalchemy import select
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.campaign import Campaign
from app.models.call import Call
from app.models.worker import Worker
from app.models.enums import AgentStatus, BorrowerStatus, WorkerStatus, CallState, CallOutcome, DialingMode, CampaignStatus
from app.services.worker_pool import WorkerPool
from app.services.agent_service import AgentService
from app.services.borrower_service import BorrowerService
from app.services.safety_controller import SafetyController
from app.services.telecom import get_telecom_provider, EventProcessor

@pytest.mark.asyncio
async def test_worker_crash_and_reconciliation_basic(test_db):
    """
    Basic sanity: Orphaned agent in RESERVED state is restored to AVAILABLE.
    """
    worker = Worker(worker_name="Test-Worker-Basic", status=WorkerStatus.IDLE)
    test_db.add(worker)

    past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=25)
    agent = Agent(
        name="Orphaned-Agent-Basic",
        status=AgentStatus.RESERVED,
        last_status_change=past_time
    )
    test_db.add(agent)
    await test_db.commit()

    await WorkerPool.simulate_worker_crash(test_db, worker.worker_name)
    res = await WorkerPool.recover_worker_and_reconcile(test_db, worker.worker_name)

    assert res["status"] == "RECOVERED"
    assert res["reconciled_agents"] >= 1

    await test_db.refresh(agent)
    assert agent.status == AgentStatus.AVAILABLE

@pytest.mark.asyncio
async def test_worker_crash_before_provider_initiation(test_db):
    """
    Scenario 1: Worker crashes BEFORE telecom provider initiation.
    - Call row exists in INITIATED with provider_call_id=None.
    - Agent is RESERVED, Borrower is RESERVED.
    - Recovery must mark Call FAILED (WORKER_CRASH_ORPHANED) and restore Agent & Borrower.
    """
    worker = Worker(worker_name="Worker-Crash-PreInit", status=WorkerStatus.IDLE)
    test_db.add(worker)
    await test_db.commit()
    await test_db.refresh(worker)

    campaign = Campaign(name="Camp-1", dialing_mode=DialingMode.PROGRESSIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=20)
    agent = Agent(name="Agent-PreInit", status=AgentStatus.RESERVED, last_status_change=past_time)
    borrower = Borrower(
        campaign_id=campaign.id,
        name="Pre Init",
        phone_number="+15550001",
        status=BorrowerStatus.RESERVED,
        last_attempted_at=past_time
    )
    test_db.add(agent)
    test_db.add(borrower)
    await test_db.commit()
    await test_db.refresh(agent)
    await test_db.refresh(borrower)

    # Call created by worker before crash, never dispatched to carrier
    call = Call(
        campaign_id=campaign.id,
        borrower_id=borrower.id,
        agent_id=agent.id,
        worker_id=worker.id,
        provider_id="PROVIDER_A",
        provider_call_id=None,
        call_state=CallState.INITIATED,
        outcome=CallOutcome.PENDING,
        created_at=past_time
    )
    test_db.add(call)
    agent.current_call_id = call.id
    worker.active_job_id = call.id
    await test_db.commit()
    await test_db.refresh(call)

    # Worker crashes
    await WorkerPool.simulate_worker_crash(test_db, worker.worker_name)

    # Reconcile
    rec = await WorkerPool.recover_worker_and_reconcile(test_db, worker.worker_name)
    assert rec["orphaned_calls_failed"] >= 1
    assert rec["reconciled_agents"] >= 1
    assert rec["reconciled_borrowers"] >= 1

    await test_db.refresh(call)
    await test_db.refresh(agent)
    await test_db.refresh(borrower)

    assert call.call_state == CallState.FAILED
    assert call.outcome == CallOutcome.WORKER_CRASH_ORPHANED
    assert agent.status == AgentStatus.AVAILABLE
    assert agent.current_call_id is None
    assert borrower.status == BorrowerStatus.QUEUED

@pytest.mark.asyncio
async def test_worker_crash_after_initiation_carrier_ringing(test_db):
    """
    Scenario 2: Worker crashes after telecom provider initiation while call is RINGING.
    - Provider confirms call is ACTIVE (RINGING).
    - Recovery MUST PRESERVE the call and KEEP agent assigned.
    """
    worker = Worker(worker_name="Worker-Crash-Ringing", status=WorkerStatus.IDLE)
    test_db.add(worker)
    campaign = Campaign(name="Camp-2", dialing_mode=DialingMode.PROGRESSIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(worker)
    await test_db.refresh(campaign)

    agent = Agent(name="Agent-Ringing", status=AgentStatus.DIALING)
    borrower = Borrower(campaign_id=campaign.id, name="Ring Guy", phone_number="+15550002", status=BorrowerStatus.DIALING)
    test_db.add(agent)
    test_db.add(borrower)
    await test_db.commit()
    await test_db.refresh(agent)
    await test_db.refresh(borrower)

    provider_call_id = f"PA-ring-{uuid.uuid4().hex[:6]}"
    call = Call(
        campaign_id=campaign.id,
        borrower_id=borrower.id,
        agent_id=agent.id,
        worker_id=worker.id,
        provider_id="PROVIDER_A",
        provider_call_id=provider_call_id,
        call_state=CallState.INITIATED,
        outcome=CallOutcome.PENDING
    )
    test_db.add(call)
    agent.current_call_id = call.id
    await test_db.commit()
    await test_db.refresh(call)

    # Provider A tracks this call in RINGING
    provider = get_telecom_provider("PROVIDER_A")
    provider.active_calls[call.id] = {
        "provider_call_id": provider_call_id,
        "state": "RINGING"
    }

    # Worker crashes
    await WorkerPool.simulate_worker_crash(test_db, worker.worker_name)

    # Reconcile
    rec = await WorkerPool.recover_worker_and_reconcile(test_db, worker.worker_name)
    assert rec["active_calls_preserved"] >= 1

    await test_db.refresh(call)
    await test_db.refresh(agent)
    assert call.call_state == CallState.RINGING
    assert agent.status == AgentStatus.DIALING
    assert agent.current_call_id == call.id

@pytest.mark.asyncio
async def test_worker_crash_after_answered_carrier_connected(test_db):
    """
    Scenario 3 & 4: Worker crashes after borrower answered. Provider confirms CONNECTED.
    - Recovery MUST preserve call, advance to CONNECTED, and ensure agent remains CONNECTED.
    """
    worker = Worker(worker_name="Worker-Crash-Answered", status=WorkerStatus.IDLE)
    test_db.add(worker)
    campaign = Campaign(name="Camp-3", dialing_mode=DialingMode.PREDICTIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(worker)
    await test_db.refresh(campaign)

    agent = Agent(name="Agent-Conn", status=AgentStatus.DIALING)
    borrower = Borrower(campaign_id=campaign.id, name="Conn User", phone_number="+15550003", status=BorrowerStatus.DIALING)
    test_db.add(agent)
    test_db.add(borrower)
    await test_db.commit()
    await test_db.refresh(agent)
    await test_db.refresh(borrower)

    provider_call_id = f"PA-conn-{uuid.uuid4().hex[:6]}"
    call = Call(
        campaign_id=campaign.id,
        borrower_id=borrower.id,
        agent_id=agent.id,
        worker_id=worker.id,
        provider_id="PROVIDER_A",
        provider_call_id=provider_call_id,
        call_state=CallState.ANSWERED,
        outcome=CallOutcome.PENDING
    )
    test_db.add(call)
    agent.current_call_id = call.id
    await test_db.commit()
    await test_db.refresh(call)

    provider = get_telecom_provider("PROVIDER_A")
    provider.active_calls[call.id] = {
        "provider_call_id": provider_call_id,
        "state": "CONNECTED"
    }

    # Worker crashes
    await WorkerPool.simulate_worker_crash(test_db, worker.worker_name)

    # Reconcile
    rec = await WorkerPool.recover_worker_and_reconcile(test_db, worker.worker_name)
    assert rec["active_calls_preserved"] >= 1

    await test_db.refresh(call)
    await test_db.refresh(agent)
    await test_db.refresh(borrower)

    assert call.call_state == CallState.CONNECTED
    assert agent.status == AgentStatus.CONNECTED
    assert borrower.status == BorrowerStatus.CONNECTED

@pytest.mark.asyncio
async def test_provider_unreachable_during_reconciliation(test_db):
    """
    Scenario 5: Provider is unreachable during reconciliation.
    - Defensive invariant: Do NOT blindly release agent or borrower. Keep resources protected!
    """
    worker = Worker(worker_name="Worker-Unreach", status=WorkerStatus.IDLE)
    test_db.add(worker)
    campaign = Campaign(name="Camp-4", dialing_mode=DialingMode.PROGRESSIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(worker)
    await test_db.refresh(campaign)

    agent = Agent(name="Agent-Prot", status=AgentStatus.DIALING)
    borrower = Borrower(campaign_id=campaign.id, name="Prot One", phone_number="+15550004", status=BorrowerStatus.DIALING)
    test_db.add(agent)
    test_db.add(borrower)
    await test_db.commit()
    await test_db.refresh(agent)
    await test_db.refresh(borrower)

    provider_call_id = f"PA-unreach-{uuid.uuid4().hex[:6]}"
    call = Call(
        campaign_id=campaign.id,
        borrower_id=borrower.id,
        agent_id=agent.id,
        worker_id=worker.id,
        provider_id="PROVIDER_A",
        provider_call_id=provider_call_id,
        call_state=CallState.INITIATED,
        outcome=CallOutcome.PENDING
    )
    test_db.add(call)
    agent.current_call_id = call.id
    await test_db.commit()
    await test_db.refresh(call)

    # Trigger carrier outage
    provider = get_telecom_provider("PROVIDER_A")
    provider.outage_mode = True

    try:
        await WorkerPool.simulate_worker_crash(test_db, worker.worker_name)
        rec = await WorkerPool.recover_worker_and_reconcile(test_db, worker.worker_name)

        assert rec["deferred_calls"] >= 1

        # Invariant check: Agent is NOT released to AVAILABLE!
        await test_db.refresh(agent)
        await test_db.refresh(borrower)
        assert agent.status != AgentStatus.AVAILABLE
        assert borrower.status != BorrowerStatus.QUEUED

    finally:
        provider.outage_mode = False

@pytest.mark.asyncio
async def test_duplicate_recovery_execution_is_idempotent(test_db):
    """
    Scenario 6: Running reconciliation twice in a row is completely idempotent.
    """
    worker = Worker(worker_name="Worker-Idempotent", status=WorkerStatus.IDLE)
    test_db.add(worker)
    await test_db.commit()

    await WorkerPool.simulate_worker_crash(test_db, worker.worker_name)

    rec1 = await WorkerPool.recover_worker_and_reconcile(test_db, worker.worker_name)
    assert rec1["status"] == "RECOVERED"

    # Second execution
    rec2 = await WorkerPool.recover_worker_and_reconcile(test_db, worker.worker_name)
    assert rec2["status"] == "RECOVERED"
    assert rec2["orphaned_calls_failed"] == 0

@pytest.mark.asyncio
async def test_late_completed_event_after_recovery(test_db):
    """
    Scenario 7: Completed call cannot regress to earlier states even if late webhooks arrive.
    """
    campaign = Campaign(name="Camp-Late", dialing_mode=DialingMode.PROGRESSIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    agent = Agent(name="Agent-Late", status=AgentStatus.AVAILABLE)
    borrower = Borrower(campaign_id=campaign.id, name="Late Event", phone_number="+15550005", status=BorrowerStatus.COMPLETED)
    test_db.add(agent)
    test_db.add(borrower)
    await test_db.commit()
    await test_db.refresh(agent)
    await test_db.refresh(borrower)

    call = Call(
        campaign_id=campaign.id,
        borrower_id=borrower.id,
        agent_id=agent.id,
        provider_id="PROVIDER_A",
        provider_call_id="PA-late-1",
        call_state=CallState.COMPLETED,
        outcome=CallOutcome.SUCCESS
    )
    test_db.add(call)
    await test_db.commit()
    await test_db.refresh(call)

    # An out-of-order ANSWERED webhook arrives for this COMPLETED call
    res = await EventProcessor.process_provider_event(
        db=test_db,
        event_id=f"evt-late-{uuid.uuid4().hex[:6]}",
        provider_id="PROVIDER_A",
        call_id=call.id,
        event_type=CallState.ANSWERED
    )

    assert res["is_out_of_order"] is True
    await test_db.refresh(call)
    assert call.call_state == CallState.COMPLETED

@pytest.mark.asyncio
async def test_safe_capacity_restored_after_orphan_resolution(test_db):
    """
    Scenario 8: Capacity calculation no longer counts genuinely resolved orphaned calls.
    """
    campaign = Campaign(name="Camp-Cap", dialing_mode=DialingMode.PROGRESSIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    worker = Worker(worker_name="Worker-Cap", status=WorkerStatus.IDLE)
    test_db.add(worker)
    await test_db.commit()
    await test_db.refresh(campaign)
    await test_db.refresh(worker)

    past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=25)
    agent = Agent(name="Agent-Cap", status=AgentStatus.RESERVED, last_status_change=past_time)
    borrower = Borrower(campaign_id=campaign.id, name="Cap Test", phone_number="+15550006", status=BorrowerStatus.RESERVED, last_attempted_at=past_time)
    test_db.add(agent)
    test_db.add(borrower)
    await test_db.commit()
    await test_db.refresh(agent)
    await test_db.refresh(borrower)

    # Orphaned uninitiated call
    call = Call(
        campaign_id=campaign.id,
        borrower_id=borrower.id,
        agent_id=agent.id,
        worker_id=worker.id,
        provider_id="PROVIDER_A",
        provider_call_id=None,
        call_state=CallState.INITIATED,
        outcome=CallOutcome.PENDING,
        created_at=past_time
    )
    test_db.add(call)
    agent.current_call_id = call.id
    await test_db.commit()

    # Prior to recovery: 0 available agents, 1 in-flight pending -> safe_capacity = 0
    cap_before = await SafetyController.get_system_capacity_snapshot(test_db)
    assert cap_before["available_agents"] == 0
    assert cap_before["in_flight_pending"] >= 1
    assert cap_before["safe_capacity"] == 0

    # Execute recovery
    await WorkerPool.simulate_worker_crash(test_db, worker.worker_name)
    await WorkerPool.recover_worker_and_reconcile(test_db, worker.worker_name)

    # After recovery: Call is FAILED, agent is AVAILABLE, in_flight_pending is 0
    cap_after = await SafetyController.get_system_capacity_snapshot(test_db)
    assert cap_after["available_agents"] >= 1
    assert cap_after["initiated_calls"] == 0
    assert cap_after["safe_capacity"] >= 1

@pytest.mark.asyncio
async def test_no_duplicate_borrower_allocation_concurrent(test_db):
    """
    Scenario 9: Concurrent borrower reservation attempts guarantee mutual exclusion.
    """
    campaign = Campaign(name="Camp-Borrower-Conc", dialing_mode=DialingMode.PROGRESSIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    borrower = Borrower(
        campaign_id=campaign.id,
        name="Solo Borrower",
        phone_number="+15550007",
        status=BorrowerStatus.QUEUED
    )
    test_db.add(borrower)
    await test_db.commit()
    await test_db.refresh(borrower)

    # Attempt two batch reservations of size 1
    res1 = await BorrowerService.reserve_eligible_borrowers_batch(test_db, campaign.id, limit=1)
    res2 = await BorrowerService.reserve_eligible_borrowers_batch(test_db, campaign.id, limit=1)

    assert len(res1) == 1
    assert len(res2) == 0
    assert res1[0].id == borrower.id

@pytest.mark.asyncio
async def test_no_duplicate_agent_allocation_concurrent(test_db):
    """
    Scenario 10: Atomic agent reservation guarantees strictly one winner.
    """
    agent = Agent(name="Solo-Agent", status=AgentStatus.AVAILABLE)
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)

    # Worker 1 reserves
    win1 = await AgentService.reserve_agent_atomic(test_db, agent.id, call_id="call-w1")
    # Worker 2 attempts same agent
    win2 = await AgentService.reserve_agent_atomic(test_db, agent.id, call_id="call-w2")

    assert win1 is True
    assert win2 is False
