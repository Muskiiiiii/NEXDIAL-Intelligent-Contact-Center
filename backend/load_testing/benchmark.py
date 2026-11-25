import asyncio
import time
import uuid
import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, func

from app.core.database import Base
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.campaign import Campaign
from app.models.enums import AgentStatus, BorrowerStatus, CampaignStatus, DialingMode, CallState
from app.services.agent_service import AgentService
from app.services.borrower_service import BorrowerService
from app.services.telecom import EventProcessor
from tabulate import tabulate

BENCHMARK_DB_URL = "sqlite+aiosqlite:///./benchmark.db"

async def run_benchmark():
    print("=" * 80)
    print(" NEXDIAL ENTERPRISE PERFORMANCE & LOAD BENCHMARK")
    print(" Evaluating Atomic Allocations, Database Latencies, and Event Throughput")
    print("=" * 80)

    engine = create_async_engine(BENCHMARK_DB_URL, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    scale_tiers = [100, 1000, 10000]
    benchmark_results = []

    for scale in scale_tiers:
        print(f"\n[Tier: {scale:,} Agents]")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as db:
            # 1. Measure Agent & Borrower Seed Latency
            t0 = time.perf_counter()
            agents = [Agent(name=f"Agent-{i}", status=AgentStatus.AVAILABLE) for i in range(scale)]
            borrowers = [
                Borrower(
                    name=f"Borrower-{i}",
                    phone_number=f"+1-555-{i:06d}",
                    status=BorrowerStatus.QUEUED,
                    eligible_for_call=True
                )
                for i in range(scale)
            ]
            db.add_all(agents)
            db.add_all(borrowers)
            await db.commit()
            t_seed = (time.perf_counter() - t0) * 1000 # ms

            # 2. Measure Atomic Agent Reservation Throughput
            # We simulate batch allocation: reserving a batch of 50 agents
            batch_size = min(100, scale)
            t_alloc_start = time.perf_counter()
            reserved = await AgentService.reserve_available_agents_batch(db, limit=batch_size)
            t_alloc_duration = time.perf_counter() - t_alloc_start
            alloc_throughput = len(reserved) / max(0.001, t_alloc_duration) # ops/sec
            avg_reservation_latency_ms = (t_alloc_duration / max(1, len(reserved))) * 1000

            # 3. Measure Concurrent Contention (50 workers competing for same 5 agents)
            target_agent = agents[0]
            # Reset target to AVAILABLE
            await db.execute(update(Agent).where(Agent.id == target_agent.id).values(status=AgentStatus.AVAILABLE))
            await db.commit()

            async def worker_attempt(w_id: int):
                async with session_factory() as local_db:
                    return await AgentService.reserve_agent_atomic(local_db, target_agent.id)

            t_contention_start = time.perf_counter()
            competing_tasks = [worker_attempt(w) for w in range(50)]
            competing_results = await asyncio.gather(*competing_tasks)
            t_contention_duration = (time.perf_counter() - t_contention_start) * 1000

            winners = competing_results.count(True)
            conflicts = competing_results.count(False)

            # 4. Measure Event Processor Throughput (Deduplication & State Update)
            # Create a test call
            call = Call(
                campaign_id=str(uuid.uuid4()),
                borrower_id=borrowers[0].id,
                agent_id=target_agent.id,
                call_state=CallState.INITIATED
            )
            db.add(call)
            await db.commit()
            await db.refresh(call)

            t_evt_start = time.perf_counter()
            event_count = 50
            for ev_idx in range(event_count):
                await EventProcessor.process_provider_event(
                    db=db,
                    event_id=f"bench-evt-{scale}-{ev_idx}",
                    provider_id="PROVIDER_A",
                    call_id=call.id,
                    event_type=CallState.RINGING if ev_idx % 2 == 0 else CallState.ANSWERED
                )
            t_evt_duration = time.perf_counter() - t_evt_start
            event_throughput = event_count / max(0.001, t_evt_duration)

            benchmark_results.append({
                "Agents Count": f"{scale:,}",
                "DB Seed Time (ms)": f"{t_seed:.1f}",
                "Alloc Throughput (ops/s)": f"{alloc_throughput:.1f}",
                "Avg Alloc Latency (ms)": f"{avg_reservation_latency_ms:.2f}",
                "Contention Wins": winners,
                "Contention Conflicts": conflicts,
                "Event Throughput (ops/s)": f"{event_throughput:.1f}"
            })

    await engine.dispose()

    print("\n" + "=" * 80)
    print(" ACTUAL EMPIRICAL BENCHMARK RESULTS")
    print("=" * 80)
    print(tabulate(benchmark_results, headers="keys", tablefmt="psql"))
    print("\nBenchmark Completed Successfully.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
