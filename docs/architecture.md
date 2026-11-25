# System Architecture Specification — NEXDIAL

## 1. Architectural Overview

NEXDIAL is engineered as a **Clean Modular Monolith** designed for high-concurrency progressive dialing, predictive statistical pacing, and fault-tolerant telecom carrier orchestration.

The architecture enforces strict structural isolation: **The Predictive Pacing Engine is prohibited from initiating telephone calls directly.** It operates solely as an advisory component, submitting dial permission requests to an **Independent Safety Controller**.

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & Management Layer"]
        UI["React + Vite Enterprise Console"]
        WSClient["WebSocket Telemetry Client"]
    end

    subgraph OrchestrationLayer ["Orchestration & Policy Layer"]
        CM["Campaign Manager"]
        PE["Pacing Engine (Progressive / Predictive)"]
    end

    subgraph GovernanceLayer ["Safety & Governance Layer (Mandatory Gate)"]
        SC["Independent Safety Controller"]
        Audit["Immutable Audit Log"]
    end

    subgraph ExecutionLayer ["Atomic Allocation Layer"]
        Alloc["Call Allocator (Conditional Row Locking)"]
        WorkerPool["Distributed Worker Pool"]
    end

    subgraph CarrierLayer ["Carrier Abstraction Layer"]
        CB["Circuit Breakers (CLOSED / OPEN / HALF_OPEN)"]
        PA["Mock Provider A (Low Latency)"]
        PB["Mock Provider B (Simulated Jitter & OOO)"]
        EP["Idempotent Event Processor"]
    end

    subgraph PersistenceLayer ["Persistence Layer (Source of Truth)"]
        DB[("PostgreSQL / SQLite WAL Engine")]
    end

    UI <-->|REST & WebSockets| CM
    UI <-->|Telemetry Stream| WSClient
    CM -->|Campaign Directives| PE
    PE -->|Dial Permission Request| SC
    SC -->|APPROVE / REDUCE / REJECT| Alloc
    SC -->|Record Audit| Audit
    Audit --> DB
    Alloc -->|Atomic Conditional UPDATE| DB
    Alloc -->|Dispatch Approved Calls| CB
    CB --> PA
    CB --> PB
    PA -->|Webhook Events| EP
    PB -->|Webhook Events| EP
    EP -->|Monotonic State Progression| DB
    WorkerPool -->|Job Execution & Heartbeats| Alloc
```

---

## 2. Component Directory & Responsibilities

| Component | Module | Responsibility | Invariants |
| :--- | :--- | :--- | :--- |
| **Campaign Manager** | `app.services.campaign_service` | Defines campaign targets, max attempts, retry intervals, target abandon rate. | Never allows duplicate campaigns to process the same borrower simultaneously. |
| **Pacing Engine** | `app.services.pacing_engine` | Evaluates queue demand, smoothed answer rate, talk times, and near-term agent releases. | **Never dispatches telecom calls.** Only computes advisory requests. |
| **Safety Controller** | `app.services.safety_controller` | Evaluates system capacity directly from DB rows. Emits `APPROVE`, `REDUCE`, `REJECT`, `FALLBACK_TO_PROGRESSIVE`. | Zero borrower connects without an assigned agent. Bypassing is architecturally impossible. |
| **Call Allocator** | `app.services.call_allocator` | Transactionally binds agent and borrower using atomic SQL updates. Rolls back reservations on carrier initiation errors. | Never leaves an agent or borrower locked in `RESERVED` upon failure. |
| **Telecom Interface** | `app.services.telecom` | Standardizes outbound carrier APIs, manages Circuit Breakers per provider. | Protects carriers from cascading load when error rates spike. |
| **Event Processor** | `app.services.telecom.event_processor` | Deduplicates carrier webhooks by `event_id`. Enforces monotonic call state progression. | Older/late events can never regress a call from `COMPLETED` back to earlier states. |
| **Worker Pool** | `app.services.worker_pool` | Distributed worker simulation with leases, heartbeats, and stale reservation recovery. | Reconciles orphaned reservations (>15s) left by crashed workers without double dialing. |

---

## 3. The Five-Phase Allocation Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Worker as Dialing Worker
    participant PE as Pacing Engine
    participant SC as Safety Controller
    participant DB as Database (Source of Truth)
    participant Alloc as Call Allocator
    participant Tel as Telecom Provider

    Worker->>PE: Compute Dial Request for Campaign
    PE->>DB: Query Historical Answer Rates & Active Calls
    DB-->>PE: Stats (Smoothed Answer Rate = 42%, Avg TT = 68s)
    PE->>SC: Request Permission (e.g. 15 Dials)

    SC->>DB: Atomic Capacity Snapshot (Available, Ringing, Reserved)
    DB-->>SC: Snapshot (10 Available, 2 Ringing, 0 Reserved)
    SC->>SC: Evaluate Constraints: Safe Headroom = 8
    SC->>DB: Commit Immutable Safety Decision (REDUCE to 8)
    SC-->>Alloc: Approved 8 Calls (Reduced by 7)

    loop For Each Approved Call (up to 8)
        Alloc->>DB: UPDATE Agent SET status='RESERVED' WHERE status='AVAILABLE'
        DB-->>Alloc: Rowcount = 1 (Acquired)
        Alloc->>DB: UPDATE Borrower SET status='RESERVED' WHERE status='QUEUED'
        DB-->>Alloc: Rowcount = 1 (Acquired)
        Alloc->>Tel: InitiateCall(call_id, to_number)
        Tel-->>Alloc: ProviderEvent(INITIATED, provider_call_id)
        Alloc->>DB: Advance Call to INITIATED & Agent to DIALING
    end
```
