from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter(prefix="/architecture", tags=["Architecture"])

@router.get("/components")
async def get_architecture_components() -> Dict[str, Any]:
    nodes = [
        {
            "id": "campaign_manager",
            "name": "Campaign Manager",
            "layer": "Orchestration",
            "responsibility": "Manages dialing campaigns, target metrics (abandon rate <= 3%), agent assignment, and queue prioritization.",
            "inputs": ["Operator Configurations", "Borrower Queues", "Target Abandon Thresholds"],
            "outputs": ["Active Campaign Directives", "Pacing Trigger Events"],
            "failure_handling": "Prevents cross-campaign borrower duplicate processing. Automatically pauses when queues are exhausted.",
            "backend_module": "app.services.campaign_service"
        },
        {
            "id": "pacing_engine",
            "name": "Pacing Engine",
            "layer": "Algorithmic Pacing",
            "responsibility": "Computes optimal dial count using Progressive 1:1 rule or statistical predictive formula with smoothed answer rates and near-term releases. NEVER dials directly.",
            "inputs": ["Available Agents", "Historical Answer Rate", "Talk Times", "Setup Latency"],
            "outputs": ["Requested Dial Count", "Mathematical Justification", "Risk-Buffered Projections"],
            "failure_handling": "Detects volatile answer rate variance and automatically recommends fallback to Progressive mode.",
            "backend_module": "app.services.pacing_engine"
        },
        {
            "id": "safety_controller",
            "name": "Safety Controller",
            "layer": "Safety & Governance",
            "responsibility": "Independent final authority. Enforces zero borrower abandonment without available agent. Emits APPROVE, REDUCE, REJECT, or FALLBACK_TO_PROGRESSIVE.",
            "inputs": ["Dial Requests", "Real-Time DB Capacity Snapshot", "Provider Circuit Status"],
            "outputs": ["Approved Dial Count", "Immutable Audit Records", "Capacity Constraints"],
            "failure_handling": "Rejects dials when provider circuit is OPEN or available agent headroom is consumed by in-flight calls.",
            "backend_module": "app.services.safety_controller"
        },
        {
            "id": "call_allocator",
            "name": "Call Allocator",
            "layer": "Atomic Execution",
            "responsibility": "Executes approved calls using conditional atomic database reservations on agents and borrowers. Handles transactional rollback on provider rejection.",
            "inputs": ["Approved Calls from Safety Controller", "Eligible Queues"],
            "outputs": ["Allocated Call Records", "Dispatched Telecom Packets"],
            "failure_handling": "If borrower reservation or carrier handshake fails, reserved agent is atomically rolled back to AVAILABLE within transaction.",
            "backend_module": "app.services.call_allocator"
        },
        {
            "id": "telecom_layer",
            "name": "Provider Abstraction Layer",
            "layer": "Carrier Integration",
            "responsibility": "Abstracts carrier nuances. Manages Circuit Breakers (CLOSED, OPEN, HALF_OPEN) and dispatches across Provider A and B.",
            "inputs": ["Standardized InitiateCall Requests", "Hangup Directives"],
            "outputs": ["Raw Provider Packets", "Latency & Health Telemetry"],
            "failure_handling": "Trips circuit breaker upon consecutive failures; redirects traffic to healthy carrier.",
            "backend_module": "app.services.telecom.circuit_breaker"
        },
        {
            "id": "event_processor",
            "name": "Idempotent Event Processor",
            "layer": "State Reconciliation",
            "responsibility": "Deduplicates carrier events, enforces monotonic call state progression (no regressing completed calls), and triggers agent release.",
            "inputs": ["INITIATED, RINGING, ANSWERED, CONNECTED, COMPLETED Events"],
            "outputs": ["Durable Event Records", "State Transition Broadcasts"],
            "failure_handling": "Safely discards duplicate event IDs and logs out-of-order state transitions without regressing database state.",
            "backend_module": "app.services.telecom.event_processor"
        },
        {
            "id": "worker_pool",
            "name": "Distributed Worker Pool",
            "layer": "Concurrency & Resilience",
            "responsibility": "Runs concurrent workers with leases and heartbeats. Reconciles orphaned reservations if a worker terminates abruptly.",
            "inputs": ["Worker Heartbeats", "Queue Batches"],
            "outputs": ["Job Execution Status", "Recovery Metrics"],
            "failure_handling": "Scans for stale reservations > 15s from crashed workers, reconciling calls and freeing locked agents.",
            "backend_module": "app.services.worker_pool"
        },
        {
            "id": "database",
            "name": "PostgreSQL / SQLite WAL",
            "layer": "Persistence (Source of Truth)",
            "responsibility": "Provides ACID transactional guarantees, row-level conditional locking, and immutable audit logs.",
            "inputs": ["Atomic UPDATE ... WHERE queries", "Audit Inserts"],
            "outputs": ["Confirmed State Commits", "Read Snapshots"],
            "failure_handling": "Write-Ahead Logging (WAL) ensures crash durability and non-blocking reads.",
            "backend_module": "app.core.database"
        }
    ]

    edges = [
        {"from": "campaign_manager", "to": "pacing_engine", "label": "Campaign Directives"},
        {"from": "pacing_engine", "to": "safety_controller", "label": "Dial Permission Request"},
        {"from": "safety_controller", "to": "call_allocator", "label": "Approved Dial Allocation"},
        {"from": "call_allocator", "to": "telecom_layer", "label": "Carrier Dispatch"},
        {"from": "telecom_layer", "to": "event_processor", "label": "Carrier Webhooks / Events"},
        {"from": "event_processor", "to": "database", "label": "Monotonic State Commits"},
        {"from": "call_allocator", "to": "database", "label": "Atomic Conditional Reservations"},
        {"from": "safety_controller", "to": "database", "label": "Real-time Capacity Queries & Audit Log"},
        {"from": "worker_pool", "to": "call_allocator", "label": "Worker Job Execution"}
    ]

    return {"nodes": nodes, "edges": edges}
