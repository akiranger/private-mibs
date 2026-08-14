Embedded deployment guidance

Overview

This document provides practical recommendations when deploying the project on resource-constrained embedded devices (limited RAM/Flash/CPU) where durability and lifetime of storage (Flash) are concerns.

SQLite configuration

- Defaults in code: the SQLiteAdapter applies these pragmatic defaults:
  - PRAGMA busy_timeout = 30000 (30s) to reduce SQLITE_BUSY on concurrent writes
  - PRAGMA journal_mode = WAL to allow concurrent readers during writes
  - PRAGMA synchronous = NORMAL to balance durability and performance on flash

- Recommendations:
  - For extremely low-write workloads prefer journal_mode = DELETE and synchronous = FULL only if Flash endurance is not a concern; otherwise WAL + synchronous=NORMAL is a good balance.
  - Consider using an external flash-friendly filesystem (e.g., F2FS) or a wear-leveling layer for raw flash devices.
  - If power-loss durability is critical, set synchronous = FULL and ensure filesystems are mounted with write barriers enabled.

Durability and fsync strategy

- WAL mode writes a separate write-ahead log which can increase write amplification; measure Flash endurance accordingly.
- synchronous = NORMAL reduces number of fsyncs (better performance) but risks losing a small amount of recent transactions on power loss. Use FULL for maximum safety.
- Provide a configuration knob (SQLiteAdapter.pragmas) to adjust these settings at runtime depending on device capabilities.

Lightweight subagent options

- If Python runtime is too heavy, implement a minimal C-based subagent (e.g. net-snmp subagent) that interacts with a lightweight IPC or small database. Keep the Python components for management and offline tooling.
- Consider cross-compiling a small C agent that exposes a JSON/CBOR-over-UNIX-socket API that the Python tooling can use for heavier operations.

Benchmarks and minimum requirements

- Suggested smoke checks to include in device images:
  - Startup time: measure time from process spawn to ready (import and main loop) — target <250ms on constrained boards where possible.
  - Resident memory snapshot (RSS) after initialization — target depends on device, but document observed numbers for each supported board.
  - SQLite write latency: run a small bulk_upsert of N rows and measure mean/95th percentile latency.

Examples

- The repository includes run_smoke_getbulk.py and scripts/run_benchmarks.py (proposed) that can be adapted to target platforms. Use them to gather baseline numbers during CI or on-device tests.

Operational notes

- Keep secrets out of filesystem where possible; use platform keyrings or TPMs for USM user keys.
- Document expected minimum RAM and storage for images that include Python 3 and dependencies like pysnmp/pysmi.

If you want, the next step is to add a small benchmarks script (cross-platform) and a README section with suggested target numbers for common embedded boards. 