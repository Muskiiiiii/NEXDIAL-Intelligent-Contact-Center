import pytest
from app.models.campaign import Campaign
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.enums import CampaignStatus, DialingMode, AgentStatus, BorrowerStatus, CallState
from app.services.agent_service import AgentService
from app.services.call_allocator import CallAllocator
from app.services.safety_controller import SafetyController

@pytest.mark.asyncio
async def test_progressive_dialer_one_to_one(test_db):
    """Rule: One available agent -> At most one agent-bound outbound call."""
    # Create Campaign
    campaign = Campaign(
        name="Test Progressive Campaign",
        dialing_mode=DialingMode.PROGRESSIVE,
        status=CampaignStatus.RUNNING
    )
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    # Create 3 Available Agents, 2 Offline Agents
    for i in range(3):
        ag = Agent(name=f"Avail-Agent-{i}", status=AgentStatus.AVAILABLE)
        test_db.add(ag)
    for i in range(2):
        ag = Agent(name=f"Offline-Agent-{i}", status=AgentStatus.OFFLINE)
        test_db.add(ag)

    # Create 10 Queued Borrowers
    for i in range(10):
        bw = Borrower(
            name=f"Borrower-{i}",
            phone_number=f"+1-555-010{i}",
            campaign_id=campaign.id,
            status=BorrowerStatus.QUEUED,
            eligible_for_call=True
        )
        test_db.add(bw)
    await test_db.commit()

    # Run allocation cycle
    result = await CallAllocator.run_allocation_cycle(
        db=test_db,
        campaign=campaign,
        provider_id="PROVIDER_A"
    )

    # With 3 available agents and 10 queued borrowers, Progressive mode MUST initiate exactly 3 calls
    assert len(result["initiated_calls"]) == 3
    assert result["safety_decision"]["approved_calls"] == 3

    # Verify that offline agents never received calls
    offline_agents = await AgentService.get_agents_by_status(test_db, AgentStatus.OFFLINE)
    assert len(offline_agents) == 2
    for off in offline_agents:
        assert off.current_call_id is None

@pytest.mark.asyncio
async def test_progressive_dialer_no_calls_when_no_agents(test_db):
    """When zero agents are available, zero calls must be initiated."""
    campaign = Campaign(
        name="Zero Agent Campaign",
        dialing_mode=DialingMode.PROGRESSIVE,
        status=CampaignStatus.RUNNING
    )
    test_db.add(campaign)
    # Add borrower
    bw = Borrower(name="Borrower-1", phone_number="+1-555-1234", campaign_id=campaign.id, eligible_for_call=True)
    test_db.add(bw)
    await test_db.commit()
    await test_db.refresh(campaign)

    result = await CallAllocator.run_allocation_cycle(test_db, campaign)
    assert len(result["initiated_calls"]) == 0
    assert result["safety_decision"]["decision"] == "REJECT"

@pytest.mark.asyncio
async def test_failed_call_releases_agent(test_db):
    """If call fails, agent must be released back to AVAILABLE and never left RESERVED."""
    agent = Agent(name="Agent-Release-Test", status=AgentStatus.AVAILABLE)
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)

    # Reserve agent
    reserved = await AgentService.reserve_agent_atomic(test_db, agent.id)
    assert reserved is True

    # Check agent is now RESERVED
    ag_check = await AgentService.get_agent(test_db, agent.id)
    assert ag_check.status == AgentStatus.RESERVED

    # Release agent due to abort/failure
    released = await AgentService.release_agent(test_db, agent.id, reason="Call failed")
    assert released is True

    ag_after = await AgentService.get_agent(test_db, agent.id)
    assert ag_after.status == AgentStatus.AVAILABLE
