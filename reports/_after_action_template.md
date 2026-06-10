# After-Action Review Template

> Copy this file to `reports/<project_name>_review.md`, fill in sections, then update `knowledge/`.

---

# Review: **<project_name>**
**Date**: YYYY-MM-DD
**Agent version**: (from AGENTS.md)

---

## What Went Well
- (techniques that worked, patterns that were correct first try)
- ...

---

## Issues Encountered

### 1. **<Issue Title>**
- **Symptom**: (what the agent observed — test failures, wrong values, timing mismatches)
- **Root Cause**: (why it happened — missing knowledge, simulator quirk, RTL bug)
- **Resolution**: (how it was fixed)
- **Generalized Lesson**: (universal rule, NOT project-specific)
- **New Knowledge Entry**: `<knowledge/patterns/xxx.md>` or MERGED into existing `<...>` (why merged, what was added)

### 2. **<Issue Title>**
- (repeat)

---

## Test Coverage

- Total test functions: N
- Pass: N, Fail: 0
- Scenarios covered:
  - Normal operation
  - Boundary conditions
  - Error handling
  - Reset behavior
  - Sequential/burst
  - Concurrent/multi-input

---

## Knowledge Base Changes

| Action | File | Summary |
|--------|------|---------|
| NEW | `knowledge/patterns/xxx.md` | ... |
| MERGED | `knowledge/simulator/yyy.md` | Added note about ... |
| NONE | — | No new knowledge needed |

---

## Agent Self-Assessment

- **(1-5) Efficiency**: how many iterations did this take? could it have been fewer?
- **(1-5) Correctness**: were all fixes substantive, or were there trial-and-error cycles?
- **Main time sink**: (what consumed the most iterations — unknown API, timing model, RTL logic)
- **For next time**: (what this agent should do differently on the next project)
