---
title: "WSL + Verilator/cocotb 运行要点（从 Windows 宿主调用）"
category: simulator
severity: must-know
simulator: verilator
created: 2026-06-22
updated: 2026-06-22
sources: [agent_tools/sim_driver.py, agent_tools/fpga_tools.py]
related: [knowledge/simulator/verilator_cocotb.md]
---

## 背景
本项目在 Windows 上开发，仿真在 WSL(Ubuntu) 的 Python 虚拟环境里跑。
从 Windows(PowerShell) 宿主调用 WSL 时有几个会反复踩的坑，记录如下。

## 必记要点

1. **Python 解释器**：WSL 里 `python` 不在 PATH，会报 `command not found`。
   直接用虚拟环境解释器：`.venv/bin/python ...`（`source .venv/bin/activate`
   在 `bash -lc` 非交互下不一定生效）。verilator 是系统二进制 (`/usr/local/bin/verilator`)，
   不需要 venv；但 cocotb 必须在 venv 里。

2. **从 PowerShell 调 WSL 的引号陷阱**：`wsl bash -lc "..."` 里若含 `$变量`、
   `\"` 嵌套或换行，PowerShell 会先把字符串解析坏（典型报错：把 `outputs`/`from`
   当成 cmdlet）。规避：**命令里写死字面路径、不用 `$` 变量**；要跑多行 Python 就
   **先写一个临时 `.py` 文件再执行**，不要内联。

3. **Verilator lint 的致命警告**：`verilator --lint-only -Wall` 会把**任何警告
   升级为致命错误**并打印 `%Error: Exiting due to N warning(s)`。要让"错误才阻断、
   警告只提示"，必须加 **`-Wno-fatal`**。（见 `fpga_tools.py` 的 lint 门禁。）

4. **`--xml-only` 已弃用但可用**：Verilator 5.036 提示 `--xml-only` deprecated
   (建议 `--json-only`)，但仍正常输出 XML。模块解析当前用 `--xml-only`，将来若失效
   再迁移到 `--json-only`。

5. **Git 在 Windows 跑**：`git` 命令在 Windows PowerShell 执行（凭据由 Windows
   凭据管理器 `manager` 提供）；不要在 WSL 里 git（路径变 `/mnt/c`，凭据不共享）。
   开局先跑只读 `git branch -a / status -sb / log` 并汇报，永不自动 push。
