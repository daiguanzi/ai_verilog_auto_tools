---
title: "跨 Always 块的 Done/Start 握手时序"
category: patterns
severity: high
simulator: verilog, verilator, modelsim
created: 2026-07-21
updated: 2026-07-21
sources: [outputs/dft8_axi]
related: [knowledge/patterns/delayed_input_signal.md, knowledge/patterns/robust_test_reset.md]
---

## Problem

当 `done` 和 `start` 信号跨越多个 `always` 块时，如果清除逻辑写在**同一
always 块内且在 case 之前**，容易导致 done 在设置后的下一个周期立即被
错误清除。

## 具体场景 (DFT8-AXI)

```
always_ff @(posedge clk) begin
    if (done_q && !start_req)   // ❌ 清除条件错误
        done_q <= 1'b0;         // done 刚设 1 就被清除
    case (state)
        2'd1: if (last) done_q <= 1'b1;
    endcase
end
```

时序：done 设为 1 的**下一个周期**，`!start_req` 为真，done 立即被清 0。
主机轮询永远读不到 done=1。

## Correct Pattern

**done 不应该自动清除**。只在**新一轮 start 到来时**清除：

```verilog
always_ff @(posedge clk) begin
    if (done_q && start_req)    // ✅ 有新 start 时才清除
        done_q <= 1'b0;
    case (state)
        2'd0: if (start_req) state <= 2'd1;
        2'd1: if (last) begin
            state  <= 2'd0;
            done_q <= 1'b1;
        end
    endcase
end
```

这样 done 保持为 1 直到新 start 写入，主机有充分时间读取。

## When to Apply

- 任何有 `done`/`busy`/`valid` 状态标志的 FSM
- AXI 寄存器接口中的状态寄存器
- 多个 always 块共享的控制信号

**通用原则**：状态标志位只应在**事件驱动**下改变（start→done, new_start→clear），
不应在标志位自身上加自动清除逻辑。
