# AgentX MIB Persistence Framework

A prototype framework for generating MIB-driven schemas and managing AgentX-style subagent state with SQLite for persistence and Redis for volatile runtime data.

## Overview

This project demonstrates a workflow for:

- parsing SMIv2 MIB definitions into schema data
- generating Python handlers from that schema
- persisting managed values with SQLite
- using Redis for transient or cache-like state
- simulating GET/SET operations for prototype validation

The repository is intended as a lightweight experimental foundation for MIB-aware AgentX development.

## Features

- SMIv2 MIB parsing and schema extraction
- Generator-based handler creation from schema definitions
- SQLite-backed persistent state management
- Redis-backed ephemeral state management
- Demo flow for simulated GET/SET behavior
- Example schema and documentation for experimentation

## Project Structure

```text
.
├── README.md
├── data/
├── design/
├── docs/
├── example/
├── scaffold/
│   ├── generated_handlers/
│   ├── mibs/
│   └── ...
├── tests/
└── ...
```

## Quick Start

Prerequisites: Python 3.8+

1. Install optional dependencies

```bash
pip install redis pysmi pysnmp
```

2. Parse the sample MIB and generate a schema JSON

```bash
python scaffold\mib_parser_text_advanced.py example\EXAMPLE-MIB > docs\schema_example_text.json
```

3. Generate handlers from the schema

```bash
python scaffold\generator.py docs\schema_example_text.json scaffold\generated_handlers
```

4. Run the demo flow (simulated GET/SET)

```bash
python scaffold\agentx_demo.py myScalar get
python scaffold\agentx_demo.py myScalar set 123
```

## Documentation

Key documents:

- [docs/overview.md](docs/overview.md)
- [docs/quickstart.md](docs/quickstart.md)
- [docs/parser.md](docs/parser.md)
- [docs/persistence.md](docs/persistence.md)
- [docs/generator.md](docs/generator.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/agentx_integration.md](docs/agentx_integration.md)

## Notes

- Generated code under `scaffold/generated_handlers*` is kept out of Git tracking via `.gitignore`; placeholder `.gitkeep` files are included so the directories remain in the repository.
- Installing `pysmi` and `pysnmp` can improve MIB extraction accuracy, but a standard MIB repository or proper local MIB configuration may still be needed. See [docs/parser.md](docs/parser.md) and [docs/agentx_integration.md](docs/agentx_integration.md) for more information.
- For quick integration with net-snmp on Linux, see `scaffold/agentx_pass_persist.py` (pass_persist helper) and docs/agentx_integration.md for configuration examples.

## Contributing

Issues and pull requests are welcome.

---

This project is a prototype for experimentation, schema-driven agent generation, and MIB persistence research.

Deployment (snmpd + pass_persist) — quick steps

1. Create mapping: copy scaffold/agentx_mapping.example.json -> /etc/snmp/agentx_mapping.json and edit OIDs as needed.
2. Install or confirm net-snmp (snmpd) is present and writable config path is /etc/snmp/snmpd.conf.
3. Add the pass_persist line to /etc/snmp/snmpd.conf:
   pass_persist .1.3.6.1.4.1.53864 /usr/bin/python3 /opt/project/scaffold/agentx_pass_persist.py /etc/snmp/agentx_mapping.json
4. (Optional) Deploy helper as a service for debugging: see docs/snmpd_systemd_examples.md for unit examples.
5. Restart snmpd: sudo systemctl daemon-reload && sudo systemctl restart snmpd
6. Verify: snmpget -v2c -c public localhost 1.3.6.1.4.1.53864.1.0

For PR reviewers

- This PR adds: scaffold/agentx_pass_persist.py, mapping example, docs/snmpd_systemd_examples.md and docs/agentx_integration_full.md. Verify that the pass_persist protocol and handler-loading behaviour match generated handlers and that the documentation describes safe deployment steps.
- Testing: run the helper locally with:
  echo -e "PING\nGET <oid>\n" | python3 scaffold/agentx_pass_persist.py scaffold/agentx_mapping.example.json

