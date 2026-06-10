---
title: "Verilator Official Reference Summary"
category: simulator
simulator: verilator
severity: reference
created: 2026-06-10
updated: 2026-06-10
sources: [https://verilator.org/guide/latest/]
related: [knowledge/simulator/verilator_cocotb.md]
---

# Verilator 官方手册摘要

> Source: https://verilator.org/guide/latest/
> Focus: Verilog→C++ compilation, model structure, eval loop

## Core Concepts

Verilator is a **Verilog/SystemVerilog to C++/SystemC compiler**. It does NOT interpret
the code — it compiles to optimized C++ for maximum speed (10-100x faster than interpreted).

### Operation Modes
- `--binary` — compile to C++ then to executable (most common for cocotb)
- `--cc` — compile to C++ only
- `--sc` — compile to SystemC
- `--lint-only` — lint checks, no code gen
- `--json-only` — JSON output for other tools

### Model Structure
The generated model class (`{prefix}`) contains:
- **Top-level I/O ports**: accessible as member references
- **Public sub-modules**: pointers to `/* verilator public */` items
- **Root scope**: `model->rootp` for internal signal access (since v4.210)

## The Evaluation Loop (Key for cocotb integration)

```
1. Set inputs on the model
2. Call model->eval()
   ├── Evaluates combinational logic
   └── Advances sequential state (always_ff @posedge)
3. Read outputs from the model
4. Repeat
```

**Critical**: Combinational logic is NOT computed before sequential blocks.
Set non-clock inputs with a separate `eval()` before changing clocks.

When using `--timing` (for delay support):
- `model->eventsPending()` — any delayed events remaining?
- `model->nextTimeSlot()` — time of next event

## VPI Interface (How cocotb Communicates)

Verilator supports VPI via `--vpi`. This is the interface cocotb uses.
- Signal values written via VPI do NOT immediately propagate — must call `eval()`
- VPI access is ~100x slower than direct C++ reference
- `VerilatedVpi::callValueCbs()` must be called for signal callbacks

## Cocotb-Specific Implications

cocotb uses Verilator's VPI interface. When cocotb writes a signal value:
1. The VPI write is "queued" (deposited)
2. Next `eval()` call applies it
3. This creates the **1-cycle GPI delay** we observe in practice

## Build Output Summary

The Verilation report prints:
```
- Verilator: Built from 354 MB sources in 247 modules,
    into 74 MB in 89 C++ files needing 0.192 MB
- Verilator: Walltime 26.580 s (elab=2.096, cvt=18.268, bld=2.100)
```

- `elab` — time to read+elaborate input files
- `cvt` — time to convert to C++
- `bld` — time to compile with gcc/clang

## Key Options for cocotb Usage

| Option | Purpose |
|--------|---------|
| `--binary` | Generate executable |
| `--trace --trace-structs` | Enable VCD/FST waveform dump |
| `--timing` | Enable intra-assignment delays |
| `--threads N` | Multithreaded simulation |
| `--coverage` | Code coverage instrumentation |
| `--Mdir <dir>` | Output directory |
| `--top-module <name>` | Force top module |
