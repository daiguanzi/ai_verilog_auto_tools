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

6. **String 参数不支持**：Verilator 5.036 不支持 `parameter MODE = "SDP"` 这种
   字符串参数，会报 `Illegal character in decimal constant`。改用整数编码
   （如 `0=SDP, 1=SP_RAM, 2=ROM`），并在 `project.json` 里填同样的整数值。

7. **unpacked 数组 + generate 输出管道在 Verilator 中脆弱**：用显式命名寄存器
   （`dout_s0, dout_s1, dout_s2`）代替 `logic [W-1:0] dout_q [0:N]` +
   `generate` 循环。更简单、更可靠。（参见 `ip_stub_development.md`。）

8. **fpga_tools.py CLI 导入模式**：当 `python agent_tools/fpga_tools.py` 以
   脚本方式运行时，`from agent_tools.xxx` 会失败（Python 只把 `agent_tools/`
   加到 `sys.path`，不把工作区根加进去）。所有 CLI 命令的导入必须用回退模式：
   ```python
   try:
       from agent_tools.xxx import something
   except ImportError:
       from xxx import something
   ```
   vivado_backend、ise_backend、sim_driver 都适用此规则。
