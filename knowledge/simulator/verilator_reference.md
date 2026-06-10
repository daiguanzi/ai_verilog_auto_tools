---
title: "Verilator 官方参考 — 编译模型与仿真执行模型"
category: simulator
simulator: verilator
severity: reference
created: 2026-06-10
updated: 2026-06-10
sources:
  - https://verilator.org/guide/latest/overview.html
  - https://verilator.org/guide/latest/verilating.html
  - https://verilator.org/guide/latest/connecting.html
  - https://verilator.org/guide/latest/simulating.html
related: [knowledge/simulator/verilator_cocotb.md, knowledge/simulator/cocotb_reference.md]
---

## Verilator 是什么

Verilator 是一个 **Verilog/SystemVerilog → C++/SystemC 编译器**，不是传统的事件驱动仿真器。它将 HDL 编译成 C++ 源码，再由 C++ 编译器编译为可执行文件。

```
Verilog(.sv) → verilator → C++(.cpp/.h) → g++/clang++ → executable → simulation
```

## 核心执行模型

### eval() 循环

Verilated 模型由用户代码（wrapper）通过 `eval()` 显式驱动。没有内置时钟概念：

```cpp
while (!contextp->gotFinish()) {
    top->eval();  // 执行一个评估周期
}
```

**关键**：Verilator 先计算时序逻辑（`always_ff`），再计算组合逻辑。这是出于性能考虑。

> "combinatorial logic is not computed before sequential always blocks are computed (for speed reasons). Therefore it is best to set any non-clock inputs up with a separate eval() call before changing clocks."

### 与 cocotb 的关系

cocotb 通过 VPI（Verilog Procedural Interface）连接 Verilator。官方文档明确指出：

> "signal values that are changed by the VPI will not immediately propagate their values, instead the top level header file's eval() method must be called."

这就是我们观测到的 **GPI 写入有 1 个 eval() 延迟** 的官方解释：VPI 写入只在下次 `eval()` 时生效。

## Verilating 流程

```
1. verilator 读取 .sv 文件，确定 top module
2. 将设计翻译为 C++ 代码 (输出到 --Mdir 指定目录)
3. 若使用 --binary: 同时生成 main() wrapper + Makefile，自动编译
4. 若使用 --build: 自动调用 make 编译
```

cocotb 的 runner 封装了这个过程：`runner.build()` 调用 verilator + make，`runner.test()` 运行仿真。

## 性能选项

| 选项 | 作用 |
|------|------|
| `-O3` | 最高优化，编译时间最长 |
| `--x-assign fast` | 加速 X 赋值，略增复位 bug 风险 |
| `--no-assert` | 跳过断言检查，适合已知正确的模型 |
| `--threads N` | 多线程仿真 |
| `--trace` | 启用波形追踪 (FST) |

## 与已有知识库的一致性验证

我们的 `knowledge/simulator/verilator_cocotb.md` 中的 **Eval→Edge→Callback 模型** 与官方文档一致，但官方使用的术语略有不同：

| 我们使用 | 官方使用 |
|----------|---------|
| EVAL | eval() / combinational evaluation |
| EDGE | sequential logic evaluation (同一个 eval 调用内先时序后组合) |
| CALLBACK | VPI callback / testbench read phase |

**重要修正**：官方文档说明在一个 `eval()` 调用内，时序逻辑先于组合逻辑计算。我们的 3 阶段模型是正确的，但 "EDGE" 和 "EVAL" 在同一个 `eval()` 调用内发生，顺序是 时序→组合，而非 组合→时序。

## 关键限制

- 不支持 `#delay`（Verilator 不是事件驱动仿真器），除非使用 `--timing`
- VPI 访问比直接 C++ 指针访问慢数百倍
- 多线程模型有线程亲和性考量
