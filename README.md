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
│   ├── generated_handlers_improved/
│   ├── generated_handlers_text/
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
python scaffold\generator.py docs\schema_example_text.json scaffold\generated_handlers_improved
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

## Contributing

Issues and pull requests are welcome.

---

This project is a prototype for experimentation, schema-driven agent generation, and MIB persistence research.