import pytest
from app.models.campaign import Campaign
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.enums import CampaignStatus, CallState, CallOutcome, AgentStatus, BorrowerStatus
from app.services.telecom import EventProcessor

@pytest.mark.asyncio
async def test_duplicate_event_is_idempotent(test_db):
    """
    Sending the same event ID twice must not double-process or regress state.
    """
    camp = Campaign(name="Idempotency Camp", status=CampaignStatus.RUNNING)
    test_db.add(camp)
    bw = Borrower(name="Borrower-Dup", phone_number="+1-555-4444", eligible_for_call=True)
    test_db.add(bw)
    ag = Agent(name="Agent-Dup", status=AgentStatus.AVAILABLE)
    test_db.add(ag)
    await test_db.commit()

    call = Call(
        campaign_id=camp.id,
        borrower_id=bw.id,
        agent_id=ag.id,
        call_state=CallState.INITIATED
    )
    test_db.add(call)
    await test_db.commit()
    await test_db.refresh(call)

    event_id = "evt-unique-12345"

    # First event: RINGING
    res1 = await EventProcessor.process_provider_event(
        db=test_db,
        event_id=event_id,
        provider_id="PROVIDER_A",
        call_id=call.id,
        event_type=CallState.RINGING
    )
    assert res1["status"] == "PROCESSED"
    assert res1["call_state"] == "RINGING"

    # Second event: Exact same event_id dispatched again (duplicate carrier webhook)
    res2 = await EventProcessor.process_provider_event(
        db=test_db,
        event_id=event_id,
        provider_id="PROVIDER_A",
        call_id=call.id,
        event_type=CallState.RINGING
    )
    assert res2["status"] == "DUPLICATE_IGNORED"
    assert res2["is_duplicate"] is True

@pytest.mark.asyncio
async def test_out_of_order_event_does_not_regress_state(test_db):
    """
    Scenario: COMPLETED -> Late ANSWERED/RINGING.
    The late event must be flagged as out-of-order and MUST NOT regress the call back to RINGING.
    """
    camp = Campaign(name="OOO Camp", status=CampaignStatus.RUNNING)
    test_db.add(camp)
    bw = Borrower(name="Borrower-OOO", phone_number="+1-555-5555", eligible_for_call=True)
    test_db.add(bw)
    ag = Agent(name="Agent-OOO", status=AgentStatus.AVAILABLE)
    test_db.add(ag)
    await test_db.commit()

    call = Call(
        campaign_id=camp.id,
        borrower_id=bw.id,
        agent_id=ag.id,
        call_state=CallState.COMPLETED,
        outcome=CallOutcome.SUCCESS
    )
    test_db.add(call)
    await test_db.commit()
    await test_db.refresh(call)

    # Late RINGING event arrives after COMPLETED
    res = await EventProcessor.process_provider_event(
        db=test_db,
        event_id="evt-late-ringing-999",
        provider_id="PROVIDER_B",
        call_id=call.id,
        event_type=CallState.RINGING
    )

    assert res["is_out_of_order"] is True
    assert res["state_applied"] is False

    # Verify call state remained COMPLETED in DB
    await test_db.refresh(call)
    assert call.call_state == CallState.COMPLETED
