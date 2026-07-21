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
│   ├── vivado_tools.py     ← Vivado Tcl IP generator
│   ├── vivado_backend/      ← Vivado batch synthesis runner (synth_runner.py)
│   │   ├── synth_runner.py ← Synthesis + timing + report parsing
│   │   ├── xsim_runner.py  ← xsim simulation + auto-TB generator
│   │   ├── modelsim_runner.py ← ModelSim simulation runner
│   │   ├── project_manager.py ← .xpr open/backup/modify/save
│   │   └── xdc_tools.py    ← XDC constraint generator
│   ├── project_gen.py     ← Project skeleton generator
│   ├── reference_reader.py ← Reads files from reference/
│   └── ise_backend/       ← ISE 14.7 VM backend (ise_remote.py + config)
│
├── ip_models/             ← Shared IP stub library (replaces vendor IPs for sim)
│   ├── bram/              ← Block RAM stub (SDP/ROM/SP_RAM, 5/5 contract tests)
│   ├── fifo/              ← FIFO stub (common/indep clk, asymmetric, 5/5)
│   └── multiplier/        ← Multiplier stub (signed/unsigned, 5/5)
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
│   ├── 08_config_demo/     (project.json includes/defines/parameters)
│   ├── 09_mac_unit/        (multi-module hierarchy + dep tree)
│   ├── 10_axil_regs/        (AXI-Lite register file + cocotbext-axi BFM)
│   └── 11_dft8/              (complex DFT + hierarchy + ModelSim verified)
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

# Vivado / ModelSim side
python agent_tools/fpga_tools.py vivado-sim outputs/my_project --simulator modelsim
python agent_tools/fpga_tools.py vivado-synth outputs/my_project
python agent_tools/fpga_tools.py vivado-xdc outputs/my_project
python agent_tools/fpga_tools.py ip-scan reference/beamform

# Full certification (run ONCE, after all simulation passes)
python agent_tools/fpga_tools.py full-run outputs/my_project --clk-freq 100
```

All commands run from the **workspace root** (where this AGENTS.md lives).

---

## 4. Agent Decision Flow (V3)

> **Resource principle**: Use the cheapest tool that gives you the answer.
> Verilator is seconds; ModelSim is ~10s; Vivado synth is 5+ minutes.
> **Never run synthesis during iteration.** It runs ONCE when all sims pass.

### Phase 0: Understand Requirements
1. Read user requirements / reference files
2. Ask for clock frequency upfront (default 100 MHz if no answer)
3. Check `knowledge/_index.md` for relevant patterns
4. **Port count pre-check**: Count top-level ports after design. If >100, propose
   AXI-Lite or addr+data bus wrapper BEFORE writing RTL. This prevents IO overutilization
   failures at the Vivado implementation stage. (See `knowledge/patterns/timing_closure.md` §7)
5. **Knowledge gap escalation**: If the knowledge base does not cover a needed topic,
   use `webfetch` to search for relevant documentation/reference projects (Xilinx docs,
   GitHub, open-source FPGA examples). Write learned knowledge back to `knowledge/`.

### Phase 1: Design + Write RTL + Verilator Iteration (seconds)
```
Agent: generate RTL → fpga_tools.py run → PASS? → fix → repeat
```
- Use `fpga_tools.py run` (not `full-run`) for iteration
- Only proceed to Phase 2 when ALL Verilator tests pass
- Max 10 Verilator iterations before surfacing to user

### Phase 2: ModelSim Compatibility Check
```
Agent: fpga_tools.py vivado-sim → PASS? → fix RTL → back to Phase 1 → repeat
```
- Agent runs this ONLY after Verilator passes
- Fixes: Verilog-2001 compliance (`logic`→`reg`/`wire`, `always_ff`→`always`)
- Generate the .v testbench ALONGSIDE the cocotb testbench in Phase 1
- Max 5 ModelSim iterations before surfacing to user

### Phase 3: Final Certification (runs ONCE)
```bash
# Run by AGENT only after Phases 1+2 pass, with user confirmation.
# --no-sim skips Verilator+ModelSim (already passed in Phase 1+2):
fpga_tools.py full-run outputs/my_project --clk-freq 100 --no-sim
```
- `full-run --no-sim` = lint → Vivado synth → timing → report（跳过已通过的仿真）
- If WNS < 0: auto-runs timing_loop (relax period). If still failing, suggest RTL changes.
- After full-run passes: write `reports/` review, update `knowledge/`, recommend promotion

### Agent Self-Scheduling Rules
| When | What to run | Purpose |
|------|-----------|---------|
| I just changed RTL | `fpga_tools.py run` | Fast Verilator feedback |
| Verilator all passes | `fpga_tools.py vivado-sim` | Check Vivado compatibility |
| Both sim platforms pass | `fpga_tools.py full-run` (ask user first) | Final certification |
| I need resource estimates | `fpga_tools.py vivado-synth` | Without timing |
| User says "just synth" | `fpga_tools.py vivado-synth` | Skip sim steps |

### Session End Routine
After every development turn, the agent MUST:
- Run `git status -sb` and report pending changes to the user
- Provide the exact `git add -A; git commit -m "..."; git push` commands
- Never commit or push automatically — always wait for the user to run them

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

### Before developing an IP stub model
**Mandatory pre-read** (these were learned the hard way):
1. `knowledge/patterns/ip_stub_development.md` — IP 替身开发的 5 大陷阱
2. `knowledge/patterns/robust_test_reset.md` — 跨测试 GPI 污染 + helper 封装
3. `knowledge/patterns/delayed_input_signal.md` — GPI 写延迟 + 采样点
4. `knowledge/simulator/wsl_verilator_ops.md` — Verilator 语法/参数限制

### Before developing Vivado/ISE batch tooling
**Mandatory pre-read**:
1. `knowledge/simulator/vivado_batch_runner.md` — Vivado 批处理：路径/行尾/报告格式
2. `knowledge/simulator/ise_vm_backend.md` — ISE VM 模式参考（同类"生成脚本→调工具"）
3. `knowledge/simulator/wsl_verilator_ops.md` — 跨平台坑（路径/行尾）

### After completing any debugging session
- If a problem took more than 3 iterations to fix, **write a knowledge entry**
  or update an existing one. This is not optional — otherwise every future
  session repeats the same debugging.
- Check: was this problem already in the knowledge base? If yes and I didn't
  read it → the knowledge base works but I failed to use it. If no → write it.

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
4. **Was this lesson already in the knowledge base?** — If yes and I didn't read it
   before starting, the knowledge base works but I failed to use it (record this
   as a process failure). If no, I must write it now.
5. **Write or merge**:
    - If no existing entry covers this: write a new knowledge file
    - If existing entry overlaps: merge (consolidate) into that file
    - Update `updated:` date
6. **Update index**: Add/update entry in `knowledge/_index.md`
7. **Write project review**: Save to `reports/<project>_review.md`
8. **Curate `outputs/` → `examples/`** (keep `outputs/` a pure scratch area):
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
- **Wrap parallel ports behind a bus if >100.** Large parallel-port top modules
  (like DFT with 500+ I/Os) will fail Vivado implementation due to physical pin limits.
  Use AXI-Lite or a simple addr+data bus — keep top-level ports under 100.
  The internal logic stays the same.

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
- [ ] **Read last 3 review files** in `reports/` for recently-learned patterns
      and pitfalls (formats: `reports/*_review.md`; sort by date, take newest 3).
      This prevents repeating known bugs (e.g. `model_dut_format_align.md`).
