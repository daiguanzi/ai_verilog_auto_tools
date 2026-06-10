# Review: **fifo**
**Date**: 2026-06-10
**Agent version**: AGENTS.md v1.1

---

## What Went Well
- RTL logic was correct on first attempt (count-based full/empty, pointer wraparound)
- 4 of 5 tests passed on first run
- Registered outputs (data_out, full, empty) ensured clean sampling

---

## Issues Encountered

### 1. apply_and_settle Causes Double-Action on wr_en/rd_en
- **Symptom**: test_full_empty_flags failed at index 8 — data_out was one behind expected. The FIFO was reading the wrong entry because wr_en/rd_en were asserted for 2 edges via `apply_and_settle`, causing double-write/double-read.
- **Root Cause**: `apply_and_settle` keeps the signal high for 2 RisingEdges. For wr_en and rd_en (which trigger one operation per edge), this means 2 operations instead of 1. This is the same "level control side effect" documented in `verilator_cocotb.md`.
- **Resolution**: Replaced `apply_and_settle` with single-cycle pulse pattern (3-edge: set → edge → clear → edge → sample → edge) via `do_write()`/`do_read()` helpers.
- **Generalized Lesson**: `apply_and_settle` is for **persistent** level controls (enable, up_down). For signals that cause an **action per edge** (wr_en, rd_en, send), use the 3-edge pulse pattern.
- **Knowledge Entry**: This reinforces existing `delayed_input_signal.md` and `verilator_cocotb.md` — no new entry needed.

---

## Test Coverage

- Total test functions: 5
- Pass: 5, Fail: 0
- Iterations: 2

| Test | Scenario | Result |
|------|----------|--------|
| test_single_write_read | Write 1, read 1, verify data | ✅ |
| test_full_empty_flags | Fill to full, read all, verify empty | ✅ |
| test_wraparound | 24 write/read cycles (wrap pointers) | ✅ |
| test_overflow_prevention | Write to full FIFO, verify not corrupted | ✅ |
| test_underflow_prevention | Read from empty FIFO, verify safe | ✅ |

---

## Knowledge Base Changes

No new entry. This failure reinforced the existing distinction between:
- **Level controls** (enable, up_down) → `apply_and_settle` (2 edges, persistent)
- **Action triggers** (wr_en, rd_en, send, coin) → 3-edge pulse (set → edge → clear)
