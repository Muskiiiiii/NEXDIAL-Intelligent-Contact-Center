import pytest
import datetime
import uuid
from app.models.campaign import Campaign
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.enums import CampaignStatus, DialingMode, AgentStatus, BorrowerStatus, CallState, CallOutcome, SafetyDecisionType
from app.services.pacing_engine import PacingEngine
from app.services.safety_controller import SafetyController
from app.services.telecom import get_telecom_provider

@pytest.mark.asyncio
async def test_predictive_pacing_formula_calculation(test_db):
    """
    Test that the predictive pacing engine calculates requested calls according to
    answer rates, risk factors, and agent capacity.
    """
    campaign = Campaign(
        name="Predictive Test",
        dialing_mode=DialingMode.PREDICTIVE,
        status=CampaignStatus.RUNNING
    )
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    # 10 available agents
    for i in range(10):
        test_db.add(Agent(name=f"Agent-{i}", status=AgentStatus.AVAILABLE))

    # 50 queued borrowers
    for i in range(50):
        test_db.add(Borrower(
            name=f"Borrower-{i}",
            phone_number=f"+1-555-88{i:02d}",
            campaign_id=campaign.id,
            status=BorrowerStatus.QUEUED,
            eligible_for_call=True
        ))
    await test_db.commit()

    # Compute dial request with 15% risk factor
    pacing = await PacingEngine.compute_dial_request(
        db=test_db,
        campaign=campaign,
        risk_factor=0.15
    )

    assert pacing["dialing_mode"] == DialingMode.PREDICTIVE
    assert pacing["available_agents"] == 10
    assert pacing["requested_dial_count"] > 0
    assert "formula_explanation" in pacing
    assert "calculation_details" in pacing
    assert "setup_latency_telemetry" in pacing
    assert pacing["requested_dial_count"] <= 50

@pytest.mark.asyncio
async def test_dynamic_setup_latency_normal_telemetry(test_db):
    """
    B7 Requirement: Normal fresh telemetry combining carrier latency + rolling DB call ring times.
    """
    campaign = Campaign(name="Camp-B7-Normal", dialing_mode=DialingMode.PREDICTIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    # Add 5 fresh calls with ~7.0s ring times
    for i in range(5):
        c = Call(
            campaign_id=campaign.id,
            borrower_id=f"b-b7-{i}",
            call_state=CallState.COMPLETED,
            outcome=CallOutcome.SUCCESS,
            ring_time_seconds=7.0 + (i * 0.2), # 7.0, 7.2, 7.4, 7.6, 7.8 -> avg 7.4s
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )
        test_db.add(c)
    await test_db.commit()

    lat = await PacingEngine.get_dynamic_setup_latency(test_db, provider_id="PROVIDER_A", campaign_id=campaign.id)

    assert lat["telemetry_source"] == "DYNAMIC_PROVIDER_AND_DB"
    assert lat["is_fallback"] is False
    assert lat["sample_size"] == 5
    # Provider A has avg_latency ~75ms (0.075s) + measured ~7.4s -> setup around 7.47s
    assert 7.0 <= lat["setup_window_sec"] <= 8.5
    assert lat["clamped"] is False

@pytest.mark.asyncio
async def test_dynamic_setup_latency_high_latency_clamping(test_db):
    """
    B7 Requirement: Extreme carrier latency is safely clamped to MAX_SETUP_WINDOW_SEC (30.0s).
    """
    campaign = Campaign(name="Camp-B7-High", dialing_mode=DialingMode.PREDICTIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    # Provider B latency spiked to 35,000ms (35 seconds)
    provider_b = get_telecom_provider("PROVIDER_B")
    orig_latency = provider_b.avg_latency_ms
    provider_b.avg_latency_ms = 35000.0

    try:
        lat = await PacingEngine.get_dynamic_setup_latency(test_db, provider_id="PROVIDER_B", campaign_id=campaign.id)
        assert lat["setup_window_sec"] == PacingEngine.MAX_SETUP_WINDOW_SEC
        assert lat["clamped"] is True
        assert lat["raw_setup_sec"] > 30.0
    finally:
        provider_b.avg_latency_ms = orig_latency

@pytest.mark.asyncio
async def test_dynamic_setup_latency_missing_telemetry(test_db):
    """
    B7 Requirement: Missing telemetry uses documented default fallback (10.0s).
    """
    campaign = Campaign(name="Camp-B7-Missing", dialing_mode=DialingMode.PREDICTIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    # Provider offline / circuit OPEN
    provider_a = get_telecom_provider("PROVIDER_A")
    orig_state = provider_a.circuit_breaker.state
    provider_a.circuit_breaker.state = "OPEN"

    try:
        lat = await PacingEngine.get_dynamic_setup_latency(test_db, provider_id="PROVIDER_A", campaign_id=campaign.id)
        assert lat["telemetry_source"] == "MISSING_TELEMETRY_DEFAULT"
        assert lat["is_fallback"] is True
        assert lat["setup_window_sec"] == PacingEngine.DEFAULT_SETUP_WINDOW_SEC
    finally:
        provider_a.circuit_breaker.state = orig_state

@pytest.mark.asyncio
async def test_dynamic_setup_latency_stale_telemetry(test_db):
    """
    B7 Requirement: Stale telemetry older than 300s activates safe stale fallback.
    """
    campaign = Campaign(name="Camp-B7-Stale", dialing_mode=DialingMode.PREDICTIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    await test_db.commit()
    await test_db.refresh(campaign)

    # Add calls older than 5 minutes (e.g. 10 minutes ago)
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=600)
    for i in range(5):
        c = Call(
            campaign_id=campaign.id,
            borrower_id=f"b-stale-{i}",
            call_state=CallState.COMPLETED,
            outcome=CallOutcome.SUCCESS,
            ring_time_seconds=14.0,
            created_at=old_time
        )
        test_db.add(c)
    await test_db.commit()

    lat = await PacingEngine.get_dynamic_setup_latency(test_db, provider_id="PROVIDER_A", campaign_id=campaign.id)
    assert lat["telemetry_source"] == "STALE_TELEMETRY_FALLBACK"
    assert lat["is_fallback"] is True
    assert lat["sample_size"] == 0 # 0 fresh samples

@pytest.mark.asyncio
async def test_predictive_pacing_respects_safety_controller_with_dynamic_latency(test_db):
    """
    B7 Requirement: Predictive pacing with dynamic latency NEVER overrides SafetyController.
    When available agent capacity is 0, SafetyController strictly rejects requests.
    """
    campaign = Campaign(name="Camp-B7-Safety", dialing_mode=DialingMode.PREDICTIVE, status=CampaignStatus.RUNNING)
    test_db.add(campaign)
    # Add 10 queued borrowers, but 0 available agents
    for i in range(10):
        test_db.add(Borrower(name=f"B-{i}", phone_number=f"+1555{i}", campaign_id=campaign.id, status=BorrowerStatus.QUEUED))
    await test_db.commit()
    await test_db.refresh(campaign)

    # Pacing engine evaluates
    pacing = await PacingEngine.compute_dial_request(test_db, campaign, provider_id="PROVIDER_A")

    # Evaluate with Safety Controller
    decision = await SafetyController.evaluate_dial_request(
        db=test_db,
        campaign_id=campaign.id,
        requested_calls=pacing["requested_dial_count"],
        dialing_mode=DialingMode.PREDICTIVE,
        provider_id="PROVIDER_A"
    )

    # Zero agents -> REJECT with 0 approved calls
    assert decision.decision == SafetyDecisionType.REJECT
    assert decision.approved_calls == 0
