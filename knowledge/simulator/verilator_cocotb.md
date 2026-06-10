---
title: "Verilator + cocotb Signal Timing Model"
category: simulator
simulator: verilator, cocotb
severity: must-know
created: 2026-06-09
updated: 2026-06-09
sources: [examples/02_vending_machine]
related: [knowledge/patterns/delayed_input_signal.md, knowledge/patterns/registered_vs_combinational.md]
---

## Core Cycle Model

Each clock cycle has 3 phases, **strictly ordered**:

```
Phase 1: EVAL          → Combinational logic computes _d signals
Phase 2: EDGE           → Sequential logic: _q <= _d (registers update)
Phase 3: CALLBACK       → cocotb testbench runs (read outputs, write inputs)
```

GPIO writes from the callback are seen by EVAL in the **next** cycle.

## Signal Write Timing

| Action | When Visible |
|--------|-------------|
| Set input signal in CALLBACK | EVAL of NEXT cycle |
| Combinational output changes | Same CALLBACK (eval triggered immediately by write) |
| Registered output updates | EDGE of cycle AFTER the EVAL that processes the write |

**Practical consequence**: Writing `dut.signal.value = 1` in the callback means the registered outputs reflect this change **1 edge later**, and fully settle **2 edges later**.

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

- `int(dut.signal.value)` to read, NOT `.integer` (AttributeError)
- `dut.signal.value == N` for comparison (works directly)
- `@cocotb.test()` decorator marks test functions
- `await RisingEdge(dut.clk)` is the primary trigger
- `Clock(dut.clk, 10, "ns")` generates continuous clock
