import asyncio
import random
import datetime
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, Base, engine
from app.models.campaign import Campaign
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.worker import Worker
from app.models.safety import SafetyDecision
from app.models.audit import AuditLog
from app.models.enums import (
    CampaignStatus, DialingMode, AgentStatus, BorrowerStatus,
    CallState, CallOutcome, SafetyDecisionType, WorkerStatus
)

AGENT_NAMES = [
    "Sarah Jenkins", "Michael Chang", "Emily Rodriguez", "David Kim", "Jessica Taylor",
    "Robert Chen", "Amanda White", "Daniel Martinez", "Olivia Brown", "James Wilson",
    "Sophia Patel", "Alexander Ross", "Mia Gonzalez", "Ethan Wright", "Isabella King",
    "Lucas Scott", "Charlotte Green", "Benjamin Adams", "Harper Baker", "Noah Hall",
    "Ava Campbell", "Mason Mitchell", "Amelia Roberts", "Elijah Carter", "Evelyn Phillips",
    "Logan Evans", "Abigail Turner", "Oliver Torres", "Elizabeth Parker", "William Collins"
]

BORROWER_NAMES = [
    "Marcus Vance", "Elena Rostova", "Liam O'Connor", "Priya Sharma", "Carlos Mendez",
    "Chloe Bennett", "DeAndre Washington", "Svetlana Ivanova", "Tariq Al-Mansoor", "Grace Kelly",
    "Mateo Silva", "Ananya Deshmukh", "Dmitri Volkov", "Kaitlyn O'Brien", "Jaxon Brooks",
    "Fatima Zahra", "Hiroshi Tanaka", "Megan Fitzpatrick", "Siddharth Verma", "Zoe Saldana",
    "Gabriel Santana", "Leila Haddad", "Sean MacLeod", "Aaliyah Jackson", "Tomas Lindqvist",
    "Nadia Kowalska", "Andre Dubois", "Mei-Ling Zhou", "Kwame Mensah", "Valeria Morales"
]

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        existing_campaigns = (await db.execute(select(func.count(Campaign.id)))).scalar() or 0
        if existing_campaigns > 0:
            print("Database already contains data, skipping seed.")
            return

        print("Seeding initial NEXDIAL database records...")

        # 1. Campaigns
        campaign_prog = Campaign(
            id=str(uuid.uuid4()),
            name="Retail Loan Servicing — Progressive",
            dialing_mode=DialingMode.PROGRESSIVE,
            status=CampaignStatus.RUNNING,
            priority=1,
            max_attempts=3,
            retry_interval_seconds=300,
            target_abandon_rate=0.02,
            pacing_ratio=1.0
        )
        campaign_pred = Campaign(
            id=str(uuid.uuid4()),
            name="Prime Auto Collections — Predictive",
            dialing_mode=DialingMode.PREDICTIVE,
            status=CampaignStatus.RUNNING,
            priority=2,
            max_attempts=4,
            retry_interval_seconds=600,
            target_abandon_rate=0.03,
            pacing_ratio=1.8
        )
        db.add(campaign_prog)
        db.add(campaign_pred)
        await db.commit()

        # 2. Workers
        for i in range(1, 4):
            w = Worker(
                worker_name=f"Dialer-Worker-{i}",
                status=WorkerStatus.IDLE,
                jobs_processed=random.randint(120, 450),
                jobs_recovered=random.randint(0, 3)
            )
            db.add(w)
        await db.commit()

        # 3. Agents
        created_agents = []
        for i, name in enumerate(AGENT_NAMES):
            if i < 18:
                status = AgentStatus.AVAILABLE
            elif i < 22:
                status = AgentStatus.CONNECTED
            elif i < 24:
                status = AgentStatus.RESERVED
            elif i < 26:
                status = AgentStatus.WRAP_UP
            elif i < 28:
                status = AgentStatus.PAUSED
            else:
                status = AgentStatus.OFFLINE

            tot_calls = random.randint(15, 65)
            avg_tt = random.uniform(45.0, 110.0)
            ag = Agent(
                name=name,
                status=status,
                total_calls=tot_calls,
                total_talk_time_seconds=tot_calls * avg_tt,
                average_talk_time=avg_tt
            )
            db.add(ag)
            created_agents.append(ag)
        await db.commit()

        # 4. Borrowers
        created_borrowers = []
        for i in range(120):
            b_name = f"{BORROWER_NAMES[i % len(BORROWER_NAMES)]} {i+1}"
            phone = f"+1-800-{100 + (i % 900):03d}-{1000 + i:04d}"
            camp = campaign_prog if i % 2 == 0 else campaign_pred
            b = Borrower(
                name=b_name,
                phone_number=phone,
                priority=random.randint(1, 3),
                campaign_id=camp.id,
                status=BorrowerStatus.QUEUED,
                attempt_count=random.randint(0, 1),
                eligible_for_call=True
            )
            db.add(b)
            created_borrowers.append(b)
        await db.commit()

        # 5. Historical Completed Calls (so analytics charts are immediately populated!)
        now = datetime.datetime.now(datetime.timezone.utc)
        for i in range(80):
            mins_ago = random.uniform(2, 55)
            call_time = now - datetime.timedelta(minutes=mins_ago)
            camp = campaign_prog if i % 2 == 0 else campaign_pred
            ag = random.choice(created_agents)
            bw = random.choice(created_borrowers)

            is_success = (i % 10 != 0) # 90% success
            tt = random.uniform(30.0, 150.0) if is_success else 0.0
            ring_t = random.uniform(4.0, 12.0)

            c = Call(
                campaign_id=camp.id,
                borrower_id=bw.id,
                agent_id=ag.id,
                provider_id="PROVIDER_A" if i % 3 != 0 else "PROVIDER_B",
                provider_call_id=f"HIST-{uuid.uuid4().hex[:8]}",
                call_state=CallState.COMPLETED if is_success else CallState.FAILED,
                outcome=CallOutcome.SUCCESS if is_success else (CallOutcome.BUSY if i % 2 == 0 else CallOutcome.UNANSWERED),
                ring_time_seconds=ring_t,
                talk_time_seconds=tt,
                total_duration_seconds=ring_t + tt,
                initiated_at=call_time,
                ringing_at=call_time + datetime.timedelta(seconds=1),
                answered_at=call_time + datetime.timedelta(seconds=ring_t) if is_success else None,
                connected_at=call_time + datetime.timedelta(seconds=ring_t + 0.5) if is_success else None,
                ended_at=call_time + datetime.timedelta(seconds=ring_t + tt + 1),
                created_at=call_time
            )
            db.add(c)
        await db.commit()

        # 6. Safety Decisions history
        for i in range(15):
            mins_ago = random.uniform(1, 40)
            dt = now - datetime.timedelta(minutes=mins_ago)
            dec_type = SafetyDecisionType.APPROVE if i % 4 != 0 else SafetyDecisionType.REDUCE
            req = random.randint(4, 12)
            appr = req if dec_type == SafetyDecisionType.APPROVE else req - 3
            sd = SafetyDecision(
                campaign_id=campaign_pred.id,
                decision=dec_type,
                requested_calls=req,
                approved_calls=appr,
                rejected_calls=req - appr,
                available_agents=18,
                reserved_agents=2,
                ringing_calls=random.randint(1, 4),
                active_calls=4,
                provider_health_score=0.98,
                reason=f"Safety policy check: Capacity ({18} avail) safely validated for {appr} calls.",
                created_at=dt
            )
            db.add(sd)
        await db.commit()

        # 7. Audit log entries
        audit_events = [
            ("SYSTEM_INITIALIZED", "System", "NEXDIAL platform started in SIMULATION mode"),
            ("CAMPAIGN_STARTED", "Campaign", f"Campaign '{campaign_prog.name}' started in PROGRESSIVE mode"),
            ("CAMPAIGN_STARTED", "Campaign", f"Campaign '{campaign_pred.name}' started in PREDICTIVE mode"),
            ("SAFETY_CONTROLLER_ARMED", "SafetyController", "Independent Safety Controller armed with strict zero-abandonment policy"),
            ("WORKER_POOL_READY", "WorkerPool", "Worker pool armed with 3 distributed dialer workers"),
        ]
        for evt, etype, msg in audit_events:
            al = AuditLog(
                event_type=evt,
                entity_type=etype,
                message=msg
            )
            db.add(al)
        await db.commit()

        print("Seeding complete! 30 agents, 120 borrowers, 2 campaigns, 80 calls generated.")

if __name__ == "__main__":
    asyncio.run(seed_data())
