---
title: "webfetch 搜索策略——FPGA 知识获取"
category: patterns
severity: medium
simulator: n/a
created: 2026-07-21
updated: 2026-07-21
sources: [U5 webfetch 实战]
related: []
---

## 背景

Agent 在 knowledge/ 无法解决当前问题时，应使用 `webfetch` 工具搜索网络资源，
并将学到的新知识写入 knowledge/。

## 有效 URL 模式（已验证）

| 类型 | URL 模式 | 状态 |
|------|---------|------|
| GitHub raw | `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>` | ✅ 可读取 |
| AMD docs | `https://docs.amd.com/...` | ✅ 可连通（JS 页面需 text 格式） |
| 一般网页 | `https://<domain>/<path>` | ✅ 取决于网站 |

## 不适合的 URL

| 类型 | 原因 |
|------|------|
| PDF 文件 | 返回二进制，webfetch 无法解析 |
| GitHub blob | 返回 HTML 渲染页面，非源码 |
| 动态加载页面 | JS 渲染内容不可见 |

## 推荐搜索流程

1. **先搜 GitHub raw**：`site:github.com "module fir_filter" FPGA verilog` → 找到 repo → 用 raw URL
2. **再搜论文/博客**：Markdown/text 格式的文章
3. **最后 AMD/Xilinx docs**：官方文档技术细节最准确

## 有效关键词

- `FPGA FIR filter verilog implementation`
- `Xilinx DSP48E1 utilization guide`
- `timing closure pipelining DSP heavy designs`
- `cocotb axi verification example`
- `Verilog 2001 vs SystemVerilog synthesis`

## 写入知识库的规则

- 每个网上学到的知识点必须写一个条目
- 必须标注 `sources: [URL]` 
- must-know 条目需要 3 个以上独立来源确认
- high/medium 条目至少 1 个可靠来源
