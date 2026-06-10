---
title: "cocotb Official Reference Summary"
category: simulator
simulator: cocotb
severity: reference
created: 2026-06-10
updated: 2026-06-10
sources: [https://docs.cocotb.org/en/stable/]
related: [knowledge/simulator/verilator_cocotb.md]
---

# cocotb 官方文档摘要

> Source: https://docs.cocotb.org/en/stable/
> Focus: Testbench writing, triggers, API reference

## Core Concepts

cocotb = **COroutine COsimulation TestBench**.
Testbench is Python. DUT is Verilog/VHDL. Simulator runs the DUT; cocotb drives inputs and reads outputs.

**Key paradigm**: Either the simulator is running OR the Python code is running, never both simultaneously. The `await` keyword transfers control back to the simulator.

## Signal Access

```python
# Read
value = int(dut.signal.value)    # Logic/LogicArray → int

# Write (delayed until next write cycle)
dut.signal.value = 42

# Immediate write
from cocotb.handle import Deposit
dut.signal.value = Deposit(42)   # Immediate deposit
```

**Signal types mapped to Python**:
| HDL Type | Python Type |
|----------|------------|
| `logic`, `logic [N:0]` | `LogicArray` (use `int()` to convert) |
| `integer`, `natural` | `int` |
| `real` | `float` |
| `boolean` | `bool` |
| `string` | `bytes` |

**Reading**: Always use `int(dut.signal.value)`. Do NOT use `.integer` (doesn't exist).

**Writing**: `dut.signal.value = N`. Uses **inertial delay** — applied on next write cycle.

## Triggers

```python
from cocotb.triggers import (
    RisingEdge,    # await RisingEdge(dut.clk)
    FallingEdge,   # await FallingEdge(dut.clk)
    Timer,         # await Timer(10, unit='ns')
    ClockCycles,   # await ClockCycles(dut.clk, 5)
    ReadOnly,      # await ReadOnly() — read after combinatorial settle
    ReadWrite,     # await ReadWrite() — read+write point
    Combine,       # await Combine(trig1, trig2) — any trigger fires
    First,         # await First(trig1, trig2) — first trigger wins
    Join,          # await Join() — all previous triggers fire
)
```

`Timer(10, unit='ns')` does NOT advance the clock — it just waits for simulated time.

## Clock Generation

```python
from cocotb.clock import Clock
c = Clock(dut.clk, 10, unit='ns')  # 10ns period = 100MHz
cocotb.start_soon(c.start())       # Start in background
```

Clock starts low (0), first rising edge at `period/2`.

## Concurrent Execution

```python
# Sequential (blocks)
await coroutine()

# Concurrent (non-blocking)
task = cocotb.start_soon(coroutine())
# ... do other things ...
await task  # wait for it to finish
```

## Test Functions

```python
@cocotb.test()                    # Basic decorator
@cocotb.test(skip=True)           # Skip this test
@cocotb.test(expect_fail=True)    # Expected to fail
@cocotb.test(expect_error=ValueError)  # Expected specific error
async def my_test(dut):
    ...
```

## Logging

```python
cocotb.log.info("message")     # Info level
cocotb.log.debug("debug")      # Debug level
cocotb.log.warning("warn")     # Warning
cocotb.log.error("error")      # Error
```

Do NOT use `print()` — stdout may be buffered and out-of-order.

## Accessing Internal Signals

```python
dut.sub_module.signal.value                         # Hierarchy access
dut["_underscore_signal"]                            # Underscore prefix
dut["\\!escaped_name!\\"]                            # Escaped identifier
dir(dut)                                             # List all signals/ports
cocotb.packages.my_package.param.value               # Verilog packages
```

## Python Runner API (Alternative to Makefile)

```python
from cocotb_tools.runner import get_runner
runner = get_runner("verilator")
runner.build(hdl_toplevel="top", sources=["file.sv"], build_dir="sim_build")
runner.test(hdl_toplevel="top", test_module="tb.test_name",
            test_dir="", results_xml="results.xml", waves=False)
```

Key parameters for `.test()`:
- `test_dir` — directory containing test Python modules
- `test_module` — module name(s) to run
- `results_xml` — path for JUnit output
- `waves` — enable waveform dump
- `log_file` — capture simulation output

## Force/Freeze/Release

```python
dut.signal.value = Force(value)    # Force to value (ignores DUT)
dut.signal.value = Freeze()        # Hold current value
dut.signal.value = Release()       # Release force/freeze
```

Not supported by all simulators. Verilator: limited support.
