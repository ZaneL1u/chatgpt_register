# ChatGPT Register — TUI 化重构

## What This Is

ChatGPT 批量自动注册 CLI 工具，支持多种临时邮箱适配器（DuckMail、Mailcow、Mail.tm）、OAuth 登录、并发注册和 token 上传。当前版本计划将散乱的配置体验（config.json + CLI 参数 + 环境变量）替换为基于 Textual 的交互式 TUI 向导，引入 TOML profile 机制。

## Core Value

用户通过 TUI 交互式向导完成所有注册配置，无需手动编辑任何配置文件。

## Requirements

### Validated

<!-- 已有代码中已经实现并在用的能力 -->

- ✓ 支持 DuckMail、Mailcow、Mail.tm 临时邮箱适配器 — existing
- ✓ 并发批量注册 ChatGPT 账号 — existing
- ✓ 自动获取 OTP 验证码并完成注册流程 — existing
- ✓ 支持 OAuth 登录与 token 获取 — existing
- ✓ 注册结果上传到 CPA / Sub2API — existing
- ✓ Rich 实时运行面板（RuntimeDashboard） — existing
- ✓ 代理支持（HTTP/SOCKS） — existing

### Active

<!-- 本次迭代的目标 -->

- [ ] Textual TUI 向导：交互式选择邮箱平台、上传目标、账号数量、并发数等
- [ ] TOML Profile 机制：保存/加载/管理多套配置
- [ ] 混合启动模式：有 profile 时快速选择，也可新建配置走完整流程
- [ ] 配置存储：默认 `~/.chatgpt-register/profiles/`，支持参数指定路径
- [ ] 配置确认摘要：选择完毕后显示配置概览，确认后再开始注册
- [ ] 完全替换 config.json：移除旧配置方式，TUI + TOML 是唯一入口

### Out of Scope

- Web UI — 本工具定位为本地 CLI，不做 Web 界面
- 实时远程监控 — 超出 CLI 工具范畴
- 多用户权限管理 — 单用户本地工具

## Context

- 现有主逻辑集中在单文件 `chatgpt_register.py`（~2000+ 行）
- 配置来源优先级：CLI 参数 > 环境变量 > config.json，混杂且难以管理
- 已有 `questionary` 依赖用于简单交互，但本次选择 Textual 实现更丰富的 TUI 体验
- 已有 `rich` 依赖用于运行时面板，Textual 底层也基于 Rich
- 项目使用 `uv` 管理依赖，`pyproject.toml` 定义包元数据

## Constraints

- **TUI 框架**: Textual — 用户明确选择
- **配置格式**: TOML — 人类可读、便于版本控制
- **Python**: 3.10+ — pyproject.toml 已约束
- **兼容性**: 完全替换旧配置方式，不保留 config.json 兼容

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 使用 Textual 而非 questionary | 功能更丰富，组件化、可测试，适合复杂 TUI | — Pending |
| TOML 格式存储配置 | 人类可读、结构化、Python 标准库支持（tomllib） | — Pending |
| 混合启动模式 | 兼顾快速使用和首次配置的便利性 | — Pending |
| 完全替换 config.json | 减少配置方式混乱，统一入口 | — Pending |
| 默认存储到 ~/.chatgpt-register/ | 跨项目共享，避免敏感信息进入仓库 | — Pending |
| 配置完成后确认再跑 | 避免误操作，给用户检查机会 | — Pending |

---
*Last updated: 2026-03-07 after initialization*
