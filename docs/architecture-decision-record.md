# Architecture Decision Records (ADRs) — NEXDIAL

## ADR-001: Clean Modular Monolith over Distributed Microservices

### Context
Contact centers require high transaction integrity, sub-millisecond coordination between agent availability and call allocation, and strict abandonment limits. An initial consideration was to build separate microservices for Campaigns, Pacing, Safety, and Telecom.

### Decision
We rejected microservices in favor of a **Clean Modular Monolith** implemented with Python FastAPI and SQLAlchemy.

### Consequences
- **Pros:** Zero network hops between Pacing, Safety, and Call Allocation. Eliminates distributed transactions (2PC/Sagas) and partial failure partitions. Simplifies local testing and benchmark reproducibility.
- **Cons:** Shared CPU and memory space. Mitigated by async I/O (`asyncio`, `aiosqlite`, `asyncpg`) and clean domain module boundaries.

---

## ADR-002: Relational Database as Single Source of Truth over In-Memory Cache (Redis)

### Context
Predictive dialers frequently suffer from "split-brain" allocation bugs when agent statuses are tracked in in-memory caches (e.g. Redis) that fall out of sync with the persistent database during worker crashes or network partitions.

### Decision
The relational database (PostgreSQL in production, SQLite with WAL mode in development/testing) is the **exclusive, authoritative source of truth** for agent availability, call states, and borrower queue reservations.

### Consequences
- **Pros:** Strict ACID transactional consistency. If a worker crashes midway, atomic row states in the database guarantee no orphaned resources or duplicate call initiations.
- **Cons:** Higher write load on the database. Mitigated by index tuning, conditional row updates (`UPDATE ... WHERE status = 'AVAILABLE'`), and batch queries.

---

## ADR-003: Architectural Decoupling of Pacing Engine and Safety Controller

### Context
A classic vulnerability in predictive pacing algorithms is aggressive overdialing when borrower answer rates drop, leading to borrowers answering calls with no available agents (abandoned connected calls).

### Decision
The **Pacing Engine is structurally isolated from telecom dispatch.** It has zero network access to carrier clients. It can only generate advisory requests sent to the **Independent Safety Controller**. The Safety Controller has sole veto authority and commits an immutable audit record for every decision.

### Consequences
- **Pros:** 100% guarantee that pacing algorithms cannot bypass safety constraints, carrier circuit breakers, or zero-abandonment rules.
- **Cons:** Adds an explicit validation step to every dialing cycle (~0.5ms database snapshot overhead).

---

## ADR-004: Atomic Conditional SQL Updates (`UPDATE ... WHERE`) over Distributed Distributed Mutexes

### Context
In multi-worker environments, two workers must never allocate the same agent simultaneously. Distributed locks (e.g. Redlock) introduce lease expiration hazards, clock drift vulnerabilities, and coordination overhead.

### Decision
We use atomic conditional SQL updates:
```sql
UPDATE agents
SET status = 'RESERVED', last_status_change = CURRENT_TIMESTAMP
WHERE id = :agent_id AND status = 'AVAILABLE';
```
If `rowcount == 1`, reservation was atomically acquired. If `rowcount == 0`, another worker won the lock and the caller cleanly backs off.

### Consequences
- **Pros:** Supported natively across SQLite and PostgreSQL. Zero external lock manager dependencies. Complete mathematical exclusion verified by concurrency benchmarks (1 winner, 49 conflicts out of 50 concurrent attempts).
- **Cons:** None in this architecture.

---

## ADR-005: Monotonic State Progression for Carrier Webhooks

### Context
Carrier webhooks arrive out of order (e.g. `COMPLETED` before late `RINGING`) or duplicate times due to network retries.

### Decision
We assigned monotonic integer ranks to call states (`INITIATED: 1, RINGING: 2, ANSWERED: 3, CONNECTED: 4, COMPLETED: 5`). An incoming event with rank $\le$ current rank cannot regress state. Duplicate event IDs are durably cached and discarded idempotently.
