---
title: "Robust Reset and Cross-Test State Management"
category: patterns
severity: high
simulator: verilator, cocotb
created: 2026-06-09
updated: 2026-06-09
sources: [outputs/counter]
related: [knowledge/simulator/verilator_cocotb.md]
---

## Problem

In cocotb + Verilator, relying on `dut.rst_n = 0` to clear state between tests is unreliable:
1. GPI queue may overwrite `rst_n=0` with later `rst_n=1` writes
2. Cross-test GPI contamination leaves old control signals active
3. Registered outputs may not reset even after 10+ edges of rst_n=0

## Root Cause

Verilator's cycle-based model + cocotb's GPI interface creates timing fragility
for asynchronous reset signals. Shallow GPI queue (1 entry per signal) can cause
writes to be lost. Cross-test simulation runs compound the issue.

## Correct Pattern: `reset_and_clear`

```python
async def reset_dut(dut):
    dut.rst_n.value = 0
    for _ in range(5):           # Hold reset for 5+ edges
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):           # Release and wait 5+ edges
        await RisingEdge(dut.clk)

async def reset_and_clear(dut):
    await reset_dut(dut)
    # Explicitly settle ALL control inputs to known values
    await apply_and_settle(dut, dut.enable, 0)
    await apply_and_settle(dut, dut.up_down, 0)
    await apply_and_settle(dut, dut.load, 0)
    await apply_and_settle(dut, dut.data_in, 0)
    # Extra idle cycles
    await tick(dut, 2)
```

## Even Better: Load Known State Instead of Reset

```python
# Instead of relying on reset giving count=0:
dut.data_in.value = 5
await apply_and_settle(dut, dut.load, 1)
dut.load.value = 0
await tick(dut)
assert int(dut.count.value) == 5   # Reliable!
```

## When to Apply

- Always call `reset_and_clear` at the START of every test function
- Use explicit `load` to set state, NOT `assert count == 0` after reset
- If reset behavior IS the test target (must verify reset clears state):
  - Load a known value first
  - Assert it's loaded
  - Then apply reset
  - Use 8+ edges in each phase
  - Use loose assertions if needed
