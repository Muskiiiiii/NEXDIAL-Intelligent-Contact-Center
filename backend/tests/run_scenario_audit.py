import asyncio
import datetime
import uuid
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.worker import Worker
from app.models.enums import AgentStatus, BorrowerStatus, CallState, WorkerStatus, DialingMode
from app.services.worker_pool import WorkerPool
from app.services.telecom import EventProcessor, get_telecom_provider
from app.services.safety_controller import SafetyController

async def test_scenarios_2_to_8():
    # Scenario 2: Provider outage
    print("\n--- SCENARIO 2: Provider Outage ---")
    p = get_telecom_provider("PROVIDER_A")
    p.outage_mode = True
    p.circuit_breaker.state = "OPEN"
    async with AsyncSessionLocal() as db:
        dec = await SafetyController.evaluate_dial_request(db, "camp-test", 5, DialingMode.PROGRESSIVE, "PROVIDER_A")
        print(f"Provider Outage Result: decision={dec.decision}, approved={dec.approved_calls}, reason={dec.reason}")
    p.outage_mode = False
    p.circuit_breaker.state = "CLOSED"

    # Scenario 3: 100 agents available, then 40 suddenly disappear
    print("\n--- SCENARIO 3: Sudden Agent Drop ---")
    async with AsyncSessionLocal() as db:
        agents = [Agent(name=f"Drop-Agent-{i}", status=AgentStatus.AVAILABLE) for i in range(100)]
        db.add_all(agents)
        await db.commit()
        cap_before = await SafetyController.get_system_capacity_snapshot(db)
        print(f"Capacity before drop: available={cap_before['available_agents']}, safe={cap_before['safe_capacity']}")

        # 40 suddenly drop offline
        for ag in agents[:40]:
            ag.status = AgentStatus.OFFLINE
        await db.commit()

        cap_after = await SafetyController.get_system_capacity_snapshot(db)
        print(f"Capacity after 40 drop: available={cap_after['available_agents']}, safe={cap_after['safe_capacity']}")

        dec = await SafetyController.evaluate_dial_request(db, "camp-test", 70, DialingMode.PROGRESSIVE, "PROVIDER_A")
        print(f"Safety Decision after drop: decision={dec.decision}, requested=70, approved={dec.approved_calls}, rejected={dec.rejected_calls}")

    # Scenario 4: Duplicate ANSWERED events
    print("\n--- SCENARIO 4: Duplicate ANSWERED events ---")
    async with AsyncSessionLocal() as db:
        c = Call(campaign_id=str(uuid.uuid4()), borrower_id="b-1", call_state=CallState.RINGING)
        db.add(c)
        await db.commit()
        await db.refresh(c)

        evt_id = f"dup-ans-{uuid.uuid4().hex[:8]}"
        res1 = await EventProcessor.process_provider_event(db, evt_id, "PROVIDER_A", c.id, CallState.ANSWERED)
        res2 = await EventProcessor.process_provider_event(db, evt_id, "PROVIDER_A", c.id, CallState.ANSWERED)
        print(f"1st Event: status={res1['status']}, call_state={res1['call_state']}")
        print(f"2nd Duplicate Event: status={res2['status']}, is_duplicate={res2.get('is_duplicate')}")

    # Scenario 5: COMPLETED arrives before ANSWERED
    print("\n--- SCENARIO 5: COMPLETED arrives before ANSWERED ---")
    async with AsyncSessionLocal() as db:
        c = Call(campaign_id=str(uuid.uuid4()), borrower_id="b-2", call_state=CallState.RINGING)
        db.add(c)
        await db.commit()
        await db.refresh(c)

        res1 = await EventProcessor.process_provider_event(db, f"comp-{uuid.uuid4().hex[:6]}", "PROVIDER_A", c.id, CallState.COMPLETED)
        res2 = await EventProcessor.process_provider_event(db, f"late-ans-{uuid.uuid4().hex[:6]}", "PROVIDER_A", c.id, CallState.ANSWERED)
        await db.refresh(c)
        print(f"1st COMPLETED: call_state={res1['call_state']}")
        print(f"Late ANSWERED: is_out_of_order={res2.get('is_out_of_order')}, state_applied={res2.get('state_applied')}")
        print(f"Final DB Call State: {c.call_state}")

    # Scenario 6: Worker crashes immediately after ANSWERED
    print("\n--- SCENARIO 6: Worker crashes immediately after ANSWERED ---")
    async with AsyncSessionLocal() as db:
        ag = Agent(name="Ans-Crash-Agent", status=AgentStatus.DIALING)
        bw = Borrower(name="Ans-Crash-Borrower", phone_number="+1-555-8888", eligible_for_call=True)
        w = Worker(worker_name=f"Ans-Crash-Worker-{uuid.uuid4().hex[:6]}", status=WorkerStatus.PROCESSING)
        c = Call(campaign_id=str(uuid.uuid4()), borrower_id="b-3", agent_id=ag.id, call_state=CallState.ANSWERED)
        db.add_all([ag, bw, w, c])
        await db.commit()

        # Worker crashes
        await WorkerPool.simulate_worker_crash(db, w.worker_name)
        # Simulate stale lease timeout (>15s)
        ag.last_status_change = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=20)
        bw.last_attempted_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=20)
        await db.commit()
        rec = await WorkerPool.recover_worker_and_reconcile(db, w.worker_name)
        await db.refresh(ag)
        await db.refresh(c)
        print(f"After reconcile: Agent status={ag.status}, Call state={c.call_state}, Reconciled counts={rec}")

    # Scenario 7: Answer rate drops from 70% to 10%
    print("\n--- SCENARIO 7: Answer rate drops from 70% to 10% ---")
    async with AsyncSessionLocal() as db:
        dec = await SafetyController.evaluate_dial_request(
            db, "camp-test", 20, DialingMode.PREDICTIVE, "PROVIDER_A",
            predictive_confidence=0.35, historical_answer_rate=0.10
        )
        print(f"Drop Decision: decision={dec.decision}, approved={dec.approved_calls}, reason={dec.reason}")

    # Scenario 8: Provider latency spike
    print("\n--- SCENARIO 8: Provider latency spike ---")
    p = get_telecom_provider("PROVIDER_B")
    p.avg_latency_ms = 3500.0
    health = p.get_health()
    print(f"Provider B Latency Spiked: avg_latency={health['avg_latency_ms']}ms, status={health['status']}")

if __name__ == "__main__":
    asyncio.run(test_scenarios_2_to_8())
