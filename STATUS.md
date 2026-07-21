# STATUS.md — FPGA Agent 项目状态

> 新对话开始时，AI 应读取：**AGENTS.md → STATUS.md → ROADMAP.md → knowledge/_index.md**
> 最后更新：2026-07-21

---

## 1. 这是什么

一个 AI 驱动的 FPGA 开发工具包。Agent 读需求 → 生成 RTL → 自动写 cocotb Python testbench → Verilator 快速迭代 → ModelSim 兼容验证 → Vivado 综合/时序 → 交付可上板的工程。

**技术栈**: Verilator 5.036 + cocotb 2.0.1 (WSL2), Vivado 2018.2 (Win), ModelSim 10.4 (Win), Python 3.14

---

## 2. 当前能力一览

| 类别 | 能做什么 | 命令/工具 |
|------|---------|----------|
| 仿真 | Verilator+cocotb 秒级迭代，lint 门禁，scoreboard+参考模型+随机测试 | `fpga_tools.py run` |
| 多模块 | 层次化工程，依赖树，自动找顶层 | `summary` 命令 |
| AXI 总线 | cocotbext-axi BFM 读写寄存器 | Phase B2 已验证 |
| IP 替身 | BRAM/FIFO/Multiplier 三个替身库，契约测试全 5/5 | `ip_models/` + project.json `ip` 段 |
| IP 扫描 | 解析 .xci 文件，自动匹配替身 | `fpga_tools.py ip-scan` |
| Vivado | XDC 约束生成、综合/实现/bitstream、时序报告解析 | `vivado-synth`/`vivado-xdc` |
| Vivado 仿真 | ModelSim(2.3x快)/xsim 行为仿真，自动 .v TB 生成 | `vivado-sim` |
| ISE VM | ISE 14.7 VM 通过 VirtualBox 调用，ISim 仿真+综合 | `ise-synth`/`ise-sim`（按需） |
| 时序 | timing_loop 自动放宽周期→收敛，full-run 自动接入 | Phase D3 已验证 ✅ |
| 工程管理 | .xpr 打开/备份/git/增删文件 | `vivado_backend/project_manager.py` |
| 知识库 | 21 条知识条目（sim/patterns），复盘机制 | `knowledge/` |

---

## 3. 架构决策

| # | 决策 |
|---|------|
| D1 | 仿真统一用 Verilator+cocotb（WSL）；Vivado 只做综合/时序/bitstream |
| D2 | 混合运行模式：仿真在 WSL，Vivado/ModelSim 在 Windows |
| D3 | IP 双轨：仿真用 ip_models/ 替身，上板用真 .xci |
| D4 | 主要面向 Xilinx Vivado 2018.2；ISE 14.7 VM 作为按需备用 |
| D5 | 所有项目最终需通过综合+时序验证 |

---

## 4. V3 执行流程

Agent 自主调度，按成本递增使用工具：

```
改 RTL         → fpga_tools.py run          (秒级，Verilator)
Verilator 全过  → fpga_tools.py vivado-sim   (秒级，ModelSim)
ModelSim 全过   → 问用户 → full-run          (分钟级，综合认证)
```

**原则**：能在仿真解决的绝不调综合。综合只跑一次——当所有仿真都通过之后。

---

## 5. 路线图完成情况

```
✅ 阶段 A  加固地基       (A1–A4)
✅ 阶段 B  复杂度升级     (B1–B4)
✅ 阶段 C  IP 双轨战略   (C1–C6)
✅ 阶段 D  上板轨道       (D1–D4)
✅ 阶段 E  端到端整合    (E1–E2)
✅ V3 自主调度机制       (AGENTS §4)
🧊 ISE VM               (ISE-1/2/3 done, ISE-4 待端到端验证)
🧪 DFT 验证项目 ✅（已提拔 11_dft8）
✅ DFT8-AXI 全流程 ✅（已提拔 12_dft8_axi，AXI 总线封装 + full-run PASS + timing_loop 收敛）
✅ FIR 滤波器 ✅（已提拔 13_fir_filter，8-tap MAC + AXI + Vivado GUI + WNS=+1.71ns）
```

---

## 6. 环境

| 工具 | 版本 | 位置 |
|------|------|------|
| WSL2 | Ubuntu 24.04 | `wsl` |
| Verilator | 5.036 | `/usr/local/bin/verilator` |
| cocotb | 2.0.1 | `.venv` |
| Vivado | 2018.2.2 | `C:\Xilinx\Vivado\2018.2` |
| ModelSim | 10.4 | `C:\modeltech64_10.4\win64` (快 2.3x 于 xsim) |
| ISE 14.7 | VM (VirtualBox Win7) | `ise_backend/` |

---

## 7. 下一步

### 工具升级
| # | 升级方向 | 状态 | 工作量 |
|---|---------|------|--------|
| U1 | full-run 自动接 timing_loop | ✅ | 小 |
| U2 | 生成 GUI 可打开的 Vivado 项目 | ✅ | 中 |
| U3 | 自动 .v TB 生成器升级（多周期 FSM） | ⬜ pending (spec ready) | 中 |
| U4 | agent_tools 配置文件 | ✅ | 小 |
| U5 | webfetch 实战验证 | ✅ | 小 |
| U6 | ISE-4 端到端验证 | 🧊 暂缓 | 大 |
| T1 | Pipeline Advisor (timing_advise) | ✅ | 大 |
| T2 | Logic Depth Optimizer (timing_advise) | ✅ | 大 |
| U7 | AGENTS §10 "重读最近复盘" | ✅ | 小 |
| U8 | full-run --no-sim | ✅ | 小 |
| U9 | vivado-project 增量更新 | ✅ | 小 |

### 项目覆盖
| # | 项目 | 验证能力 | 状态 |
|---|------|---------|------|
| P1 | FIR 滤波器 (DSP 流水线) | ✅ examples/13 | done |
| P2 | 异步 FIFO (CDC) | ✅ examples/14 | done |
| P3 | BRAM IP 双轨验证 | ✅ outputs/bram_acc | done |
| P4 | AXI-Stream→AXI-Lite 桥 | ✅ outputs/axistream_bridge | done |
| P5 | 覆盖率驱动随机验证 | ⬜ pending (spec ready) | 中 |
| P6 | 主动总线设计 (IO 超标预防) | ✅ | done |

### 优先级建议
1. **P5 覆盖率驱动验证** — 最后的能力缺口
2. **U3 自动 TB 升级** — 提升多周期 FSM 项目的测试自动化
3. 新一轮项目建议：复杂协议 (Ethernet/I2C)、多时钟系统集成
5. **U4 agent_tools 配置文件**
6. **U7 AGENTS 启动清单改进**（小改动，随时可做）
