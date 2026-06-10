---
title: "Accumulating Multiple One-Hot Inputs in always_comb"
category: patterns
severity: medium
simulator: verilator
created: 2026-06-09
updated: 2026-06-09
sources: [examples/02_vending_machine]
---

## Problem

When multiple one-hot input signals can be asserted simultaneously, using
`amount_d = base + value` for each will overwrite previous assignments.
Only the LAST input is counted.

## Wrong (Last-write-wins)

```systemverilog
always_comb begin
    amount_d = amount_q;          // default
    if (coin_05) amount_d = amount_q + 5;   // writes 5
    if (coin_1)  amount_d = amount_q + 10;  // OVERWRITES to 10!
    // coin_05's contribution is LOST
end
```

## Correct (Accumulate into self)

```systemverilog
always_comb begin
    amount_d = amount_q;          // default
    if (coin_05) amount_d = amount_d + 5;   // reads self: 0+5=5
    if (coin_1)  amount_d = amount_d + 10;  // reads self: 5+10=15 ✓
    // Both coins contribute correctly
end
```

## Why

In `always_comb`, blocking assignments execute sequentially. Reading `amount_d`
after a previous write gives the updated value. Starting from `amount_q` as
default, subsequent `amount_d = amount_d + N` accumulate correctly.

## Applies To

- Coin/value accumulators with multiple input channels
- Priority encoders where multiple bits may be set
- Any summing of multiple `if` condition contributions
