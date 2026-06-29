---
title: "Randomized Testing with Reference Model + Scoreboard"
category: patterns
severity: high
simulator: verilator
created: 2026-06-29
updated: 2026-06-29
sources: [templates/tb_comprehensive.py, outputs/b3_rand_check]
related: [knowledge/patterns/scoreboard_reference_model.md]
---

## Problem
Hand-picking 5-10 test vectors only exercises the cases you thought of.
Silent bugs (e.g. overflow at specific values, timing edge conditions) almost
never show up in directed tests.

## Pattern
Combine `random_test_sequence()` + `reference_model()` + `Scoreboard`:

1. **`random_test_sequence(n, **ranges)`** generates N random vectors within
   per-signal (min, max) bounds.
2. Feed each vector through the **reference model** (pure-Python golden spec)
   to get the expected output.
3. **`Scoreboard`** compares DUT output vs expected and tallies pass/fail.
4. Use a **fixed seed** (`random.seed(42)`) for reproducibility across runs.

```python
random.seed(42)
sb = Scoreboard("rand_500")
for vec in random_test_sequence(500, a=(0, 255), b=(0, 255)):
    dut.a.value = vec["a"]
    dut.b.value = vec["b"]
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    sb.check(f"a={vec['a']},b={vec['b']}", reference_model(vec)["sum"], dut.sum.value)
sb.report()
```

## Why this works
- The reference model is the independent oracle — the DUT must match it.
- Randomized inputs cover value combinations you would never think to write.
- 500 random vectors cost seconds in Verilator; a directed test of 5 vectors
  takes the same wall-clock time but covers 100x less.
- Fixed seed means you can re-run and get exactly the same failures.

## Notes
- Obey GPI timing: sample after the correct number of edges.
- For stateful DUTs, feed the reference model the whole history (or maintain
  its own internal state matching the DUT's FSM).
- This pattern replaces (not adds to) `test_normal_operation` — a single
  randomized test can cover nomial + boundary + overflow in one go.
