---
title: "cocotb 官方参考 — API、触发器和 Runner 详解"
category: simulator
simulator: cocotb
severity: reference
created: 2026-06-10
updated: 2026-06-10
sources:
  - https://docs.cocotb.org/en/stable/quickstart.html
  - https://docs.cocotb.org/en/stable/triggers.html
  - https://docs.cocotb.org/en/stable/coroutines.html
  - https://docs.cocotb.org/en/stable/runner.html
  - https://docs.cocotb.org/en/stable/writing_testbenches.html
  - https://docs.cocotb.org/en/stable/library_reference.html
related: [knowledge/simulator/verilator_cocotb.md, knowledge/simulator/verilator_reference.md]
---

## cocotb 是什么

cocotb 是一个 Python 测试框架，让用户用 Python 写 HDL 的 testbench。DUT 直接作为仿真的 toplevel，无需 HDL wrapper。

## 信号读写

### 写入信号

```python
dut.signal.value = 1       # 赋值（推荐）
dut.signal.value = 12      # 多 bit 赋整数值
```

**官方明确说明写入有延迟**：
> "writes are not applied immediately, but delayed until the next write cycle."

这解释了我们观测到的 1 个时钟沿延迟。

强制立即写入：
```python
from cocotb.handle import Immediate
dut.signal.value = Immediate(1)  # 不推荐常规使用
```

### 读取信号

```python
val = int(dut.signal.value)       # LogicArray → int
val = dut.signal.value.integer    # ★ 不存在！会报 AttributeError ★
```

官方写的是 `.value` 返回 `LogicArray`，用 `int()` 转换。**没有 `.integer` 属性。**

### 符号与无符号值

Python `int` 可赋给任何位宽信号，范围检查：`-2^(Nbits-1) <= value <= 2^Nbits - 1`。

## 触发器 (Triggers)

这是 cocotb 的核心机制。用 `await` 等待触发器，协程暂停直到触发事件发生。

| 触发器 | 说明 |
|--------|------|
| `RisingEdge(sig)` | 等待信号上升沿 |
| `FallingEdge(sig)` | 等待信号下降沿 |
| `Clock(sig, period, unit)` | 连续时钟生成器 |
| `Timer(time, unit)` | 等待指定时间 |
| `First(t1, t2, ...)` | 任一触发器满足即返回 |
| `Combine(t1, t2, ...)` | 所有触发器都满足才返回 |
| `with_timeout(coro, time, unit)` | 给协程加超时 |

### Clock 用法

```python
from cocotb.clock import Clock
c = Clock(dut.clk, 10, "ns")    # 10ns 周期 = 100MHz
cocotb.start_soon(c.start())    # 后台运行
```

## 并发执行

```python
# 顺序执行：阻塞直到完成
await reset_dut(dut, 500)

# 并发执行：不阻塞
task = cocotb.start_soon(reset_dut(dut, 500))
# 做其他事...
await task  # 等待完成
```

**官方提醒**：`First` 和 `Combine` 不会自动取消未完成的 Task，需要手动 `Task.cancel()`。

## 测试标记

### @cocotb.test() 参数

| 参数 | 说明 |
|------|------|
| `timeout_time` | 超时时间（防止死锁） |
| `timeout_unit` | 超时单位，默认 `'step'` |
| `expect_fail` | True 表示预期失败 |
| `expect_error` | 预期特定异常类型 |
| `skip` | 跳过此测试 |
| `stage` | 测试阶段编号 |
| `name` | 自定义测试名 |

### 测试结果判定

| 结果 | 条件 |
|------|------|
| PASS | 协程正常完成无异常；或调用 `cocotb.pass_test()`；或抛出 `CancelledError` |
| FAIL | assert 失败；或抛出任何其他 Exception |

## @cocotb.parametrize() (v2.0+)

```python
@cocotb.test()
@cocotb.parametrize(
    arg1=[0, 1],
    arg2=["a", "b"],
)
async def test(dut, arg1, arg2):
    ...
```
生成笛卡尔积测试：test_0_a, test_0_b, test_1_a, test_1_b。

## Python Runner API

cocotb 2.0+ 推荐使用 Python runner 替代 Makefile 流程。

```python
from cocotb_tools.runner import get_runner

runner = get_runner("verilator")
runner.build(
    sources=["path/to/design.sv"],
    hdl_toplevel="module_name",
    build_dir="sim_build",
)
runner.test(
    hdl_toplevel="module_name",
    test_module="tb.test_module",
    test_dir="path/to/tb",
    results_xml="sim_build/results.xml",
)
```

### runner.test() 关键参数

| 参数 | 说明 |
|------|------|
| `test_module` | Python 测试模块名（逗号分隔多个） |
| `hdl_toplevel` | HDL toplevel 模块名 |
| `test_dir` | 测试文件所在目录 |
| `results_xml` | xUnit XML 结果文件路径 |
| `waves` | 启用波形 |
| `gui` | 启用 GUI/波形查看器 |
| `seed` | 随机种子 |
| `testcase` | 只运行指定测试 |
| `test_filter` | 正则过滤测试名 |

### 与 pytest 集成

```bash
SIM=verilator pytest test_file.py -s
```

## 写入 testbench 最佳实践（官方推荐）

1. **用 `cocotb.log.info()` 而不是 `print()`**：`print()` 可能因缓冲导致乱序
2. **用 `logging.getLogger()` 创建分层 Logger**
3. **用 `finally` 清理资源**，不直接捕获 `CancelledError`
4. **每个测试独立**：`@cocotb.test()` 一个场景
5. **使用 `Clock()` 而非手动翻转时钟**

## 信号赋值方法（高级）

```python
from cocotb.handle import Deposit, Force, Release, Freeze

dut.sig.value = Deposit(12)   # 等价于 .value = 12
dut.sig.value = Force(12)     # 强制，直到 Release
dut.sig.value = Freeze()      # 冻结当前值
dut.sig.value = Release()     # 释放 Force/Freeze
```

**注意**：并非所有仿真器都支持 Force/Freeze/Release。

## 与已有知识库的一致性验证

| 知识条目 | 官方文档确认 |
|----------|------------|
| `.integer` 不存在，用 `int(value)` | ✅ 官方从未提及 `.integer` |
| `assert` 失败 = test FAIL | ✅ 明确说明 |
| `@cocotb.test()` 标记测试 | ✅ |
| `Clock(dut.clk, 10, "ns")` | ✅ |
| `cocotb.start_soon()` 后台运行 | ✅ |
| 信号写入有延迟 | ✅ 官方说 "not applied immediately, but delayed until the next write cycle" |
| `get_runner("verilator")` | ✅ |
| `runner.build()` + `runner.test()` | ✅ |

**未覆盖**：官方文档未提及跨测试 GPI 污染问题。这是 Verilator + cocotb 集成中我们通过实践发现的特定问题。
