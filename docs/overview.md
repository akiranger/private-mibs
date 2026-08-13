Overview

Purpose

Provide a lightweight framework to generate AgentX subagent handlers from SMIv2 MIBs and persist managed data using SQLite (durable) and Redis (volatile).

Core components

- mib_parser.py: Minimal MIB parser to produce a JSON schema. Optional pysmi integration for robust parsing.
- generator.py: Takes the JSON schema and emits Python handler modules for each MIB object.
- persistence.py: SQLiteAdapter and RedisAdapter for storage.
- agentx_demo.py: Local harness to simulate AgentX GET/SET calls invoking generated handlers.

Design goals

- Rapid prototyping using SQLite + Redis
- MIB-driven automatic generation of handler skeletons
- Support SNMP v2c and v3 usage scenarios (authentication handled by Agent)
