---
title: "ISE 14.7 虚拟机后端——从 Agent 自动调用 ISE 工具链"
category: simulator
severity: high
simulator: ise
created: 2026-07-08
updated: 2026-07-08
sources: [agent_tools/ise_backend, C:/FPGA_Projects/ISE_14.7_VM_Guide.md]
related: [knowledge/simulator/vivado_ip_verilator_gap.md, knowledge/simulator/wsl_verilator_ops.md]
---

## 背景
部分老器件（Spartan-6、Virtex-6 等）只有 ISE 14.7 支持，而 ISE 不能直接
装在 Win11 上。方案：**VirtualBox VM (Win7 + ISE 14.7) + 共享文件夹 +
VBoxManage guestcontrol**，Agent 从宿主流水线式调用。

## 架构

```
Win11 主机                          Win7 VM (VirtualBox)
agent_tools/ise_backend/
  ise_remote.py   ──tcl──►  VBoxManage guestcontrol
  vm_config.json   共享文件夹  ↓
  ISE_Remote.ps1  C:/FPGA_Projects ←──→ Z: (自动挂载)
                                   │
                                   ├─ XST (综合)
                                   ├─ NGDBuild/MAP/PAR (实现)
                                   ├─ BitGen (比特流)
                                   └─ ISim (fuse + tb.exe) (仿真)
```

## 使用方式

### 配置
1. 复制 `agent_tools/ise_backend/vm_config.example.json` → `vm_config.json`
2. 填入 VM 凭据（`vm_config.json` 已 gitignored，不会提交）

### 自动启动 VM
Agent 调用 `ensure_vm_ready()` 自动检查 + 启动 VM，约 40 秒后可用。
若权限不够才提示用户手动处理。

### ISim 仿真（自动 testbench）
支持从结构化测试向量**自动生成 Verilog testbench**——无需手写 `.v` TB：
```python
signals = [
    {"name": "clk",   "width": 1,  "dir": "input"},
    {"name": "a",     "width": 8,  "dir": "input"},
    {"name": "b",     "width": 8,  "dir": "input"},
    {"name": "sum",   "width": 9,  "dir": "output"},
]
test_vectors = [
    {"stimulus": {"a": 0, "b": 0},    "expected": {"sum": 0},   "label": "0+0"},
    {"stimulus": {"a": 255, "b": 1},  "expected": {"sum": 256}, "label": "255+1"},
]
ise_sim(project_dir, top="my_design", sources=["my_design.v"],
        signals=signals, test_vectors=test_vectors)
```

### ISE 综合流水线
```python
ise_synth(project_dir, top="my_design", device="xc6slx9-2-csg324",
          sources=["module1.v", "top.v"])
```

## 启用条件
- `project.json` 中有 `ise` 段（指定 device/family）
- 或用户明确要求用 ISE
- 或参考资料中有 `.xise` 项目文件
- 或目标器件为 Spartan-6/Virtex-6 等 ISE-only 系列
