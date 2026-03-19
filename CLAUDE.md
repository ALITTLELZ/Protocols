# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Opentrons Protocol Library** — a collection of 835+ OT-2 liquid handling robot protocols, plus a four-stage pipeline that converts Opentrons protocols into structured transfer workflows.

The two main subsystems are:
1. **Protocol Library** (`protocols/`, `protoBuilds/`, `protolib/`) — source protocols, parsed JSON metadata, and the parsing library that powers the Protocol Library website.
2. **Protocol Converter Pipeline** (`protocol_converter/`) — injects hooks, simulates, converts logs to structured steps, and exports transfer-oriented workflows with reagent maps.

## Common Commands

### Protocol Library (website build)

```bash
# Full setup (clones Opentrons monorepo, installs deps)
make setup

# Install dependencies manually
pip install -e otcustomizers
pip install -r protolib/requirements.txt
pip install flake8==3.8.4 pytest

# Parse all protocols and build output
make all -j

# Individual steps
make parse-ot2       # Parse OT2 protocol files to JSON
make parse-errors    # Traverse and collect errors
make parse-README    # Parse README files
make build           # Generate final zipped JSON output
make clean           # Remove protoBuilds/
make teardown        # Remove cloned repos and virtualenvs
```

### Linting

```bash
flake8 protocols/ protolib/
```

### Protocol Converter Pipeline

All scripts run from `protocol_converter/`:

```bash
python modified_code.py              # Stage 1: Inject runtime hooks
python detailed_info_extract.py      # Stage 2: Simulate protocols → log/
python prcxi_protocol_converter.py   # Stage 3: Logs → structured steps (steps/)
python change_to_transfer_group.py   # Stage 4: Steps → transfer workflows (transfer_actions/)
python change_to_transfer_group.py batch  # Batch export all protocols
```

Alternative conversion paths:
- `protocol_from_python.py` — mock-executes protocols directly for step extraction
- `protocol_static_parser.py` — static AST analysis without execution

## Architecture

### Protocol Library Pipeline

- `protocols/<NAME>/*.ot2.apiv2.py` — Source protocol files. Each defines `def run(ctx)` using Opentrons API v2.
- `protocols/<NAME>/fields.json` — Parameter config consumed by `get_values()`.
- `protocols/<NAME>/labware/` — Optional custom labware JSON definitions.
- `protoBuilds/<NAME>/*.json` — Parsed protocol metadata (committed to git for CI speed; regenerate with `make all -j` before PRs).
- `protolib/` — Python module that parses protocols into JSON. Entry point: `python -m protolib`. Key file: `protolib/parse/parseOT2v2.py`.
- `otcustomizers/` — Installable package providing `FileInput` and `StringSelection` parameter types.

### Protocol Converter Pipeline

Data flows: `original copy/` → `log/` → `steps/` → `transfer_actions/`

| Stage | File | Input | Output |
|-------|------|-------|--------|
| 1. Code Injection | `modified_code.py` | `original copy/` protocols | Modified protocols + `detailed_action_json/` |
| 2. Simulation | `detailed_info_extract.py` | Modified protocols | `log/<name>.log` |
| 3. Structured Conversion | `prcxi_protocol_converter.py` | `log/<name>.log` | `steps/<name>.json` |
| 4. Transfer Export | `change_to_transfer_group.py` | `steps/` + `protoBuilds/` | `transfer_actions/<name>.json` |

- `liquid_handler_abstract.py` — PyLabRobot integration with `LiquidHandlerMiddleware` class for hardware abstraction and RViz simulation.

### Key Data Formats

- `steps/<name>.json` — List of phases, each a list of actions (aspirate, dispense, air_gap, blow_out, touch_tip, delay, mix, heater_shaker, magnet, temperature, raw).
- `transfer_actions/<name>.json` — Final export with `workflow` (transfer_liquid actions) and `reagent` map (liquid name → slot/wells/labware).

## Important Notes

- **Hard-coded paths**: `detailed_info_extract.py` contains `sys.path.insert(...)` lines pointing to local Opentrons repo paths. Update these for your environment.
- **Opentrons API version**: Setup clones Opentrons monorepo at tag `v4.3.0`.
- **Python version**: CI uses Python 3.8.
- **protoBuilds are committed**: Run `make all -j` locally and commit `protoBuilds/` changes before PRs.
- **Ignore protocols**: Place a `.ignore` file in a protocol's top-level folder to exclude it from parsing.
- **Error logs**: Check `log/error.txt` and `log/error_converting.txt` when pipeline stages fail.
- **Branch workflow**: `develop` is the main branch. Daily automated PRs merge `develop` → `master` for website releases.
