# Simulator Guide: Verilator + cocotb 精确时序模型

> **关键！** 不读此文档就会陷入无尽的时序调试地狱。

## 核心模型

### Verilator 的 Eval → Edge → Callback 周期

每个时钟周期分为三个阶段，**顺序固定**：

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ 1. EVAL  │ ──▶ │ 2. EDGE  │ ──▶ │ 3. CALLBACK │
│ 组合逻辑  │     │ 寄存器更新 │     │ testbench 执行 │
└──────────┘     └──────────┘     └──────────┘
```

1. **EVAL**: 组合逻辑用**当前输入**计算 `_d`（next-state）信号
2. **EDGE**: 所有 `always_ff` 的寄存器 `_q <= _d`
3. **CALLBACK**: cocotb testbench 运行，可以**读取输出**和**设置输入**

### GPI 信号写入规则

| 写入时机 | 组合输出 (dispense_d) | 寄存器输出 (amount_q) |
|---------|---------------------|----------------------|
| Callback 中设置输入 | **EVAL 立即响应**，数据立即可见 | **不更新**，要等下个 EDGE |
| 下一个 EDGE | 用新输入重新计算 | **更新为 _d 值** |

### 信号写入延迟表

```
你在 callback 写了 coin_05 = 1:

当前周期 EDGE 刚过
  ├── 马上 EVAL: coin_05=1 被看到，amount_d 更新
  │   但 amount_q 不变（已经过了 EDGE）
  │
  下一个 EDGE
  ├── EVAL: coin_05 仍为 1，amount_d = amount_q + 5
  ├── EDGE: amount_q <= amount_d  ← 寄存器终于更新了！
  └── Callback: 你现在能读到 amount_q 的新值
```

**总结：信号写入到寄存器可见，需要 1 个 EDGE 延迟。**

## 标准 testbench 时序模式

### 模式 1: insert_coin（3-edge 模式）

```python
async def insert_coin(dut, coin_05=0, coin_1=0, coin_2=0):
    # Step 1: 设置硬币信号（当前 callback 中）
    dut.coin_05.value = coin_05
    dut.coin_1.value = coin_1
    dut.coin_2.value = coin_2
    
    # Step 2: 等待 1 个 EDGE（信号写入被 EVAL 看到）
    await RisingEdge(dut.clk)
    
    # Step 3: 立即清除硬币（防止下个 EDGE 重复计数）
    clear_inputs(dut)
    
    # Step 4: 等待第 2 个 EDGE（寄存器更新，amount_q 反映新值）
    await RisingEdge(dut.clk)
    
    # Step 5: ★ 在此采样 ★
    disp     = int(dut.dispense.value)   # 寄存器输出，EDGE 刚更新
    chg_valid = int(dut.change_valid.value)
    change   = int(dut.change.value)
    amount   = int(dut.amount.value)
    
    # Step 6: 等待第 3 个 EDGE（让清除信号传播）
    await RisingEdge(dut.clk)
    
    return { ... }
```

### 时序追踪示例

```
投入 0.5 元 (coin_05=1)：

Cycle N-1, Callback:
  set coin_05 = 1

Cycle N, EVAL:
  amount_d = amount_q + 5 = 0+5 = 5
  amount_d < 15，no dispense

Cycle N, EDGE:
  amount_q <= 5  ← 寄存器采纳了 EVAL 结果

Cycle N, Callback:
  clear_inputs → coin_05 = 0

Cycle N+1, EVAL:
  coin_05 = 0
  amount_d = amount_q = 5（不变）

Cycle N+1, EDGE:
  amount_q <= 5

Cycle N+1, Callback:
  ★ 采样 ★
  amount = 5 ✓
  dispense = 0 ✓
```

### 模式 2: press_cancel

```python
async def press_cancel(dut):
    dut.cancel.value = 1
    await RisingEdge(dut.clk)      # 写入生效
    dut.cancel.value = 0
    await RisingEdge(dut.clk)      # 寄存器更新
    # ★ 在此采样 ★
    chg_valid = int(dut.change_valid.value)
    change   = int(dut.change.value)
    amount   = int(dut.amount.value)
    await RisingEdge(dut.clk)      # 清除传播
    return { ... }
```

## 组合输出 vs 寄存器输出

| 类型 | 例子 | 采样时机 | 可见时长 |
|------|------|---------|---------|
| 组合输出 | `assign x = a & b` | EVAL 后立即可见 | 直到下次 EVAL 改变 |
| 寄存器输出 | `always_ff ... q <= d` | EDGE 后可见 | 刚好 1 个完整周期 |

**强烈建议：将所有关键输出做成寄存器输出**（如 dispense、change_valid），方便 testbench 采样。

## 常见陷阱

### 陷阱 1: 在错误的位置采样寄存器输出

```python
# ❌ 错误：刚设置 coin 就采样 amount
dut.coin_05.value = 1
amount = int(dut.amount.value)  # 还是 0！还没到 EDGE

# ✓ 正确：等 EDGE 后采样
dut.coin_05.value = 1
await RisingEdge(dut.clk)
clear_inputs(dut)
await RisingEdge(dut.clk)  # 寄存器已更新
amount = int(dut.amount.value)  # 5 ✓
```

### 陷阱 2: 不清除硬币信号导致双倍计数

```python
# ❌ 硬币信号保持 2 个周期 → amount 加了两次
dut.coin_05.value = 1
await RisingEdge(dut.clk)  # +5
await RisingEdge(dut.clk)  # +5 again!
amount = 10  # 应该是 5

# ✓ 在第一个 EDGE 后立即清除
dut.coin_05.value = 1
await RisingEdge(dut.clk)
dut.coin_05.value = 0       # 立即清除
await RisingEdge(dut.clk)
amount = 5  # ✓
```

### 陷阱 3: blocking assignment 覆盖

```verilog
// ❌ 同时投两枚硬币时后者覆盖前者
if (coin_05) amount_d = amount_q + 5;  // amount_d = 5
if (coin_1)  amount_d = amount_q + 10; // amount_d = 10, 丢了 5!

// ✓ 使用累加（读取 amount_d 自身）
if (coin_05) amount_d = amount_d + 5;  // amount_d = 5
if (coin_1)  amount_d = amount_d + 10; // amount_d = 15 ✓
```

### 陷阱 4: cocotb `Logic` 类型没有 `.integer`

```python
# ❌
val = dut.signal.value.integer  # AttributeError

# ✓
val = int(dut.signal.value)
```

### 陷阱 5: cocotb 信号赋值与比较

```python
# 赋值
dut.signal.value = 1    # 赋 1
dut.signal.value = 0    # 赋 0

# 读取
int(dut.signal.value)   # 读到 0 或 1
dut.signal.value == 1   # 直接比较，返回 bool

# 多 bit 信号
dut.bus.value = 42      # 赋整数
int(dut.bus.value)      # 42
dut.bus.value == 42     # True
```

## 调试步骤

当仿真行为异常时，按以下顺序排查：

1. **检查 RTL**: `always_comb` 的 blocking assignment 顺序是否正确
2. **检查 timing**: 是否在正确的 EDGE 后采样
3. **检查 clear**: 硬币/控制信号是否在 1 个周期后清除
4. **打印内部状态**: `cocotb.log.info(f"amount_q={int(dut.amount.value)}")`
5. **简化测试**: 写一个只测 1 个硬币的 debug test
6. **导出波形**: `EXTRA_ARGS='--trace --trace-structs'` 用 GTKWave 查看

## 已安装的工具

| 工具 | 版本 | 位置 | 说明 |
|------|------|------|------|
| Verilator | 5.036 | WSL `/usr/local/bin/verilator` | 最快开源仿真器 |
| Icarus | 12.0 | WSL `/usr/bin/iverilog` | 备用仿真器 |
| cocotb | 2.0.1 | .venv `pip install cocotb` | Python testbench |
| GTKWave | 3.3.126 | WSL `/usr/bin/gtkwave` | 波形查看 |
| Python | 3.14.4 | .venv | 虚拟环境 |

## 项目结构约定

```
project_name/
├── project.json          # 必须：告诉 agent 怎么跑
│   {
│     "sources": ["src/*.sv"],
│     "toplevel": "top_module",
│     "test_module": "tb.test_top",
│     "sim": "verilator"
│   }
├── src/                  # HDL 源码
│   └── *.sv / *.v
└── tb/                   # Python testbench
    └── test_*.py
```

项目创建后，一键运行：`python agent_tools/fpga_tools.py run project_path`
