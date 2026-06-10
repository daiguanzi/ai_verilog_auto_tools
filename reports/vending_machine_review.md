# Review: **vending_machine**
**Date**: 2026-06-09
**Agent version**: AGENTS.md v1.0

---

## What Went Well
- FSM design was correct from the start (3 states, clear transitions)
- Test coverage was comprehensive (9 scenarios covering exact payment, overpayment, refund, multi-drink, simultaneous coins, pulse width, cancel-when-zero)
- Final RTL passed all 9 tests on first full run after the registered-output fix

---

## Issues Encountered

### 1. Combinational Outputs Unreliable for Testbench Sampling
- **Symptom**: Testbench failed to detect `dispense` and `change_valid` pulses. The signals were asserted as combinational pulses that disappeared before the testbench callback could read them.
- **Root Cause**: `dispense` and `change_valid` were initially driven combinatorially from `always_comb`. They were only valid for a brief moment between EVAL and the next EDGE, invisible to the callback.
- **Resolution**: Converted both signals to registered outputs using `always_ff`. Now they hold for exactly 1 full clock cycle, easily sampled in the testbench callback.
- **Generalized Lesson**: **Never** use combinational outputs for pulse/status signals. Always register them.
- **New Knowledge Entry**: `knowledge/patterns/registered_vs_combinational.md`

### 2. Coin Double-Counting Due to Late Clear
- **Symptom**: After inserting a 0.5-yuan coin, the amount registered as 10 (1.0 yuan) instead of 5 (0.5 yuan). Sequential coins accumulated at 2x rate.
- **Root Cause**: The `insert_coin` helper left the coin signal asserted across 2 clock edges. The FSM's `always_comb` added the coin value on each edge EVAL.
- **Resolution**: Clear the coin signal immediately after the first `RisingEdge` (3-edge pattern: set → edge → clear → edge → sample → edge).
- **Generalized Lesson**: All pulsed inputs in Verilator+cocotb require a strict 3-edge drive pattern to avoid double-counting.
- **New Knowledge Entry**: `knowledge/patterns/delayed_input_signal.md`

### 3. Simultaneous Coin Overwrite in always_comb
- **Symptom**: When both `coin_05` and `coin_1` were asserted simultaneously, only the last coin's value was counted (10 instead of 15).
- **Root Cause**: Blocking assignment `amount_d = amount_q + N` was used for each coin channel, causing the first channel's contribution to be overwritten by the second.
- **Resolution**: Changed to `amount_d = amount_d + N` (accumulating into self), which correctly sums all simultaneously asserted coin channels.
- **Generalized Lesson**: When multiple `if` branches in `always_comb` contribute to the same variable, use `var = var + delta` rather than `var = base + delta` for each.
- **New Knowledge Entry**: `knowledge/patterns/blocking_assign_accumulate.md`

### 4. GPI Write Latency Confusion
- **Symptom**: Testbench read `dut.amount.value` immediately after setting a coin signal, expecting it to reflect the new total. It showed the old value.
- **Root Cause**: The agent initially misunderstood the Verilator+cocotb EVAL→EDGE→CALLBACK ordering. Input writes happen in the CALLBACK; EVAL runs in the next cycle; registers update on the following EDGE.
- **Resolution**: Documented the exact cycle model in SIMULATOR_GUIDE.md. The testbench now waits 2 RisingEdges before sampling registered outputs.
- **Generalized Lesson**: Understand the simulator's event model before writing a testbench. Verilator's cycle-based model differs from event-driven simulators.
- **New Knowledge Entry**: `knowledge/simulator/verilator_cocotb.md`

### 5. cocotb API: `.integer` Doesn't Exist
- **Symptom**: `AttributeError: 'Logic' object has no attribute 'integer'` when reading signal values.
- **Root Cause**: cocotb 2.0.1 uses `int(value)` or `value == N` for numeric access. The `.integer` attribute does not exist on `Logic` objects.
- **Resolution**: Changed all signal reads to `int(dut.signal.value)` and comparisons to `dut.signal.value == N`.
- **Generalized Lesson**: Read cocotb's API carefully. Use `int()` and direct `==` comparisons.
- **New Knowledge Entry**: MERGED into `knowledge/simulator/verilator_cocotb.md` under "cocotb-Specific Notes"

---

## Test Coverage

- Total test functions: 9
- Pass: 9, Fail: 0
- Scenarios covered:
  - Normal operation: exact payment, overpayment (2.0 coin, mixed 1.0+1.0)
  - Boundary: amount=0 cancel, cancel after partial payment
  - Error handling: cancel when amount=0 (no-op)
  - Reset behavior: amount resets correctly after each transaction
  - Sequential: two consecutive drinks
  - Concurrent: simultaneous 0.5+1.0 coins
  - Temporal: dispense pulse width verification (exactly 1 cycle)

---

## Knowledge Base Changes

| Action | File | Summary |
|--------|------|---------|
| NEW | `knowledge/simulator/verilator_cocotb.md` | Full EVAL→EDGE→CALLBACK model, signal write timing, common pitfalls |
| NEW | `knowledge/patterns/delayed_input_signal.md` | 3-edge pattern for driving pulsed inputs |
| NEW | `knowledge/patterns/registered_vs_combinational.md` | Always register status/pulse outputs |
| NEW | `knowledge/patterns/blocking_assign_accumulate.md` | Use `self += delta` for multi-input accumulation |
| — | `knowledge/_index.md` | Updated with all 4 entries |

---

## Agent Self-Assessment

- **(3/5) Efficiency**: ~20 iterations. The first 15 were spent debugging the exact Verilator timing model before the root cause was understood.
- **(4/5) Correctness**: After understanding the timing model, all subsequent fixes were correct on first attempt.
- **Main time sink**: Understanding Verilator+cocotb's GPI signal write latency (Issue 4). Without pre-existing documentation, this required extensive trial and error.
- **For next time**: Read `knowledge/simulator/verilator_cocotb.md` before writing any testbench. Use the 3-edge pattern template. Prefer registered outputs.
