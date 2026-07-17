---
title: "替身模型契约测试规范——ip_models 验收标准"
category: patterns
severity: must-know
simulator: verilator
created: 2026-07-08
updated: 2026-07-08
sources: [ip_models/bram, ip_models/fifo, ip_models/multiplier]
related: [knowledge/patterns/ip_stub_development.md, knowledge/patterns/scoreboard_reference_model.md]
---

## 规范 v1.0

每个 `ip_models/` 下的替身模型必须配一份 `project.json` + `tb/test_*.py`，
通过下方**通用测试** + **IP 专属测试**全部达标才视为"验收通过"。

---

## 通用测试（所有替身必须通过）

| # | 测试名 | 内容 | 目的 |
|---|--------|------|------|
| T1 | **单次基本操作** | 一个输入 → 一个输出 | 验证核心功能路径可用 |
| T2 | **多地址/多周期遍历** | 连续 N 次操作，每次校验结果 | 验证持续运算无累积偏差 |
| T3 | **覆盖/回写** | 对同一地址/端口写两次，验证最后一次值胜出 | 验证写后写语义正确 |
| T4 | **复位/清零** | 断言复位后输出归零（或回到规格定义的初始态） | 验证复位行为匹配 IP 规格 |
| T5 | **边界/极值** | 最大值/最小值/零值输入 | 验证位宽截断、溢出保护 |

---

## IP 专属测试（按替身类型追加）

### BRAM（blk_mem_gen）
- [x] **字节写使能**（T6）：`wea=0x1` 只更新最低字节，其他字节不变
- [x] **延迟**（T7）：LATENCY=N 时数据在 N+1 周期出现；N 周期前数据为 0（旧）

### FIFO（fifo_generator）
- [x] **满空标志**（T6）：写 DEPTH 次 → `full=1`；读完 → `empty=1`
- [x] **折回测试**（T7）：写读交替 DEPTH+8 轮，验证指针环绕无错
- [x] **溢出保护**（T8）：满时写操作被忽略，数据不丢失
- [x] **下溢保护**（T9）：空时读操作返回上个有效值（不返回内存垃圾）

### Multiplier（mult_gen）
- [x] **可交换性**（T6）：`a*b == b*a`
- [x] **有符号测试**（T7）：负值 × 正值 = 正确补码结果

---

## 新增替身时的检查清单

开发新 IP 替身时（如后续加 clk_wiz、AXI GPIO）：
- [ ] 建 `ip_models/<name>/` 目录，含 `ip_<name>.sv` + `tb/` + `project.json`
- [ ] 通用 T1–T5 全部通过
- [ ] 添加至少 2 条 IP 专属测试（T6+），覆盖该 IP 的核心区分特性
- [ ] `project.json` 必须设 `"parser": "verilator"` / 对应参数
- [ ] 跑 `fpga_tools.py run ip_models/<name>` → 全部 PASS
- [ ] 本文更新专属测试清单（勾选新增行）
