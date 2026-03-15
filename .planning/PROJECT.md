# ChatGPT Register — 批量注册 CLI

## What This Is

ChatGPT 批量自动注册 CLI 工具，支持多种临时邮箱适配器（Catchmail、Maildrop、DuckMail、Mailcow、Mail.tm）、OAuth 登录、并发注册和 token 上传。v1.1 新增反风控能力：邮箱拟人化、多代理池调度、批次归档、浏览器指纹统一和请求时序正态化。

## Core Value

用户通过交互式向导完成所有注册配置，无需手动编辑任何配置文件。

## Requirements

### Validated

- ✓ 支持 DuckMail、Mailcow、Mail.tm 临时邮箱适配器 — existing
- ✓ 并发批量注册 ChatGPT 账号 — existing
- ✓ 自动获取 OTP 验证码并完成注册流程 — existing
- ✓ 支持 OAuth 登录与 token 获取 — existing
- ✓ 注册结果上传到 CPA / Sub2API — existing
- ✓ Rich 实时运行面板（RuntimeDashboard） — existing
- ✓ 代理支持（HTTP/SOCKS） — existing
- ✓ Pydantic 配置模型 + TOML Profile 持久化 — v1.0
- ✓ 多模块包结构，run_batch() 配置驱动 — v1.0
- ✓ 交互式向导：选择邮箱平台、上传目标、账号数量、并发数等 — v1.0
- ✓ TOML Profile 机制：保存/加载/管理多套配置 — v1.0
- ✓ 混合启动模式：有 profile 时快速选择，也可新建配置走完整流程 — v1.0
- ✓ 配置存储：默认 `~/.chatgpt-register/profiles/`，支持参数指定路径 — v1.0
- ✓ 配置确认摘要：选择完毕后显示配置概览，确认后再开始注册 — v1.0
- ✓ 完全替换 config.json：TUI + TOML 是唯一入口 — v1.0
- ✓ `--profile` 非交互直载模式 — v1.0
- ✓ Profile 派生复制 — v1.0
- ✓ 邮箱拟人化（HumanizedPrefixGenerator，4 种人名格式） — v1.1
- ✓ 批次输出归档（output/<YYYYMMDD_HHMM>/） — v1.1
- ✓ 多代理池调度（ProxyPool 线程安全负载均衡 + 向导多模式输入） — v1.1
- ✓ 旧 proxy 单字段自动迁移到 proxies 列表 — v1.1
- ✓ 统一 BrowserProfile dataclass + 10 个 Chrome 版本 — v1.1
- ✓ 场景化正态延迟分布（random_delay gaussian） — v1.1
- ✓ Worker 启动错开（gauss 2-8s stagger） — v1.1

### Active

（下一里程碑待定义，使用 `/gsd:new-milestone` 规划）

### Out of Scope

- Web UI — 本工具定位为本地 CLI，不做 Web 界面
- 实时远程监控 — 超出 CLI 工具范畴
- 多用户权限管理 — 单用户本地工具
- 配置加密存储 — CLI 工具依赖文件系统权限，文件权限设为 600 即可
- 内置 TOML 编辑器 — 向导表单是结构化编辑的最佳方式
- macOS/Linux UA 多样化 — 需验证 curl-cffi impersonate 与非 Windows TLS 指纹一致性，v2+
- 自适应并发限速 — 需积累足够成功/失败数据才能设计反馈控制器，v2+

## Context

- 项目已完成 v1.1 反风控增强，9,203 行 Python 代码
- Tech stack: Python 3.10+, Pydantic v2, questionary, Rich, TOML (tomllib/tomli_w), faker, names
- 包结构: `chatgpt_register/` (config/, core/, adapters/, upload/, tui/)
- 141 个测试全部通过
- 使用 `uv` 管理依赖，`pyproject.toml` 定义包元数据
- 已知技术债务：DuckMail/Mailcow/MailTm 适配器未接入 humanize_email（设计范围外）

## Constraints

- **配置格式**: TOML — 人类可读、便于版本控制
- **Python**: 3.10+ — pyproject.toml 已约束
- **兼容性**: config.json 已完全移除，TUI + TOML 是唯一配置方式

## Key Decisions

| Decision | Rationale | Outcome |
| ---------- | ----------- | --------- |
| 使用 questionary 替代 Textual | Textual headless 模式在测试中不稳定，questionary 更轻量可靠 | ✓ Good |
| TOML 格式存储配置 | 人类可读、结构化、Python 标准库支持（tomllib） | ✓ Good |
| 混合启动模式 | 兼顾快速使用和首次配置的便利性 | ✓ Good |
| 完全替换 config.json | 减少配置方式混乱，统一入口 | ✓ Good |
| 默认存储到 ~/.chatgpt-register/ | 跨项目共享，避免敏感信息进入仓库 | ✓ Good |
| TUI-as-Config-Generator 模式 | TUI 退出后再执行注册流程，职责清晰 | ✓ Good |
| run_batch 只接受 RegisterConfig | 所有配置均通过配置对象传递，消除全局变量 | ✓ Good |
| WizardState 保留草稿值 | 切换邮箱平台时隐藏字段只隐藏不清空，提升用户体验 | ✓ Good |
| Sub2API 绑定属于配置态 | 运行阶段只验证并执行，不再触发交互补问 | ✓ Good |
| CLI 参数面精简 | 只保留 `--profile`、`--profiles-dir`、`--non-interactive`，业务配置一律回归 profile | ✓ Good |
| config.model_copy 路径重定向 | 归档集成时下游代码零改动，深拷贝 config 修改输出路径即可 | ✓ Good |
| ProxyPool min-load 均衡替代 round-robin | 实际负载比轮询更均匀，对不均匀耗时的 worker 更友好 | ✓ Good |
| BrowserProfile frozen dataclass | 统一浏览器指纹来源，消除 register.py/sentinel.py 双维护 | ✓ Good |
| 正态分布延迟替代均匀分布 | 更接近真实用户行为分布，降低风控识别概率 | ✓ Good |

---
*Last updated: 2026-03-15 after v1.1 milestone*
