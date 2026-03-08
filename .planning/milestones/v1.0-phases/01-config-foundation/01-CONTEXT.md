# Phase 1: 配置层基础 - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

为所有配置字段建立统一的 Pydantic 数据模型（RegisterConfig）和 TOML 持久化能力（ProfileManager）。ProfileManager 支持 Profile 的创建/读取/保存/列举，存储路径可通过参数指定。现有 20+ 个模块级全局变量收拢为 RegisterConfig 数据类字段。

不包含：TUI 向导、CLI 集成、模块拆分、旧配置迁移工具。

</domain>

<decisions>
## Implementation Decisions

### Pydantic 模型结构
- 采用嵌套子模型结构：RegisterConfig 包含 EmailConfig、RegConfig（注册参数）、OAuthConfig、UploadConfig 等子模型
- TOML section 自然对应子模型层级：`[email]`、`[registration]`、`[oauth]`、`[upload]`
- 与未来 TUI 分屏向导的步骤对齐（每个子模型对应一屏）

### 邮箱平台联动
- EmailConfig 包含 `provider: Literal["duckmail", "mailcow", "mailtm"]` 字段
- 三个平台的专属配置作为 Optional 子模型：`duckmail: DuckMailConfig | None`、`mailcow: MailcowConfig | None`、`mailtm: MailTmConfig | None`
- 通过 `@model_validator(mode="after")` 校验 provider 与对应子模型的一致性（选了 duckmail 则 duckmail 配置必填）
- TOML 中只写实际使用的平台 section，未使用的平台不需要出现

### 上传目标联动
- 与邮箱配置采用相同的 Optional 子模型模式
- UploadConfig 包含 `targets: list[Literal["cpa", "sub2api"]]`，允许空列表（不上传）
- CPA 和 Sub2API 各自为 Optional 子模型，validator 校验 targets 与子模型的一致性

### 校验错误信息
- 校验失败时提供中文可读错误消息，不使用 Pydantic 默认的英文技术格式
- 错误消息风格与现有代码库一致，便于未来 TUI 直接展示

### Claude's Discretion
- Profile TOML 文件的命名规则和目录组织方式
- 全局变量收拢的具体迁移策略（一步切换 vs 过渡期）
- TOML 文件中的注释模板和 section 排列顺序
- ProfileManager 的具体 API 设计（方法签名、错误处理策略）

</decisions>

<specifics>
## Specific Ideas

- 模型结构应与 Phase 3 的 TUI 分步向导自然对齐——每个子模型对应向导的一个 Screen
- 现有 config.json 的字段命名可以在 Pydantic model 中使用更规范的名称，通过 `Field(alias=...)` 保持 TOML 可读性

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_load_config()` 函数：理解现有配置加载逻辑，可作为迁移参考
- `config.example.json`：完整的字段清单和默认值参考
- `EmailAdapter` 适配器模式：已验证的邮箱平台抽象，配置模型可对齐

### Established Patterns
- 配置优先级：CLI 参数 > 环境变量 > config.json（新模型需保持类似层级）
- 模块级 UPPER_SNAKE_CASE 全局变量：需要收拢的 20+ 个变量位于 `chatgpt_register.py:414-435`
- 错误处理用中文终端输出，配置校验错误也应保持一致

### Integration Points
- `run_batch()` 和 `_register_one()`：当前消费全局变量的主要位置，Phase 2 将改为接受 RegisterConfig 参数
- `_build_cli_parser()`：CLI 参数定义，未来需与 Pydantic 模型字段对齐
- `pyproject.toml`：新增 Pydantic 依赖

</code_context>

<deferred>
## Deferred Ideas

None — 讨论保持在阶段范围内

</deferred>

---

*Phase: 01-config-foundation*
*Context gathered: 2026-03-07*
