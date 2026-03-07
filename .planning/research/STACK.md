# 技术栈推荐

**项目：** ChatGPT Register TUI 配置向导
**研究日期：** 2026-03-07
**整体置信度：** HIGH

## 推荐技术栈

### TUI 框架

| 技术 | 版本 | 用途 | 选择理由 |
|------|------|------|----------|
| Textual | >=8.0.2 | TUI 交互式配置向导主框架 | 用户明确指定；Python TUI 生态事实标准（GitHub 33.5K stars）；底层基于 Rich（项目已有依赖）；内置 Screen 栈系统天然支持多步向导模式；CSS-like 布局引擎适合表单界面；async 架构与未来扩展兼容；MIT 协议；活跃维护（2026年3月仍在频繁发版） |
| textual-dev | >=1.7.0 | 开发期调试工具（console、devtools） | Textual 官方配套，提供实时 CSS 热重载、DOM 检查器、事件追踪，大幅提升 TUI 开发效率 |

**置信度：** HIGH -- PyPI 已验证版本号，官方文档确认功能集

### 配置格式与解析

| 技术 | 版本 | 用途 | 选择理由 |
|------|------|------|----------|
| tomllib（标准库） | Python 3.11+ 内置 | TOML 配置读取 | 零依赖；PEP 680 标准化；项目要求 Python 3.10+，但建议将最低版本提升至 3.11（3.10 已接近 EOL 2026-10） |
| tomli | >=2.4.0 | TOML 读取后备（若保留 3.10 支持） | tomllib 的 PyPI 后备版本；mypyc 编译性能优于标准库；仅在需要 3.10 兼容时才引入 |
| tomli-w | >=2.2.0 | TOML 写入（保存 profile 配置） | 轻量 TOML writer；与 tomllib/tomli 配套；输出格式规范干净 |

**为什么不用 tomlkit？** tomlkit (0.14.0) 的核心优势是"保留注释和格式"的风格感知往返编辑。本项目的 profile 文件由程序生成和管理，用户无需手动编辑，因此不需要保留注释。tomli + tomli-w 组合更轻量、解析更快，是更合适的选择。

**置信度：** HIGH -- Python 官方文档、PyPI 已验证

### 配置校验

| 技术 | 版本 | 用途 | 选择理由 |
|------|------|------|----------|
| Pydantic | >=2.10.0 | 配置数据模型定义与校验 | 类型安全的配置建模；自动校验与类型转换；清晰的错误消息帮助用户定位配置问题；与 TOML 数据结构无缝映射；Python 生态最成熟的数据校验库 |

**为什么不用 pydantic-settings？** pydantic-settings (2.13.1) 主要解决"从多源（环境变量、.env、TOML）加载配置"的问题。本项目的配置来源单一（TUI 交互 -> TOML profile），不需要多源合并逻辑。直接用 Pydantic BaseModel + tomllib 读取更简单透明，避免引入不必要的抽象层。

**置信度：** HIGH -- Pydantic 官方文档验证

### 文件系统路径管理

| 技术 | 版本 | 用途 | 选择理由 |
|------|------|------|----------|
| platformdirs | >=4.9.0 | 跨平台配置目录解析 | appdirs 的官方继任者（appdirs 已废弃）；pip 等核心工具已迁移至此；遵循 XDG 规范（Linux）和各平台原生约定（macOS/Windows）；提供 user_config_dir、user_data_dir 等标准路径 |

**注意：** PROJECT.md 指定默认路径为 `~/.chatgpt-register/profiles/`。建议保留此硬编码路径作为默认值以保持项目一致性，但用 platformdirs 作为备选方案（或未来迁移路径）。初始阶段可直接用 `Path.home() / ".chatgpt-register"` 实现。

**置信度：** HIGH -- PyPI 验证，pip 项目已采用

### 现有依赖处理

| 技术 | 当前状态 | TUI 阶段处理方式 |
|------|----------|-----------------|
| questionary 2.1.1 | 现有依赖，简单交互选择 | **移除** -- Textual 完全覆盖其功能且体验更好；保留会导致两套交互系统共存 |
| rich 14.3.3 | 现有依赖，运行时面板 | **保留** -- Textual 底层依赖 Rich；运行时面板（RuntimeDashboard）继续使用 Rich；两者可共存 |
| curl-cffi 0.7.0 | 核心 HTTP 客户端 | **不动** -- 注册流程核心，与 TUI 层无关 |

## 完整新增依赖清单

```bash
# 核心依赖（添加到 pyproject.toml [project].dependencies）
uv add textual ">=8.0.2"
uv add pydantic ">=2.10.0"
uv add tomli-w ">=2.2.0"

# 可选：如需保留 Python 3.10 支持
uv add tomli ">=2.4.0"

# 开发依赖
uv add --dev textual-dev ">=1.7.0"

# 移除旧依赖
uv remove questionary
```

### pyproject.toml 修改要点

```toml
[project]
requires-python = ">=3.11"  # 建议提升，获得 tomllib 标准库支持
dependencies = [
  "curl-cffi>=0.7.0",
  "rich>=13.7.0",
  "textual>=8.0.2",
  "pydantic>=2.10.0",
  "tomli-w>=2.2.0",
]

[project.optional-dependencies]
dev = ["textual-dev>=1.7.0"]
```

## 未选用方案及理由

| 类别 | 推荐方案 | 备选方案 | 未选择原因 |
|------|----------|----------|------------|
| TUI 框架 | Textual | questionary | questionary 只能做线性问答，无法构建复杂 TUI 界面；用户已明确选择 Textual |
| TUI 框架 | Textual | prompt_toolkit | 底层库，需大量手写 UI 代码；Textual 已封装为高层框架 |
| TUI 框架 | Textual | urwid | 过时的 API 设计（curses 封装）；社区活跃度远低于 Textual |
| TOML 读取 | tomllib + tomli | toml（旧库） | toml 库已停止维护，不支持 TOML v1.0 完整规范 |
| TOML 读写 | tomli + tomli-w | tomlkit | 本项目不需要风格保留往返编辑，tomlkit 性能更差且 API 更复杂 |
| 配置校验 | Pydantic BaseModel | dataclasses | dataclasses 无内置校验；类型检查需额外代码；错误消息需手动构建 |
| 配置校验 | Pydantic BaseModel | attrs | Pydantic 在 Python 生态更主流，文档更丰富，JSON Schema 生成等高级功能更完善 |
| 配置校验 | Pydantic BaseModel | pydantic-settings | 本项目配置来源单一，不需要多源合并；直接 BaseModel 更简单 |
| 配置校验 | Pydantic BaseModel | marshmallow | Pydantic v2 性能更好，类型注解更 Pythonic |
| 路径管理 | Path.home() 硬编码 | platformdirs | 初期按 PROJECT.md 硬编码 `~/.chatgpt-register/` 即可，platformdirs 作为未来优化方向 |

## 版本兼容性矩阵

| 组件 | Python 3.10 | Python 3.11 | Python 3.12+ |
|------|-------------|-------------|--------------|
| Textual 8.x | 支持 | 支持 | 支持 |
| tomllib | 不可用（需 tomli） | 可用 | 可用 |
| Pydantic 2.x | 支持 | 支持 | 支持 |
| tomli-w | 支持 | 支持 | 支持 |

**建议：** 将 `requires-python` 提升至 `>=3.11`，消除 tomli 后备依赖的必要性，简化代码路径。Python 3.10 将于 2026 年 10 月 EOL。

## 来源

- [Textual PyPI](https://pypi.org/project/textual/) -- v8.0.2, 2026-03-03 发布 (HIGH)
- [Textual 官方文档](https://textual.textualize.io/) -- Screen 系统、Widget 库 (HIGH)
- [Textual GitHub](https://github.com/Textualize/textual) -- 33.5K stars, 活跃维护 (HIGH)
- [Python tomllib 官方文档](https://docs.python.org/3/library/tomllib.html) -- 标准库 (HIGH)
- [tomlkit PyPI](https://pypi.org/project/tomlkit/) -- v0.14.0, 2026-01-13 (HIGH)
- [tomli PyPI](https://pypi.org/project/tomli/) -- v2.4.0+ (HIGH)
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) -- v2.13.1, 2026-02-19 (HIGH)
- [Pydantic 官方文档 - Settings Management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) (HIGH)
- [platformdirs PyPI](https://pypi.org/project/platformdirs/) -- v4.9.4, 2026-03-05 (HIGH)
- [platformdirs GitHub](https://github.com/tox-dev/platformdirs) -- appdirs 官方继任 (HIGH)
- [Real Python - Python TOML](https://realpython.com/python-toml/) -- tomllib vs tomlkit 对比 (MEDIUM)
- [Real Python - Python Textual](https://realpython.com/python-textual/) -- TUI 最佳实践 (MEDIUM)
