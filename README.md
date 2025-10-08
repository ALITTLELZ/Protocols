# Protocol Simulation → Structured Steps → Transfer Export

This repository implements a four‑stage pipeline that **injects runtime hooks into Opentrons protocols**, **simulates** them to collect logs, **converts** those logs into structured steps, and **exports** a **transfer‑oriented workflow + reagent map**.

> **Note on current version**  
> The final exported workflow intentionally omits granular runtime details. Those details are preserved (when available) in `detailed_action_json/<protocol>.json` for future use.

---

## Table of Contents

- [Overview](#overview)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quickstart](#quickstart)
- [Stage 1 — Code Injection (`modified_code.py`)](#stage-1--code-injection-modified_codepy)
- [Stage 2 — Simulation (`detailed_info_extract.py`)](#stage-2--simulation-detailed_info_extractpy)
- [Stage 3 — Log → Structured Steps (`prcxi_protocol_converter.py`)](#stage-3--log--structured-steps-prcxi_protocol_converterpy)
- [Stage 4 — Steps → Transfer + Reagents (`change_to_transfer_group.py`)](#stage-4--steps--transfer--reagents-change_to_transfer_grouppy)
- [Data Formats](#data-formats)
- [Troubleshooting](#troubleshooting)
- [Notes & Limitations](#notes--limitations)

---

## Overview

**Pipeline stages**

1. **Code Injection — `modified_code.py`**  
   Injects an introspection block inside each protocol’s `def run(...)`, so that **liquid locations** and (if used) **event logs** can be written into `detailed_action_json/` at runtime.

2. **Simulation — `detailed_info_extract.py`**  
   Runs Opentrons **simulation** for all protocols in `original copy/`. Produces human‑readable run logs in `log/`.

3. **Structured Conversion — `prcxi_protocol_converter.py`**  
   Parses the run logs into **phases** and **actions**, merges compatible phases (e.g., same source→dest route), and writes `steps/<protocol>.json`.

4. **Transfer Export — `change_to_transfer_group.py`**  
   Aggregates per‑phase actions into **transfer_liquid** items and builds a **reagent** map from the protocol JSON in `protoBuilds/`. Exports `<protocol>_transfer_actions.json` or batch outputs under `transfer_actions/`.

---

## Repository Layout

```
project-root/
├─ original copy/
│  └─ <PROTOCOL_NAME>/
│     ├─ *.py                 # Opentrons protocols (must define def run(ctx))
│     ├─ fields.json          # Parameter config consumed by get_values()
│     └─ labware/             # Optional custom labware JSONs
├─ protoBuilds/
│  └─ <PROTOCOL_NAME>/
│     └─ *.json               # e.g., <PROTOCOL_NAME>.ot2.apiv2.py.json
├─ detailed_action_json/
│  └─ <PROTOCOL_NAME>.json    # (injected) event_logs + liquid_locations
├─ log/
│  ├─ <PROTOCOL_NAME>.log     # Simulation logs (human-readable)
│  ├─ error.txt
│  └─ error_converting.txt
├─ steps/
│  └─ <PROTOCOL_NAME>.json    # Structured phases/actions
└─ transfer_actions/
   └─ <PROTOCOL_NAME>.json    # Final transfer workflow + reagents
```

> Some script paths are **hard‑coded**. If you move the project/machine, update those paths in the scripts (see notes below).

---

## Prerequisites

- Python environment with the **Opentrons API** available.

- Update the **hard‑coded local Opentrons paths** in `detailed_info_extract.py` (two `sys.path.insert(...)` lines) to point to your environment:

  ```python
  sys.path.insert(0, '/path/to/opentrons/api/src')
  sys.path.insert(0, '/path/to/opentrons/shared-data/python')
  ```

- Protocol folders under `original copy/<PROTOCOL_NAME>/` should contain:

  - a Python protocol implementing `def run(ctx): ...`
  - a `fields.json` file (see example below)
  - optionally, a `labware/` directory with custom labware JSON(s)

---

## Quickstart

From the repository root:

```bash
# 1) Inject runtime hooks into each protocol's run()
python modified_code.py

# 2) Simulate all protocols and write logs to log/<name>.log
python detailed_info_extract.py

# 3) Convert simulation logs into structured steps (steps/<name>.json)
python prcxi_protocol_converter.py

# 4a) Export a single protocol’s transfer + reagent JSON (example name is set in the script)
python change_to_transfer_group.py

# 4b) Batch export: generate all transfer JSONs into transfer_actions/
python change_to_transfer_group.py batch
```

> Check `log/error.txt` and `log/error_converting.txt` if any run fails.

---

## Stage 1 — Code Injection (`modified_code.py`)

**What it does**

- Walks `original copy/` and opens every `*.py` protocol.

- Locates `def run(...)` and injects an introspection block that inspects **local variables** for `Well` and `list[Well]` objects:

  - Parses each `Well.display_name` to extract **well position** (e.g., `A1`) and **slot** (deck position).
  - Builds `liquid_locations` mapping variable names (including indexed list entries like `wells[0]`) to `{ "well": "A1", "slot": "1" }`.

- Writes `detailed_action_json/<FOLDERNAME>.json` at runtime containing:

  ```json
  {
    "event_logs": builtins.event_logs,
    "liquid_locations": { "...": { "well": "...", "slot": "..." } }
  }
  ```

**Additional behavior**

- If the protocol file doesn’t already define it, the injector **prepends**:

  ```python
  import builtins
  builtins.event_logs = []
  __protocol_file__ = r"/absolute/path/to/the/protocol.py"
  ```

  so later stages can resolve `fields.json` and (if used by your protocol) append to `builtins.event_logs`.

**Run**

```bash
python modified_code.py
```

---

## Stage 2 — Simulation (`detailed_info_extract.py`)

**What it does**

- Adds your local Opentrons paths to `sys.path`.

- Defines `get_values(*names)` and sets `builtins.get_values = get_values` so protocols read parameters from the colocated `fields.json` (next to the original protocol file identified by `__protocol_file__`).

- Simulates each protocol under `original copy/` via:

  ```python
  runlog, bundled = simulate(
      protocol_file=open(file, "r"),
      custom_labware_paths=[str(labware_dir)] if labware_dir.exists() else []
  )
  ```

- Writes `log/<FOLDERNAME>.log` and appends errors to `log/error.txt`.

**Minimal `fields.json` example**

```json
[
  { "name": "aspirate_volume", "default": 10 },
  { "name": "dispense_volume", "default": 10 }
]
```

**Run**

```bash
python detailed_info_extract.py
```

---

## Stage 3 — Log → Structured Steps (`prcxi_protocol_converter.py`)

**What it does**

- Reads each protocol’s log from `log/<name>.log`.
- Splits the log into **phases** and parses **actions** using pattern matching/regex.
- **Merges** phases when they share compatible routes (e.g., same `(src_slot → dst_slot)`), and prepends aspirate‑only phases to the subsequent dispense phase where applicable.
- Writes **high‑level steps** to `steps/<name>.json`.

**Recognized operations (examples)**

- Liquid handling:
  - `aspirate` → `{ "action": "aspirate", "vol": 10.0, "source": { "well": "A1", "labware": "Plate", "slot": 1 }, "flow_rate": 1.0 }`
  - `dispense` → `{ "action": "dispense", "vol": 10.0, "target": { "well": "B1", "labware": "Plate", "slot": 2 }, "flow_rate": 1.0 }`
  - `air_gap`, `blow_out`, `touch_tip`, `delay`
- Modules:
  - `heater_shaker` aggregate: target temperature, wait flag, shake speed, duration, deactivation flags
  - `magnet` engage/disengage, `temperature` set/off

**Run**

```bash
python prcxi_protocol_converter.py
```

This will create `steps/<name>.json` for each protocol found.

---

## Stage 4 — Steps → Transfer + Reagents (`change_to_transfer_group.py`)

**What it does**

- Loads `steps/<name>.json` and the matching protocol JSON from `protoBuilds/<name>/*.json`.
- Extracts/compacts **labware** slots (keeping original numbering if ≥ 12; otherwise compacts distinct slots into `1..total_slots` with order preserved; default `total_slots=12`).
- Aggregates each phase into a single action summary with:
  - sets of **aspirate** wells and **dispense** wells (as `(slot, well)` pairs)
  - **average volumes** and **average flow rates** for aspirate/dispense across that phase
- Assigns **liquid names** per phase:
  - All **aspirate** wells in one phase share the same **source liquid** name.
  - All **dispense** wells in one phase share the same **target liquid** name.
  - If a well was assigned earlier, its **existing liquid name** is reused.
- Produces:
  - A list of `"transfer_liquid"` actions for phases that have **both** aspirate and dispense.
  - A **reagent** map: liquid name → `{slot, wells[], labware}`.

**Single file export (script default example uses a hardcoded protocol name)**

```bash
python change_to_transfer_group.py
# prints a summary and writes: <protocol>_transfer_actions.json
```

**Batch export**

```bash
python change_to_transfer_group.py batch
# writes: transfer_actions/<protocol>.json and transfer_actions/batch_summary.json
```

---

## Data Formats

### `detailed_action_json/<name>.json` (written by injected code during run)

```json
{
  "event_logs": [],               // from builtins.event_logs (if your protocol populates it)
  "liquid_locations": {
    "wells[0]": { "well": "A1", "slot": "1" },
    "sample_A1": { "well": "A1", "slot": "1" }
  }
}
```

> `event_logs` exists to preserve raw runtime details if your protocol appends to `builtins.event_logs`.

### `log/<name>.log` (simulation output)

Human‑readable Opentrons simulate log used by the converter.

### `steps/<name>.json` (structured phases/actions)

A JSON list of **phases**, where each phase is a list of **actions**. Example (single phase):

```json
[
  [
    {
      "action": "aspirate",
      "vol": 10.0,
      "source": { "well": "A1", "labware": "96 Well Plate", "slot": 1 },
      "flow_rate": 1.0
    },
    {
      "action": "dispense",
      "vol": 10.0,
      "target": { "well": "B1", "labware": "96 Well Plate", "slot": 2 },
      "flow_rate": 1.0
    }
  ]
]
```

Other actions that may appear in phases: `air_gap`, `blow_out`, `touch_tip`, `delay`, `mix`, `heater_shaker`, `magnet`, `temperature`, `raw`.

### `<protocol>_transfer_actions.json` (final export)

```json
{
  "workflow": [
    {
      "action": "transfer_liquid",
      "action_args": {
        "sources": "Liquid_1"             // or ["Liquid_1", "Liquid_2"]
        ,
        "targets": "Liquid_2"             // or ["Liquid_3", ...]
        ,
        "asp_vol": 10.0,
        "dis_vol": 10.0,
        "asp_flow_rate": 1.0,
        "dis_flow_rate": 1.0
      }
    }
  ],
  "reagent": {
    "Liquid_1": { "slot": 1, "well": ["A1","A2"], "labware": "..." },
    "Liquid_2": { "slot": 2, "well": ["B1"],      "labware": "..." }
  }
}
```

> Liquid names are automatically generated as `Liquid_<n>` and reused if a well was assigned earlier in the run.

---

## Troubleshooting

- **No `steps/*.json` produced**  
  Check `log/<name>.log` exists and make sure `prcxi_protocol_converter.py` ran without exceptions (see `log/error_converting.txt`).

- **Simulation import errors**  
  Update the two `sys.path.insert(...)` lines in `detailed_info_extract.py` to your local Opentrons paths.

- **Custom labware not found**  
  Put JSONs under `original copy/<name>/labware/`. The simulator is invoked with `custom_labware_paths=[that_folder]` if it exists.

- **Slot compaction mismatch**  
  `extract_labware_info_from_json(..., total_slots=12)` keeps original slots if `total_slots >= 12`. If you reduce the deck size, ensure the number of distinct slots in the protocol does not exceed the limit.

- **Empty `event_logs` in `detailed_action_json`**  
  The injected file writes `builtins.event_logs`. If your protocol does not append to it, this array will be empty; that’s expected in the current version.

---

## Notes & Limitations

- Absolute paths are present in the scripts (e.g., local Opentrons repo locations). Adjust them for your environment.
- Phase merging heuristics are åconservative: aspirate‑only segments may be prepended to the next phase; adjacent compatible routes are merged to reduce fragmentation.
- The exported transfer workflow focuses on **aspirate+dispense** phases. Phases without both are omitted from the final `"workflow"` list.
