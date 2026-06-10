# Review: **debounce**
**Date**: 2026-06-10
**Agent version**: AGENTS.md v1.1 (w/ official docs)

---

## What Went Well
- RTL correct on first attempt: 4 of 5 tests passed on first run
- Only 1 iteration to fix (test timing issue, not RTL bug)
- Knowledge base patterns applied correctly: `reset_and_clear`, `apply_and_settle`, registered outputs
- Parameterized design works for both simulation (small values) and real hardware (override values)

---

## Issues Encountered

### 1. Missed Registered Pulse During Test Sampling
- **Symptom**: `test_stable_press` failed — `button_out` was 0 after the wait loop, despite the DUT having correctly generated a pulse.
- **Root Cause**: The RTL produces a 1-cycle-wide registered pulse. The test waited MAX_COUNT+5 cycles in a for loop, but the pulse occurred at ~cycle 102 and was gone by the time the loop exited and the test sampled at cycle ~107. The test was checking AFTER the loop, not DURING it.
- **Resolution**: Changed to detect the pulse INSIDE the wait loop and break out immediately upon detection. Then verified the pulse width is 1 cycle.
- **Generalized Lesson**: When testing modules that output single-cycle registered pulses, sample during the stimulus loop, not after it. A registered pulse holds for exactly 1 clock cycle — if you're waiting N cycles with a for loop and the pulse occurs at cycle K (where K < N-1), it will be gone by iteration N.
- **Knowledge Entry**: MERGED into `knowledge/patterns/registered_vs_combinational.md`

---

## Test Coverage

- Total test functions: 5
- Pass: 5, Fail: 0
- Iterations: 2 (1 to fix test timing)

| Test | Scenario | Result |
|------|----------|--------|
| test_stable_press | Hold button > debounce time → single-cycle pulse | ✅ |
| test_bounce_rejection | Rapid toggle within debounce window → no false trigger | ✅ |
| test_hold_single_pulse | Very long hold → only ONE pulse (no repeats) | ✅ |
| test_short_press_ignored | Press < debounce time → no output | ✅ |
| test_multiple_presses | 3 sequential stable presses → 3 pulses | ✅ |

---

## Knowledge Base Changes

| Action | File | Summary |
|--------|------|---------|
| MERGED | `knowledge/patterns/registered_vs_combinational.md` | Added test-side guidance: sample pulses during loops, not after |

---

## Agent Self-Assessment

- **(5/5) Efficiency**: 2 iterations total. Knowledge base patterns eliminated GPI timing guesswork. The one failure was test logic, not RTL.
- **(5/5) Correctness**: RTL was correct on first attempt (4/5 tests passed). Fix was minimal.
- **Main time sink**: None significant. The test timing issue was understood and fixed in minutes.
- **Key insight**: The knowledge base investment is paying off. Previous projects took 17-20 iterations; this took 2.
