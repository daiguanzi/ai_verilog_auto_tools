---
title: "Dual Counter FSM for Serial Protocols"
category: patterns
severity: high
simulator: verilator
created: 2026-06-10
updated: 2026-06-10
sources: [outputs/uart_tx]
related: [knowledge/patterns/registered_vs_combinational.md]
---

## Problem

When implementing serial protocols (UART, SPI, I2C), you need two levels of counting:
1. A **tick counter** to divide the clock down to the bit/baud rate
2. A **bit counter** to track which bit position you're on

Naively combining these leads to off-by-one errors and timing glitches at state transitions.

## Correct Pattern

Use two separate counters, each managed in `always_comb`, with atomic state transitions.

```systemverilog
localparam int BIT_PERIOD = CLK_FREQ / BAUD_RATE;

always_comb begin
    state_d   = state_q;
    tick_cnt_d = tick_cnt_q;
    bit_cnt_d  = bit_cnt_q;

    case (state_q)
        S_START: begin
            if (tick_cnt_q >= BIT_PERIOD - 1) begin
                tick_cnt_d = 0;              // reset tick counter
                bit_cnt_d  = 0;              // init bit counter
                state_d    = S_DATA;         // transition
            end else begin
                tick_cnt_d = tick_cnt_q + 1; // keep counting
            end
        end

        S_DATA: begin
            tx_d = data_q[bit_cnt_q];        // output current bit
            if (tick_cnt_q >= BIT_PERIOD - 1) begin
                tick_cnt_d = 0;
                if (bit_cnt_q >= 7) begin    // last bit?
                    bit_cnt_d = 0;
                    state_d   = S_STOP;
                end else begin
                    bit_cnt_d = bit_cnt_q + 1;
                end
            end else begin
                tick_cnt_d = tick_cnt_q + 1;
            end
        end
    endcase
end
```

## Key Rules

1. **Reset both counters when transitioning out of a state**, not when entering
2. **Check tick counter first**, then bit counter — tick counter drives the timing
3. **Use `>= BIT_PERIOD-1`** (not `==`) for robustness against glitches
4. **Register ALL counters** via `always_ff` — combinational counters invite synthesis issues

## Applies To

- UART TX/RX (tick = baud divider, bit = 0..7 or 0..9)
- SPI Master (tick = SCK divider, bit = 0..N-1)
- I2C controller (tick = SCL divider, bit = address/data phase)
- Any clock-divided bit-serial protocol
