# STATUS.md — FPGA Agent 项目状态

> 新对话开始时，AI 应读取：**AGENTS.md → STATUS.md → ROADMAP.md → knowledge/_index.md**

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

**阶段 0（单模块仿真闭环）已完成** ✅。4 个基础场景全部通过仿真：

| 场景 | 测试 | 迭代 |
|------|------|------|
| 按键消抖 | 5/5 | 2 |
| UART TX | 4/4 | 1 |
| SPI Master | 4/4 | 1 |
| FIFO | 5/5 | 2 |
| **合计** | **18/18** | **累计 6 次** |

**当前位置：阶段 A —— 加固地基**（见 `ROADMAP.md`）。
- ✅ A1 完成：`fpga_tools.py` 改用 `verilator --xml-only` 解析（带正则回退），可靠提取端口位宽/参数默认值/自动找 top。
- ✅ A2 完成：`project.json` 支持 `includes`/`defines`/`parameters`/`timescale`/多文件，验证项目 `outputs/a2_check` 2/2 PASS，旧项目无回归。
- ✅ 整理 outputs→examples：提拔 `06_spi_master`(4/4)、`07_counter`(6/6)、`08_config_demo`(2/2)；清空 outputs 草稿区；提拔机制写入 `AGENTS.md §8`。examples 现共 8 个（01–08）。
- ✅ A3 完成：lint 门禁（`verilator --lint-only -Wall -Wno-fatal`）。错误阻断仿真、警告仅提示；`run` 默认先 lint，可 `--no-lint` 跳过；新增独立 `lint` 命令。验证：干净示例过、位宽截断报警告、未定义信号被拦下。
- ✅ A4 完成：`templates/tb_comprehensive.py` 加入 `Scoreboard`（direct/queue 两用法）+ `reference_model` 骨架 + 演示测试；新增知识条目 `patterns/scoreboard_reference_model.md`。验证 `outputs/a4_check` 2/2。

**🎉 阶段 A（加固地基）全部完成（A1–A4）。** 正在进行**阶段 B：复杂度升级**。
- ✅ B1 完成：多模块/层次化工程支持——`print_project_summary` 新增依赖树；2 层示例 `outputs/mac_unit`（multiplier+mac_unit）4/4 PASS。

下一步：B2 接入 `cocotbext-axi` 验证 AXI-Lite / AXI-Stream 设计。

---

## 4. 下一步（按顺序执行）

完整长期路线图见 **`ROADMAP.md`**（阶段 A–E + 架构决策 D1–D5 + 数据探针）。
当前进行到 **阶段 A**，按 ROADMAP 中 A1→A4 顺序执行。每完成一项更新此处与 ROADMAP 勾选框。

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
