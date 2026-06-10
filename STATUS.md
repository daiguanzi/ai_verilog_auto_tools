# STATUS.md — FPGA Agent 项目状态

> 新对话开始时，AI 应读取：**AGENTS.md → STATUS.md → knowledge/_index.md**

---

## 1. 这是什么

一个 AI 驱动的 FPGA 开发工具包。Agent 读取需求文档 → 生成 RTL → 自动写 cocotb Python testbench → Verilator 跑仿真 → 读取结果 → 迭代修改直到全通过。

**技术栈**: Verilator 5.036 + cocotb 2.0.1 (WSL2 Ubuntu), Python 3.14

---

## 2. 已完成

### 环境
| 工具 | 版本 | 位置 |
|------|------|------|
| WSL2 | Ubuntu 24.04 | `wsl` |
| Verilator | 5.036 | `/usr/local/bin/verilator` |
| cocotb | 2.0.1 | `.venv/lib/...` |
| Python | 3.14.4 | `.venv/bin/python` |
| Icarus | 12.0 | `/usr/bin/iverilog` |
| GTKWave | 3.3.126 | `/usr/bin/gtkwave` |

### 工具
- `agent_tools/sim_driver.py` — 仿真引擎（调用 cocotb runner，返回 JSON）
- `agent_tools/fpga_tools.py` — CLI 工具（scan/summary/run/find-top）
- `agent_tools/project_gen.py` — 从零创建项目骨架
- `agent_tools/reference_reader.py` — 读取 reference/ 中的参考文件

### 示例项目
| 示例 | 测试数 | 状态 |
|------|--------|------|
| `examples/01_adder/` | 2 | ✅ PASS |
| `examples/02_vending_machine/` | 9 | ✅ PASS |
| `outputs/counter/` | 6 | ✅ PASS (端到端验证) |

### 知识库 (knowledge/)
| 条目 | 内容 |
|------|------|
| `simulator/verilator_cocotb.md` | Eval→Edge→Callback 模型, GPI 延迟, 组合 vs 寄存器 |
| `patterns/delayed_input_signal.md` | 3-edge 脉冲驱动模式 |
| `patterns/registered_vs_combinational.md` | 用寄存器输出代替组合输出 |
| `patterns/blocking_assign_accumulate.md` | always_comb 中多通道累加 |
| `patterns/robust_test_reset.md` | 跨测试 GPI 污染 + 复位替代方案 |

### 复盘报告
- `reports/vending_machine_review.md`
- `reports/counter_review.md`

### Git
- Remote: `https://github.com/daiguanzi/ai_verilog_auto_tools`
- Branch: `main`
- Last commit: `Step 2: counter project end-to-end verification (6/6 PASS)`

---

## 3. 正在做什么

**Step 2 全部完成** ✅。4 个基础场景全部通过仿真：

| 场景 | 测试 | 迭代 |
|------|------|------|
| 按键消抖 | 5/5 | 2 |
| UART TX | 4/4 | 1 |
| SPI Master | 4/4 | 1 |
| FIFO | 5/5 | 2 |
| **合计** | **18/18** | **累计 6 次** |

下一步：Step 3 Git push。

---

## 4. 下一步（按顺序执行）

### Step 1: 扩充官方文档 ✅ (2026-06-10 完成)
1. ✅ 抓取 Verilator 官方手册关键页面：https://verilator.org/guide/latest/
   - 重点：Verilating 流程、Connecting to Models、Simulating
2. ✅ 抓取 cocotb 官方文档：https://docs.cocotb.org/en/stable/
   - 重点：Writing Testbenches、Triggers、Python Runner API
3. ✅ 编写 `knowledge/simulator/verilator_reference.md` 和 `knowledge/simulator/cocotb_reference.md`
4. ✅ 用官方信息验证和修订现有知识条目
   - **修正**：verilator_cocotb.md 中 EVAL 内部顺序（时序先于组合，非组合先于时序）
   - **确认**：GPI 写入延迟是官方设计行为（"writes are not applied immediately, but delayed until the next write cycle"）
   - **确认**：跨测试 GPI 污染未在官方文档中提及，属于 Verilator+cocotb 集成特有现象

### Step 2: 积累基础场景
按难度递增：

| 序号 | 场景 | 知识点 | 状态 |
|------|------|--------|------|
| 1 | 按键消抖 (debounce) | 定时器 + FSM + 脉冲输出 | ✅ 5/5 PASS (2 iterations) |
| 2 | UART 发送器 (TX) | 波特率 + 移位寄存器 + 状态机 | ✅ 4/4 PASS (1 iteration) |
| 3 | SPI Master | 时钟相位 + 数据移位 + CS | ✅ 4/4 PASS (1 iteration) |
| 4 | FIFO (手写) | 读写指针 + 满空判断 | ✅ 5/5 PASS (2 iterations) |

每个场景的流程：
```
project_gen.py 创建骨架 → 写 RTL → 写 testbench → fpga_tools.py run
→ PASS → 写 reports/ 复盘 → 更新 knowledge/ → 更新此 STATUS.md
```

### Step 3: Git push
每次完成一个场景或重要更新后：
```powershell
cd C:\Users\12430\Desktop\ai_verilog_auto_tools
git add .
git commit -m "描述做了什么"
git push
```

---

## 5. 执行命令速查

```bash
# WSL 中运行（.venv 自动激活）

# 扫描项目
python agent_tools/fpga_tools.py summary examples/02_vending_machine

# 运行仿真
python agent_tools/fpga_tools.py run examples/02_vending_machine

# 生成新项目
python agent_tools/project_gen.py <name> \
  --sources src/<name>.sv --toplevel <name> \
  --test-module tb.test_<name>

# Git (PowerShell)
cd C:\Users\12430\Desktop\ai_verilog_auto_tools
git add . ; git commit -m "说明" ; git push
```

---

## 6. 关键教训（写 testbench 前必读）

1. **GPI 写入有 1-2 Edge 延迟**。信号写完后，寄存器输出在下 1-2 个 RisingEdge 后才更新
2. **Level 控制信号**（enable, up_down）：`apply_and_settle()` 会用 2 个 Edge，
   第 2 个 Edge 会附带一次"生效"（比如 enable=1 时计数器顺便 +1）
3. **脉冲输入**（coin, strobe）：必须在 1 个 Edge 后立即清除，
   否则跨 2 个 Edge 会重复触发
4. **异步复位不可靠**：用 `load` 设置已知状态，不要依赖 `assert count == 0` after reset
5. **跨测试 GPI 污染**：每个测试开头用 `reset_and_clear()` 清除所有控制信号
6. **读信号用 `int(value)`**，不是 `.integer`
7. **所有状态输出用寄存器**（`always_ff`），不用组合输出
8. **always_comb 中多通道累加**：`x = x + delta` 而非 `x = base + delta`

---

## 7. 项目版本

| 版本 | 日期 | 内容 |
|------|------|------|
| v1.0 | 2026-06-09 | 初始框架 + 2 示例 + 端到端验证 |
| v1.1 | 2026-06-10 | Step 1: 官方文档抓取 + 知识库交叉验证 |
| v1.2 | 2026-06-10 | Step 2: 4 基础场景全部通过 (18/18 tests, 6 total iterations) |
