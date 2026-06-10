# AI Agent Standard Workflow

## Phase 0: Understand Requirements

1. 阅读用户需求
2. 检查 `reference/` 目录是否有参考文件
3. 明确接口规范（输入输出、时序、协议）

## Phase 1: Architecture Design

1. 画出模块框图
2. 定义接口信号
3. 设计状态机（如有）
4. 列出测试场景（正常、边界、异常）

## Phase 2: Write Minimum RTL

1. 只写核心逻辑，不追求完美
2. 确保端口映射正确
3. 先用简单数据路径

## Phase 3: Write Minimum Testbench

1. 只测 1 个核心场景
2. 用 `insert_coin` 标准模式
3. 跑通基础仿真 → 确认 RTL 基本正确

## Phase 4: Expand Tests

1. 逐步加入更多测试场景
2. 边界条件测试
3. 错误条件测试
4. 每个场景独立成一个 `@cocotb.test()` 函数

## Phase 5: Fix & Iterate

1. 每次修改代码后运行全量仿真
2. 分析失败的测试
3. 修改 RTL（不改 testbench，除非测试本身有问题）
4. 重复直到全部通过

## Phase 6: Report & Export

1. 生成仿真报告（可选）
2. 导出到 `outputs/` 或直接给用户 `src/*.sv` 文件
3. 用户可导入 Vivado 做综合验证

---

## 每个 Phase 的检查清单

- [ ] Phase 0: 接口明确？有用例列表？
- [ ] Phase 1: FSM 状态完整？无死锁？
- [ ] Phase 2: 最小 test 跑通了？
- [ ] Phase 3: testbench 覆盖了所有场景？
- [ ] Phase 4: 包含边界 + 异常测试？
- [ ] Phase 5: 全部 PASS？最后一次修改没引入回归？
- [ ] Phase 6: 代码可综合？报告有结论？
