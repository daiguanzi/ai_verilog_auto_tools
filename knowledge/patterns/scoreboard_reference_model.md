---
title: "Reference Model + Scoreboard for Self-Checking Tests"
category: patterns
severity: high
simulator: verilator
created: 2026-06-22
updated: 2026-06-22
sources: [templates/tb_comprehensive.py, examples/01_adder]
related: [knowledge/patterns/delayed_input_signal.md]
---

## Problem
Hand-writing one `assert` per case does not scale and is error-prone for
non-trivial DUTs (datapaths, FIFOs, protocol blocks). It also tangles
"expected behavior" together with "test plumbing".

## Pattern
Separate the two concerns:

1. **Reference model** — a pure-Python golden function written from the SPEC
   (not by reading the RTL). It is the source of truth.
   ```python
   def reference_model(inputs: dict) -> dict:
       return {"sum": (inputs["a"] + inputs["b"]) & 0x1FF}
   ```

2. **Scoreboard** — compares DUT outputs against the model and tallies results.
   - Direct style (known timing):
     ```python
     sb.check(f"a={a},b={b}", reference_model({"a": a, "b": b})["sum"], dut.sum.value)
     ```
   - Queue style (streaming / pipelined): decouple producer & consumer
     ```python
     sb.expect(reference_model(inp)["sum"])   # push expected
     sb.observe(dut.out.value)                # pop & compare
     ```
   - End every test with `sb.report()` (asserts overall pass + flags
     unmatched expecteds).

## Notes
- Skeleton lives in `templates/tb_comprehensive.py` — copy it for new TBs.
- The reference model MUST be written independently of the RTL, otherwise it
  just re-encodes the same bug.
- Still obey GPI timing (see `delayed_input_signal.md`): sample registered
  outputs after the right number of edges before pushing to the scoreboard.
