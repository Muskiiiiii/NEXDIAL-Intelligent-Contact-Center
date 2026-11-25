import asyncio
import random
import datetime
import uuid
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_

from app.core.database import AsyncSessionLocal
from app.models.campaign import Campaign
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.enums import CampaignStatus, DialingMode, CallState, CallOutcome, AgentStatus, BorrowerStatus
from app.services.agent_service import AgentService
from app.services.borrower_service import BorrowerService
from app.services.campaign_service import CampaignService
from app.services.call_allocator import CallAllocator
from app.services.worker_pool import WorkerPool
from app.services.telecom import get_telecom_provider, EventProcessor
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("nexdial.simulation")

class SimulationEngine:
    def __init__(self):
        self.is_running: bool = False
        self.is_paused: bool = False
        self.ticks_elapsed: int = 0
        self.active_scenario_code: str = "SCENARIO_B"

        # Configuration
        self.num_agents: int = 25
        self.num_borrowers: int = 150
        self.answer_rate: float = 0.50
        self.average_talk_time_sec: float = 90.0
        self.call_setup_latency_sec: float = 1.5
        self.provider_failure_rate: float = 0.05
        self.num_workers: int = 3
        self.dialing_mode: DialingMode = DialingMode.PROGRESSIVE
        self.provider_id: str = "PROVIDER_A"
        self.tick_speed_ms: int = 1000

        self.campaign_id: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def get_state(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "ticks_elapsed": self.ticks_elapsed,
            "active_scenario_code": self.active_scenario_code,
            "config": {
                "num_agents": self.num_agents,
                "num_borrowers": self.num_borrowers,
                "answer_rate": round(self.answer_rate, 2),
                "average_talk_time_sec": self.average_talk_time_sec,
                "call_setup_latency_sec": self.call_setup_latency_sec,
                "provider_failure_rate": self.provider_failure_rate,
                "num_workers": self.num_workers,
                "dialing_mode": self.dialing_mode.value if isinstance(self.dialing_mode, DialingMode) else self.dialing_mode,
                "provider_id": self.provider_id,
                "tick_speed_ms": self.tick_speed_ms
            }
        }

    async def start(self, config_dict: Optional[Dict[str, Any]] = None):
        if config_dict:
            self.apply_config(config_dict)

        async with self._lock:
            if self.is_running and not self.is_paused:
                return

            self.is_running = True
            self.is_paused = False

            # Ensure campaign and seeded data exist
            async with AsyncSessionLocal() as db:
                await self._ensure_simulation_environment(db)

            if not self._task or self._task.done():
                self._task = asyncio.create_task(self._simulation_loop())

        await ws_manager.broadcast("SIMULATION_STARTED", self.get_state())

    async def pause(self):
        async with self._lock:
            self.is_paused = True
        await ws_manager.broadcast("SIMULATION_PAUSED", self.get_state())

    async def resume(self):
        async with self._lock:
            self.is_paused = False
        await ws_manager.broadcast("SIMULATION_RESUMED", self.get_state())

    async def reset(self):
        async with self._lock:
            self.is_running = False
            self.is_paused = False
            self.ticks_elapsed = 0
            if self._task and not self._task.done():
                self._task.cancel()

            async with AsyncSessionLocal() as db:
                # Reset all agents to AVAILABLE
                await db.execute(update(Agent).values(status=AgentStatus.AVAILABLE, current_call_id=None))
                # Reset borrowers to QUEUED
                await db.execute(update(Borrower).values(status=BorrowerStatus.QUEUED, attempt_count=0))
                # Reopen provider circuits
                for pid in ["PROVIDER_A", "PROVIDER_B"]:
                    p = get_telecom_provider(pid)
                    p.circuit_breaker.state = "CLOSED"
                    p.circuit_breaker.consecutive_failures = 0
                    p.outage_mode = False
                await db.commit()

        await ws_manager.broadcast("SIMULATION_RESET", self.get_state())

    def apply_config(self, config: Dict[str, Any]):
        if "num_agents" in config:
            self.num_agents = int(config["num_agents"])
        if "num_borrowers" in config:
            self.num_borrowers = int(config["num_borrowers"])
        if "answer_rate" in config:
            self.answer_rate = float(config["answer_rate"])
        if "average_talk_time_sec" in config:
            self.average_talk_time_sec = float(config["average_talk_time_sec"])
        if "call_setup_latency_sec" in config:
            self.call_setup_latency_sec = float(config["call_setup_latency_sec"])
        if "provider_failure_rate" in config:
            self.provider_failure_rate = float(config["provider_failure_rate"])
        if "num_workers" in config:
            self.num_workers = int(config["num_workers"])
        if "dialing_mode" in config:
            mode = config["dialing_mode"]
            self.dialing_mode = DialingMode(mode) if isinstance(mode, str) else mode
        if "provider_id" in config:
            self.provider_id = str(config["provider_id"])
        if "tick_speed_ms" in config:
            self.tick_speed_ms = int(config["tick_speed_ms"])
        if "scenario_code" in config:
            self.active_scenario_code = str(config["scenario_code"])

    async def apply_preset(self, scenario_code: str):
        self.active_scenario_code = scenario_code
        if scenario_code == "SCENARIO_A":
            self.answer_rate = 0.20
            self.average_talk_time_sec = 120.0
            self.dialing_mode = DialingMode.PREDICTIVE
        elif scenario_code == "SCENARIO_B":
            self.answer_rate = 0.50
            self.average_talk_time_sec = 90.0
            self.dialing_mode = DialingMode.PROGRESSIVE
        elif scenario_code == "SCENARIO_C":
            self.answer_rate = 0.70
            self.average_talk_time_sec = 180.0
            self.dialing_mode = DialingMode.PREDICTIVE
        elif scenario_code == "SCENARIO_D":
            # Dynamic fluctuating
            self.answer_rate = 0.40
            self.average_talk_time_sec = 60.0
            self.dialing_mode = DialingMode.PREDICTIVE

        # Update active campaign
        async with AsyncSessionLocal() as db:
            if self.campaign_id:
                camp = await CampaignService.get_campaign(db, self.campaign_id)
                if camp:
                    camp.dialing_mode = self.dialing_mode
                    db.add(camp)
                    await db.commit()

        await ws_manager.broadcast("SIMULATION_CONFIG_UPDATED", self.get_state())

    async def _ensure_simulation_environment(self, db: AsyncSession):
        # 1. Ensure campaign exists
        stmt = select(Campaign).where(Campaign.name == "Primary Simulation Campaign")
        camp = (await db.execute(stmt)).scalar_one_or_none()
        if not camp:
            camp = await CampaignService.create_campaign(
                db=db,
                name="Primary Simulation Campaign",
                dialing_mode=self.dialing_mode,
                priority=1
            )
        self.campaign_id = camp.id

        # 2. Ensure workers initialized
        await WorkerPool.initialize_workers(db, self.num_workers)

        # 3. Ensure agents exist
        agent_count_stmt = select(func.count(Agent.id))
        existing_agents = (await db.execute(agent_count_stmt)).scalar() or 0
        if existing_agents < self.num_agents:
            for i in range(existing_agents + 1, self.num_agents + 1):
                agent = Agent(
                    name=f"Agent-{i:03d}",
                    status=AgentStatus.AVAILABLE
                )
                db.add(agent)
            await db.commit()

        # 4. Ensure queued borrowers exist
        borrower_count_stmt = select(func.count(Borrower.id)).where(Borrower.campaign_id == self.campaign_id)
        existing_borrowers = (await db.execute(borrower_count_stmt)).scalar() or 0
        if existing_borrowers < self.num_borrowers:
            names = [
                "Alex Rivera", "Jordan Smith", "Samira Khan", "David Chen", "Marcus Vance",
                "Elena Rostova", "Liam O'Connor", "Priya Sharma", "Carlos Mendez", "Chloe Bennett"
            ]
            for i in range(existing_borrowers + 1, self.num_borrowers + 1):
                name = f"{names[i % len(names)]} #{i}"
                phone = f"+1-555-{1000 + i:04d}"
                b = Borrower(
                    name=name,
                    phone_number=phone,
                    campaign_id=self.campaign_id,
                    priority=random.randint(1, 3),
                    status=BorrowerStatus.QUEUED,
                    eligible_for_call=True
                )
                db.add(b)
            await db.commit()

    async def step_forward(self):
        """Execute exactly one simulation tick."""
        self.ticks_elapsed += 1
        async with AsyncSessionLocal() as db:
            await self._execute_tick(db)

    async def _simulation_loop(self):
        while self.is_running:
            try:
                if not self.is_paused:
                    self.ticks_elapsed += 1
                    async with AsyncSessionLocal() as db:
                        await self._execute_tick(db)

                sleep_time = max(0.2, self.tick_speed_ms / 1000.0)
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)

    async def _execute_tick(self, db: AsyncSession):
        # Dynamic scenario D fluctuation
        if self.active_scenario_code == "SCENARIO_D":
            cycle = (self.ticks_elapsed // 10) % 4
            rates = [0.20, 0.45, 0.75, 0.30]
            self.answer_rate = rates[cycle]

        # 1. Advance in-flight calls: INITIATED -> RINGING
        initiated_stmt = select(Call).where(Call.call_state == CallState.INITIATED)
        initiated_calls = list((await db.execute(initiated_stmt)).scalars().all())
        for c in initiated_calls:
            evt_id = f"evt-{uuid.uuid4().hex[:12]}"
            await EventProcessor.process_provider_event(
                db=db,
                event_id=evt_id,
                provider_id=c.provider_id,
                call_id=c.id,
                event_type=CallState.RINGING
            )
            if c.provider_id == "PROVIDER_B":
                p_b = get_telecom_provider("PROVIDER_B")
                if p_b and getattr(p_b, "autonomous_anomalies_enabled", False):
                    await p_b.maybe_generate_autonomous_anomalies(db, c.id, evt_id, CallState.RINGING)

        # 2. Advance RINGING calls -> ANSWERED / COMPLETED
        ringing_stmt = select(Call).where(Call.call_state == CallState.RINGING)
        ringing_calls = list((await db.execute(ringing_stmt)).scalars().all())
        for c in ringing_calls:
            evt_id = f"evt-{uuid.uuid4().hex[:12]}"
            # Check answer rate
            if random.random() < self.answer_rate:
                # Answered & connected
                await EventProcessor.process_provider_event(
                    db=db,
                    event_id=evt_id,
                    provider_id=c.provider_id,
                    call_id=c.id,
                    event_type=CallState.CONNECTED
                )
                if c.provider_id == "PROVIDER_B":
                    p_b = get_telecom_provider("PROVIDER_B")
                    if p_b and getattr(p_b, "autonomous_anomalies_enabled", False):
                        await p_b.maybe_generate_autonomous_anomalies(db, c.id, evt_id, CallState.CONNECTED)
            else:
                # Borrower didn't answer / busy
                await EventProcessor.process_provider_event(
                    db=db,
                    event_id=evt_id,
                    provider_id=c.provider_id,
                    call_id=c.id,
                    event_type=CallState.FAILED,
                    payload={"reason": "UNANSWERED_OR_BUSY"}
                )

        # 3. Advance CONNECTED calls -> COMPLETED based on talk time
        connected_stmt = select(Call).where(Call.call_state == CallState.CONNECTED)
        connected_calls = list((await db.execute(connected_stmt)).scalars().all())
        now = datetime.datetime.now(datetime.timezone.utc)
        for c in connected_calls:
            if c.connected_at:
                conn_dt = c.connected_at if c.connected_at.tzinfo else c.connected_at.replace(tzinfo=datetime.timezone.utc)
                elapsed = (now - conn_dt).total_seconds()
                # Exponential completion probability: average talk time scaled
                scaled_talk_time = max(5.0, self.average_talk_time_sec / 10.0) # Speed up slightly for interactive demo
                if elapsed >= scaled_talk_time or random.random() < 0.15:
                    evt_id = f"evt-{uuid.uuid4().hex[:12]}"
                    await EventProcessor.process_provider_event(
                        db=db,
                        event_id=evt_id,
                        provider_id=c.provider_id,
                        call_id=c.id,
                        event_type=CallState.COMPLETED
                    )
                    if c.provider_id == "PROVIDER_B":
                        p_b = get_telecom_provider("PROVIDER_B")
                        if p_b and getattr(p_b, "autonomous_anomalies_enabled", False):
                            await p_b.maybe_generate_autonomous_anomalies(db, c.id, evt_id, CallState.COMPLETED)

        # 4. Trigger dial cycle if campaign is active
        camp = await CampaignService.get_campaign(db, self.campaign_id)
        if camp:
            # Sync mode
            camp.dialing_mode = self.dialing_mode
            db.add(camp)
            await db.commit()

            # Execute real allocation cycle through Pacing Engine -> Safety Controller -> Allocator!
            await CallAllocator.run_allocation_cycle(
                db=db,
                campaign=camp,
                provider_id=self.provider_id,
                risk_factor=0.15
            )

        # 5. Broadcast tick telemetry
        await ws_manager.broadcast("SIMULATION_TICK", {
            "tick": self.ticks_elapsed,
            "answer_rate": round(self.answer_rate, 2),
            "state": self.get_state()
        })

simulation_engine = SimulationEngine()
