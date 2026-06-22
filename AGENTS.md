# AGENTS.md — FPGA Agent 操作手册

> **Always read this file first.** It defines project structure, conventions, and operational rules.

---

## 1. Repository Layout

```
<workspace>/
├── AGENTS.md              ← THIS FILE — read first
├── README.md              ← Human-readable guide
│
├── agent_tools/           ← Core automation (agent uses these)
│   ├── sim_driver.py      ← Simulation engine (cocotb runner wrapper)
│   ├── fpga_tools.py      ← Project scanner + CLI (scan/summary/run)
│   ├── project_gen.py     ← Project skeleton generator
│   └── reference_reader.py ← Reads files from reference/
│
├── knowledge/             ← Agent-maintained knowledge base
│   ├── _index.md          ← Master index of all knowledge items
│   ├── simulator/         ← Simulator-specific quirks
│   └── patterns/          ← Reusable RTL + testbench patterns
│
├── docs/
│   ├── SIMULATOR_GUIDE.md ← Low-level timing model (read if unsure)
│   └── WORKFLOW.md        ← Step-by-step development phases
│
├── examples/              ← Pre-built reference projects
│   ├── 01_adder/           (combinational)
│   ├── 02_vending_machine/ (FSM + pulsed inputs)
│   ├── 03_debounce/        (FSM + timer + pulse output)
│   ├── 04_uart_tx/         (dual-counter + serial)
│   ├── 05_fifo/            (circular buffer + pointers)
│   ├── 06_spi_master/      (clock phase + shift + CS)
│   ├── 07_counter/         (up/down + load + enable)
│   └── 08_config_demo/     (project.json includes/defines/parameters)
│
├── templates/             ← Project & testbench skeletons
│   ├── project.json
│   ├── tb_basic.py
│   └── tb_comprehensive.py
│
├── reference/             ← Human places input files here (agent READS ONLY)
├── outputs/               ← Agent writes generated projects here
└── reports/               ← Agent writes post-project reviews here
```

**Ownership**: `reference/` is human-write, agent-read. `outputs/` and `reports/` are agent-write. `knowledge/` is agent-maintained.

---

## 2. Project Structure Convention

Every FPGA project follows this layout:

```
outputs/<project_name>/
├── project.json          ← Auto-generated config
├── src/
│   └── *.sv / *.v        ← RTL sources
└── tb/
    └── test_*.py         ← cocotb testbench
```

### project.json format

```json
{
    "sources": ["src/module1.sv", "src/module2.sv"],
    "toplevel": "top_module",
    "test_module": "tb.test_top",
    "sim": "verilator",
    "includes": ["src/include"],
    "defines": {"WIDTH": 8, "ENABLE_DBG": 1},
    "parameters": {"DEPTH": 32},
    "timescale": ["1ns", "1ps"]
}
```

**Required**: `sources`, `toplevel`, `test_module`.
**Optional** (all default to empty/none):
- `sim` — simulator (default `verilator`)
- `includes` — `+incdir` dirs for `` `include `` headers (paths relative to project root)
- `defines` — Verilog macros (`` `ifdef ``); use a value like `1` for bare flags, not `null`
- `parameters` — top-level parameter overrides (e.g. resize a FIFO at build time)
- `timescale` — `["unit", "precision"]` or `"1ns/1ps"`

> `sources` is a list — list multiple files for hierarchical/multi-module designs.
> See `examples/08_config_demo/` for a live example using all optional fields.

---

## 3. Running Tasks

```bash
# Use relative paths from workspace root!
python agent_tools/fpga_tools.py summary examples/01_adder
python agent_tools/fpga_tools.py lint examples/01_adder
python agent_tools/fpga_tools.py run examples/01_adder
python agent_tools/fpga_tools.py run outputs/my_project --json
python agent_tools/fpga_tools.py run outputs/my_project --no-lint
```

All commands run from the **workspace root** (where this AGENTS.md lives).

---

## 4. Standard Workflow

### Phase 0: Understand
1. Read requirements
2. Check `reference/` for input files (use `reference_reader.py`)
3. Search `knowledge/_index.md` for relevant patterns

### Phase 1: Design
1. Define module interface (ports, parameters)
2. Design FSM if stateful
3. List test scenarios (normal, boundary, error)

### Phase 2: Generate Project
```python
from agent_tools.project_gen import create_project
path = create_project(name="my_module", sources=["src/my_module.sv"],
                      toplevel="my_module", test_module="tb.test_my_module",
                      output_dir="outputs/my_module")
```

### Phase 3: Write RTL
1. Write minimum working RTL in `src/`
2. Use registered outputs for all status signals (dispense, valid, done)
3. Refer to `knowledge/patterns/` for common idioms

### Phase 4: Write Testbench
1. Copy from `templates/tb_comprehensive.py`
2. Follow the **3-edge pattern** for driving pulsed inputs:
   ```
   set signal → RisingEdge#1 → clear → RisingEdge#2 → sample → RisingEdge#3 → return
   ```
3. One `@cocotb.test()` per scenario
4. Use `int(dut.signal.value)` for reading, `==` for comparing

### Phase 5: Iterate
```bash
python agent_tools/fpga_tools.py run outputs/my_project
```
Read result. If FAIL: check `result["raw_log"]`, find assertion line, fix RTL, re-run. Max 10 iterations.

### Phase 6: Review (AFTER project completes)
See §8 — write lessons to `knowledge/`.

---

## 5. Simulator Timing Rules

> Detail in `docs/SIMULATOR_GUIDE.md`. These are the **must-memorize** rules:

| Input write to | Registration delay | Sampling point |
|---------------|-------------------|----------------|
| Combinational output | 0 cycles (write → eval) | Immediately after write |
| Registered output | 1 cycle (write → eval → edge) | After 2nd RisingEdge |

**Standard helper pattern:**
```python
async def drive_pulse(dut, signal, value):
    signal.value = value
    await RisingEdge(dut.clk)   # Edge 1: signal enters model
    # clear signal here if needed
    await RisingEdge(dut.clk)   # Edge 2: registers update
    result = { ... }            # ★ SAMPLE HERE ★
    await RisingEdge(dut.clk)   # Edge 3: settle
    return result
```

---

## 6. Using the Knowledge Base

### Before starting a project
1. Read `knowledge/_index.md` for relevant entries
2. Load entries under `knowledge/simulator/` for simulator quirks
3. Load entries under `knowledge/patterns/` for reusable code patterns

### Knowledge entry format

```markdown
---
title: "Delayed Input Signal Pattern"
category: patterns
severity: must-know
simulator: verilator
created: 2026-06-09
updated: 2026-06-09
sources: [examples/02_vending_machine]
related: [knowledge/patterns/registered_output.md]
---

## Problem
When driving pulsed inputs (coin, button, strobe) from cocotb, the registered
output updates 1 cycle after the input write.

## Correct Pattern
```python
signal.value = 1
await RisingEdge(dut.clk)
signal.value = 0          # clear immediately
await RisingEdge(dut.clk) # registers update NOW
# Sample here
```
```

### After writing new knowledge
- Update `knowledge/_index.md` with the new entry
- Check if related entries can be merged

---

## 7. Python API Reference

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # workspace root

from agent_tools.sim_driver import run_simulation
from agent_tools.fpga_tools import scan_project, find_top_module, print_project_summary, run_project

# Analyze
summary = print_project_summary("outputs/my_project")

# Run
result = run_simulation(
    sources=["outputs/my_project/src/module.sv"],
    hdl_toplevel="module_name",
    test_module="tb.test_module",
    test_dir="outputs/my_project",
    sim="verilator",
)
print(result["pass"], result["tests_pass"], "/", result["tests_total"])
```

---

## 8. After-Action Review (MANDATORY)

After EVERY completed project (all tests pass), the agent MUST:

1. **Identify lessons**: What went wrong? What was surprising?
2. **Generalize**: Express as universal patterns, not project-specific fixes
3. **Check for overlaps**: Search `knowledge/_index.md` for similar entries
4. **Write or merge**:
   - If no existing entry covers this: write a new knowledge file
   - If existing entry overlaps: merge (consolidate) into that file
   - Update `updated:` date
5. **Update index**: Add/update entry in `knowledge/_index.md`
6. **Write project review**: Save to `reports/<project>_review.md`
7. **Curate `outputs/` → `examples/`** (keep `outputs/` a pure scratch area):
   - Assess whether the finished project deserves promotion to `examples/`.
     Criteria (all): all tests pass · demonstrates a **distinct, reusable**
     capability (not a near-duplicate of an existing example) · ideally maps to
     a `knowledge/` entry · clean RTL + testbench.
   - **Recommend candidates to the user first; only copy after they confirm.**
   - On promotion: copy `src/ tb/ project.json` into `examples/NN_name/`
     (exclude `sim_build/` and `__pycache__/`), verify it still passes, then
     delete the `outputs/` working copy.
   - Delete any `outputs/` copy that is byte-identical to an existing example
     (verify with `diff -rq` before deleting).

### Review template

```markdown
# Review: <project_name>
Date: YYYY-MM-DD

## What went well
- ...

## Issues encountered
1. **<Issue summary>**
   - Root cause: ...
   - Resolution: ...
   - Knowledge entry: knowledge/<category>/<file>.md

## Test coverage
- Total tests: N
- Scenarios covered: ...
```

---

## 9. Quality Rules

- **Never guess signal timing.** If unsure, read `docs/SIMULATOR_GUIDE.md`
- **Always register status outputs** (dispense, valid, done) for easier testbench sampling
- **One test = one scenario.** Do not combine unrelated checks in one `@cocotb.test()`
- **Clear inputs immediately.** Pulsed inputs must be deasserted within 1 cycle
- **Distinguish pulse vs level.** Use `drive_pulse` (3-edge) for action triggers (send, wr_en, coin). Use `apply_and_settle` (2-edge) for persistent controls (enable, up_down, mode). Wrong choice = double-action bugs.
- **Use `int(value)`, not `.integer`.** cocotb Logic objects don't have `.integer` attribute
- **Sources are workspace-relative.** All paths in project.json are relative to project root
- **Lint before sim.** `run` auto-runs `verilator --lint-only -Wall -Wno-fatal` first; lint
  ERRORS block simulation (fix them), WARNINGS (width truncation, undriven, unused) only
  inform but should be reviewed since sim can't catch them. Use `--no-lint` only to bypass.

---

## 10. Session Startup Checklist

- [ ] `AGENTS.md` read (this file)
- [ ] **Run read-only git check** (`git branch -a`, `git status -sb`, `git log --oneline -5`)
      and **report current branch + pending changes to the user**. Never push
      automatically — only on explicit request, and always show `git status` first.
- [ ] `STATUS.md` read for current phase & progress
- [ ] `ROADMAP.md` read for the long-term plan (phases A–E, decisions D1–D5)
- [ ] `knowledge/_index.md` scanned
- [ ] `docs/SIMULATOR_GUIDE.md` available for timing questions
- [ ] `reference/` checked for new input files
- [ ] Ready to receive instructions
