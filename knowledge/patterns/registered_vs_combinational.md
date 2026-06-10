---
title: "Choose Registered Over Combinational Outputs"
category: patterns
severity: high
simulator: verilator
created: 2026-06-09
updated: 2026-06-10
sources: [examples/02_vending_machine, outputs/debounce]
related: [knowledge/patterns/delayed_input_signal.md]
---

## Problem

Combinational output signals (driven by `assign` or `always_comb`) are difficult to sample in cocotb. They may pulse for sub-nanosecond durations and disappear before the testbench can read them. This leads to "missed pulses" and false test failures.

## Rule

**Always register status/pulse outputs.** Use `always_ff` to hold the value for exactly 1 full clock cycle.

## Before (Combinational — avoid)

```systemverilog
always_comb begin
    dispense = 1'b0;
    if (amount_d >= 15) begin
        dispense = 1'b1;          // combinational pulse
        amount_d = 0;
    end
end
assign dispense_o = dispense;     // hard to sample
```

## After (Registered — use this)

```systemverilog
always_comb begin
    dispense_d = 1'b0;
    if (amount_d >= 15) begin
        dispense_d = 1'b1;
        amount_d = 0;
    end
end

always_ff @(posedge clk) begin
    dispense_q <= dispense_d;     // registered: holds for 1 full cycle
end

assign dispense_o = dispense_q;   // testbench samples here
```

## Why This Works

- Registered output holds steady for the entire clock cycle after the EDGE
- Testbench reads it in the CALLBACK after the EDGE → always correct
- Pulse width is deterministic (exactly 1 cycle)
- No need to sample "mid-cycle" or between edges

## When This Applies

Any output that:
- Indicates completion of an operation (done, valid, ready)
- Is a pulse/acknowledge (grant, ack, interrupt)
- Must be read by external logic or testbench

✅ DO register: dispense, change_valid, read_ready, write_done, irq
❌ DON'T register: continuous data buses (unless pipelined)

## Test-Side: Sampling Registered Pulses

A registered pulse output holds for **exactly 1 clock cycle**. In a testbench, if you're waiting for a pulse to appear during a loop, you must sample **inside the loop** and break on detection. Sampling after the loop will miss the pulse.

### Wrong (sample after loop)

```python
await apply_and_settle(dut, dut.button_in, 1)
for _ in range(MAX + 20):
    await RisingEdge(dut.clk)
# WRONG: pulse already occurred and is gone
assert int(dut.button_out.value) == 1
```

### Correct (sample during loop)

```python
await apply_and_settle(dut, dut.button_in, 1)
pulse_seen = False
for _ in range(MAX + 20):
    await RisingEdge(dut.clk)
    if int(dut.button_out.value):
        pulse_seen = True
        break  # pulse found, verify width next
assert pulse_seen, "should pulse"
await tick(dut, 2)
assert int(dut.button_out.value) == 0, "pulse should be 1 cycle wide"
```

### Why This Matters

Registered pulses are intentionally narrow (1 cycle). This is correct RTL behavior. The test must match — checking at the exact cycle the pulse fires, not afterwards.
