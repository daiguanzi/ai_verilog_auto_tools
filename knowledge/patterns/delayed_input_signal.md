---
title: "Driving Pulsed Inputs from cocotb"
category: patterns
severity: must-know
simulator: verilator
created: 2026-06-09
updated: 2026-06-09
sources: [examples/02_vending_machine]
related: [knowledge/simulator/verilator_cocotb.md]
---

## Problem

When driving pulsed (one-shot) input signals—coins, buttons, strobes, request signals—from a cocotb testbench, the signal must be asserted, seen by the EVAL, registered on an EDGE, then deasserted to prevent double-counting. Incorrect timing results in either the signal being missed entirely OR counted multiple times.

## Root Cause

The Verilator+cocotb cycle model creates a 1-cycle pipeline between testbench write and register update. If the pulsed signal stays high across 2 edges, the FSM processes it twice.

## Correct 3-Edge Pattern

```python
async def drive_pulse(dut, signal, value):
    """Drive a 1-cycle input pulse. Returns sampled outputs."""
    signal.value = value              # Step 1: Assert
    await RisingEdge(dut.clk)         # Step 2: Signal enters EVAL pipeline
    signal.value = 0                  # Step 3: CLEAR IMMEDIATELY
    await RisingEdge(dut.clk)         # Step 4: Registers update
    result = {
        "amount": int(dut.amount.value),
        "done":   int(dut.done.value),
    }                                 # Step 5: SAMPLE HERE
    await RisingEdge(dut.clk)         # Step 6: Settle
    return result
```

## Concrete Example (Coin Insert)

```python
async def insert_coin(dut, coin_val):
    dut.coin.value = coin_val
    await RisingEdge(dut.clk)
    dut.coin.value = 0               # Clear before next edge!
    await RisingEdge(dut.clk)
    total = int(dut.amount.value)    # Register now reflects coin
    await RisingEdge(dut.clk)
    return total
```

## Wrong Patterns (what went wrong in development)

### Pattern A: Clear too late → double count
```python
dut.coin.value = 1
await RisingEdge(dut.clk)
await RisingEdge(dut.clk)
dut.coin.value = 0      # Too late! Counted twice.
```

### Pattern B: Sample too early → miss result
```python
dut.coin.value = 1
await RisingEdge(dut.clk)
dut.coin.value = 0
amount = int(dut.amount.value)  # Too early! Register not updated yet.
```

## When to Apply

Any testbench scenario where:
- An input is a 1-cycle pulse (not held continuously)
- The DUT responds after exactly 1 cycle of latency
- Multiple sequential pulses on the same signal

Examples: coin acceptor, button debouncer output, request/acknowledge handshake, memory read/write strobes.
