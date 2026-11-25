import pytest
from app.models.agent import Agent
from app.models.campaign import Campaign
from app.models.enums import AgentStatus, CampaignStatus, DialingMode, SafetyDecisionType
from app.services.safety_controller import SafetyController
from app.services.telecom import get_telecom_provider

@pytest.mark.asyncio
async def test_safety_controller_reduces_excessive_dial_request(test_db):
    """
    If pacing engine requests 20 calls but only 5 agents are available,
    the Safety Controller must independently REDUCE the request to safe capacity (5).
    """
    # Create 5 available agents
    for i in range(5):
        test_db.add(Agent(name=f"Agent-{i}", status=AgentStatus.AVAILABLE))
    await test_db.commit()

    decision = await SafetyController.evaluate_dial_request(
        db=test_db,
        campaign_id="camp-123",
        requested_calls=20,
        dialing_mode=DialingMode.PREDICTIVE
    )

    assert decision.decision == SafetyDecisionType.REDUCE
    assert decision.approved_calls == 5
    assert decision.rejected_calls == 15
    assert "limit safe dialing to 5" in decision.reason

@pytest.mark.asyncio
async def test_safety_controller_rejects_when_zero_capacity(test_db):
    """
    When available agent capacity is 0, requested calls must be completely REJECTED.
    """
    # 0 agents
    decision = await SafetyController.evaluate_dial_request(
        db=test_db,
        campaign_id="camp-zero",
        requested_calls=10,
        dialing_mode=DialingMode.PROGRESSIVE
    )

    assert decision.decision == SafetyDecisionType.REJECT
    assert decision.approved_calls == 0
    assert decision.rejected_calls == 10

@pytest.mark.asyncio
async def test_safety_controller_rejects_on_provider_circuit_open(test_db):
    """
    When provider circuit breaker is OPEN, Safety Controller protects carrier by rejecting calls.
    """
    for i in range(10):
        test_db.add(Agent(name=f"Agent-{i}", status=AgentStatus.AVAILABLE))
    await test_db.commit()

    provider = get_telecom_provider("PROVIDER_A")
    provider.circuit_breaker.state = "OPEN"

    decision = await SafetyController.evaluate_dial_request(
        db=test_db,
        campaign_id="camp-cb",
        requested_calls=5,
        dialing_mode=DialingMode.PROGRESSIVE,
        provider_id="PROVIDER_A"
    )

    assert decision.decision == SafetyDecisionType.REJECT
    assert decision.approved_calls == 0
    assert "circuit breaker is OPEN" in decision.reason

    # Clean up state
    provider.circuit_breaker.state = "CLOSED"

@pytest.mark.asyncio
async def test_safety_controller_fallback_to_progressive(test_db):
    """
    When predictive confidence or answer rate is unstable, automatically falls back to Progressive.
    """
    for i in range(6):
        test_db.add(Agent(name=f"Agent-{i}", status=AgentStatus.AVAILABLE))
    await test_db.commit()

    decision = await SafetyController.evaluate_dial_request(
        db=test_db,
        campaign_id="camp-fallback",
        requested_calls=15,
        dialing_mode=DialingMode.PREDICTIVE,
        predictive_confidence=0.30, # Low confidence
        historical_answer_rate=0.08  # Very low answer rate
    )

    assert decision.decision == SafetyDecisionType.FALLBACK_TO_PROGRESSIVE
    # Under progressive fallback, at most available agent capacity is approved (6)
    assert decision.approved_calls <= 6
