---
title: "Verilator + cocotb Signal Timing Model"
category: simulator
simulator: verilator, cocotb
severity: must-know
created: 2026-06-09
updated: 2026-06-10
sources:
  - examples/02_vending_machine
  - outputs/counter
  - https://verilator.org/guide/latest/connecting.html
  - https://docs.cocotb.org/en/stable/writing_testbenches.html
related:
  - knowledge/patterns/delayed_input_signal.md
  - knowledge/patterns/registered_vs_combinational.md
  - knowledge/simulator/verilator_reference.md
  - knowledge/simulator/cocotb_reference.md
---

## Core Cycle Model

Each clock cycle triggers one `eval()` call, which has 2 internal phases, followed by the cocotb callback:

```
Phase 1: eval() begins
  ├── 1a. Sequential logic: always_ff @(posedge clk) evaluates
  │        _q <= _d  (registers update with values computed last cycle)
  └── 1b. Combinational logic: always_comb evaluates
           _d = f(_q, inputs)  (next-state computed from new register values)
Phase 2: CALLBACK → cocotb testbench runs (read outputs, write inputs)
```

> **Verified by Verilator official docs**: "combinatorial logic is not computed before sequential always blocks are computed (for speed reasons)." — Verilator Connecting Guide

GPIO/VPI writes from the callback are applied during the **next** `eval()` call.

## Signal Write Timing

| Action | When Visible |
|--------|-------------|
| Set input signal in CALLBACK | Next `eval()` (Phase 1a sequential + 1b combinational) |
| Registered output (_q) changes | After next `eval()` completes (Phase 1a) |
| Combinational output (_d) changes | After next `eval()` completes (Phase 1b) |

**Practical consequence** (unchanged): Writing `dut.signal.value = 1` in the callback means registered outputs reflect this change after **1 RisingEdge + eval() cycle**, and fully settle after **2 RisingEdges**.

## Common Pitfalls

### 1. Reading registered outputs too early
```python
dut.coin.value = 1
amount = int(dut.amount.value)  # WRONG: still old value
```
→ The register hasn't updated yet. Wait 1 more edge.

### 2. Leaving pulsed inputs asserted for multiple cycles
```python
dut.coin.value = 1
await RisingEdge(dut.clk)  # +5
await RisingEdge(dut.clk)  # +5 again! Total = 10, not 5
```
→ Clear ASAP after first edge.

### 3. Sampling combinational pulses at the wrong time
```python
dut.coin.value = 1
# dispense_d = 1 combinatorially RIGHT NOW
await RisingEdge(dut.clk)
# state_q = S_DISPENSE → dispense_d defaulted to 0
disp = int(dut.dispense.value)  # WRONG: 0, missed the pulse
```
→ **Fix**: Use registered outputs instead of combinational.

## Verilator-Specific Notes

- Verilator evaluates `always_comb` as a function called during EVAL
- Signal writes via VPI trigger implicit eval in cocotb 2.0+
- Default time precision is 1ps, cocotb Clock handles scaling
- `--trace --trace-structs` enables FST waveform export for GTKWave

## cocotb-Specific Notes

> **Official confirmation**: cocotb docs state "writes are not applied immediately, but delayed until the next write cycle." This confirms the 1-cycle GPI latency we observe. — [Writing Testbenches](https://docs.cocotb.org/en/stable/writing_testbenches.html)

### Level Controls vs Pulsed Inputs

There are TWO distinct input patterns with different GPI behaviors:

**Pulsed inputs** (coin, button, strobe): Assert for 1 cycle, clear immediately.
→ Use the 3-edge pattern from `knowledge/patterns/delayed_input_signal.md`.
→ GPI delay causes 1 cycle of latency before register updates.
→ Example: `insert_coin(dut, coin_05=1)`

**Level controls** (enable, up_down, mode): Assert for many cycles.
→ Use `apply_and_settle(dut, signal, value)` — 2 edges.
→ The SECOND edge not only settles the GPI write but also causes ONE
  "side effect" (e.g., enable=1 → counter increments by 1 on the second edge).
→ Test assertions must account for this: after `apply_and_settle(enable, 1)`,
  the controlled logic has already responded once.

**Key difference**: Pulsed inputs use `clear_inputs()` after 1 edge to prevent double-counting. Level controls should NOT be cleared immediately — they stay asserted.

### Async Reset + GPI = Unreliable

`dut.rst_n = 0` followed by `dut.rst_n = 1` with only a few edges in between
may cause the reset to be overwritten in the GPI queue.
→ **Do not rely on reset for cross-test state clearing.**
→ Use explicit `load` to set known values instead.
→ If reset is necessary, hold rst_n=0 for 8+ edges, then rst_n=1 for 8+ edges.
→ See `knowledge/patterns/robust_test_reset.md`.

### Cross-Test State Contamination

cocotb runs all `@cocotb.test()` functions in a single Verilator simulation.
GPI writes from test N can bleed into test N+1.
→ Always clear ALL control inputs at test start (use `reset_and_clear` pattern).
→ Add 2+ idle RisingEdges after clearing before checking state.

- `int(dut.signal.value)` to read, NOT `.integer` (AttributeError)
- `dut.signal.value == N` for comparison (works directly)
- `@cocotb.test()` decorator marks test functions
- `await RisingEdge(dut.clk)` is the primary trigger
- `Clock(dut.clk, 10, "ns")` generates continuous clock
