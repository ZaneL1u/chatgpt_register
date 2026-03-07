# 项目研究综述

**项目：** ChatGPT Register TUI 配置向导
**领域：** 为现有 Python CLI 自动化工具集成 TUI 交互式配置向导 + TOML Profile 管理
**研究日期：** 2026-03-07
**整体置信度：** HIGH

## 执行摘要

本项目的核心任务是为一个已有的 ChatGPT 批量注册 CLI 工具（2000+ 行单文件）引入基于 Textual 的 TUI 配置向导和 TOML Profile 管理机制。研究结论明确：这不是一个"在现有代码上叠加 TUI"的任务，而是一次有纪律的分层重构——必须先完成模块拆分和全局状态收拢，才能安全地引入 TUI 层。试图跳过重构直接加 TUI 是最大的技术风险，会导致 async/sync 冲突、终端控制权争夺、以及不可测试的巨型文件。

推荐的技术路线清晰且有高置信度：Textual 8.x 作为 TUI 框架（用户明确指定，生态成熟），Pydantic 2.x 做配置校验，tomllib + tomli-w 处理 TOML 读写。架构上采用"TUI 仅生成配置"模式——Textual App 收集用户输入后退出，配置字典传递给现有的同步执行流程，已有的 Rich RuntimeDashboard 继续独立运行。这个设计完全避免了 Textual 事件循环与同步线程池的冲突，是成本最低、风险最小的集成方案。

关键风险集中在三个方面：（1）全局可变状态——当前 20+ 个模块级全局变量必须在任何新功能开发之前收拢为配置数据类；（2）TOML schema 设计——需要前瞻性地使用嵌套 table 和 schema_version，否则后续每次新增 provider 都是痛苦的迁移；（3）敏感信息处理——API key 和 bearer token 不能明文裸写入 TOML 文件，至少需要支持环境变量引用语法。

## 核心发现

### 推荐技术栈

技术选型置信度高，所有推荐库均经 PyPI 版本验证和官方文档确认。详见 [STACK.md](./STACK.md)。

**核心技术：**
- **Textual >=8.0.2：** TUI 主框架——Python TUI 生态事实标准（33.5K stars），底层基于项目已有的 Rich 依赖，Screen 栈系统天然支持多步向导
- **Pydantic >=2.10.0：** 配置校验——类型安全的配置建模，自动校验与清晰错误消息，替代散落各处的手动类型转换
- **tomllib（标准库）+ tomli-w >=2.2.0：** TOML 读写——零依赖读取（Python 3.11+），轻量写入；不需要 tomlkit 的风格保留能力
- **建议将 `requires-python` 提升至 >=3.11：** 消除 tomli 后备依赖，Python 3.10 将于 2026-10 EOL

**依赖变更：** 新增 textual、pydantic、tomli-w 三个核心依赖；移除 questionary（Textual 完全覆盖）；保留 rich（Textual 底层依赖 + RuntimeDashboard 继续使用）。

### 功能规划

功能优先级基于用户期望和依赖关系推导，详见 [FEATURES.md](./FEATURES.md)。

**必须有（Table Stakes）：**
- TOML 配置文件读写——一切 Profile 功能的地基
- 交互式邮箱平台选择 + 条件字段联动——核心配置流程
- 配置项表单输入 + 输入验证 + 即时错误提示——保证配置有效性
- 配置确认摘要页——防误操作的安全网
- Profile 保存与加载——"配置一次，反复使用"
- 敏感字段掩码输入——bearer token 等必须掩码
- 非交互模式兼容（`--profile` / `--non-interactive`）——CI/CD 必须支持

**应该有（差异化）：**
- Profile 列表与快速选择——多 Profile 管理入口
- 混合启动模式——首次走向导，后续走快选
- 分步向导（多屏 Wizard）——降低认知负荷
- Profile 复制与派生——基于已有配置创建变体
- 运行时 Dashboard 集成——配置确认后无缝过渡到执行

**延后到 v2+：**
- Profile 预览与编辑——依赖完整向导流程
- Dry Run 模式——有价值但非核心
- 配置导出/导入（脱敏）——团队场景补充
- 配置差异对比——锦上添花

### 架构方案

采用"TUI-as-Config-Generator"模式，TUI 与执行层严格分离。详见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

**核心组件：**
1. **CLI 解析器（argparse）** —— 命令行入口，支持 `--profile` / `--non-interactive` 快捷路径
2. **TUI 向导（Textual App）** —— 多 Screen 配置向导，通过 `App.exit(result)` 返回配置字典
3. **ProfileManager** —— TOML Profile 的 CRUD、校验、路径管理，是 TUI 和 CLI 的共享配置层
4. **RegisterConfig 数据类（Pydantic）** —— 配置字段的 Single Source of Truth，取代 20+ 个全局变量
5. **执行层（run_batch + RuntimeDashboard）** —— 保持现有同步+线程池模型不变

**关键架构决策：** Textual `App.run()` 是阻塞调用，返回后终端恢复正常——"先 TUI 后执行"的串行模式天然可行，无需重写执行层。

### 关键陷阱

研究发现 5 个严重陷阱和 6 个中/轻度陷阱，详见 [PITFALLS.md](./PITFALLS.md)。

1. **Textual async 与同步注册流程冲突** —— 避免方式：TUI 只管配置收集，注册在 TUI 退出后运行，两者串行不并行
2. **全局可变状态阻碍模块拆分** —— 避免方式：先将 20+ 全局变量收拢为 RegisterConfig 数据类，通过参数传递，再做任何其他工作
3. **在 2000+ 行单文件上直接叠加 TUI** —— 避免方式：先拆分模块（config/、adapters/、core/、tui/），后集成 TUI
4. **Rich Live 与 Textual 终端控制权冲突** —— 避免方式：两者串行运行，TUI 退出后 Rich Dashboard 接管
5. **TOML schema 不向前兼容** —— 避免方式：使用嵌套 table 组织 provider 配置，加入 schema_version 字段

## 路线图建议

基于组件依赖关系和陷阱预防要求，建议分 5 个阶段推进。

### 阶段 1: 配置层基础（Schema + ProfileManager）

**理由：** 配置数据类是所有后续工作的基石。不先定义 RegisterConfig 和 TOML schema，TUI 不知道渲染什么字段，CLI 不知道传递什么参数，Profile 不知道存什么内容。架构研究和陷阱研究都强烈要求"schema 先行"。

**交付物：**
- RegisterConfig Pydantic 模型（所有配置字段的 Single Source of Truth）
- TOML schema 设计（嵌套 table，含 schema_version）
- ProfileManager 类（CRUD、校验、路径管理）
- 单元测试覆盖配置读写和校验

**涉及功能：** TOML 配置文件读写、Profile 保存与加载
**需规避陷阱：** TOML schema 不兼容（陷阱 5）、类型不匹配（陷阱 7）、路径权限问题（陷阱 8）、敏感信息处理（陷阱 9）

### 阶段 2: 模块拆分（单文件 -> 包结构）

**理由：** 当前 2000+ 行单文件中的全局变量是集成 TUI 的最大技术障碍。必须在 TUI 开发之前完成拆分，让 `run_batch()` 接受 RegisterConfig 参数而非依赖全局变量。这是陷阱研究中恢复代价标记为 HIGH 的问题。

**交付物：**
- 包化目录结构（config/、core/、adapters/、upload/）
- 全局变量消除（`grep 'global ' *.py` 返回 0）
- `run_batch()` 接受 RegisterConfig 实例作为参数
- 现有功能完全保持，通过集成测试验证

**涉及功能：** 非交互模式兼容（`--profile` 加载）
**需规避陷阱：** 全局可变状态（陷阱 2）、单文件膨胀（陷阱 3）

### 阶段 3: TUI 向导（Textual 多屏配置流程）

**理由：** 模块拆分完成后，有明确的数据接口（RegisterConfig）和存储接口（ProfileManager），TUI 开发可以高效进行。

**交付物：**
- Textual App 主类 + TCSS 样式
- 多步向导 Screen（邮箱提供者 -> 注册参数 -> 上传目标 -> 确认摘要）
- 条件字段联动（不同 provider 展示不同字段）
- 输入验证与即时错误提示
- 掩码输入（敏感字段）
- Textual pilot 测试覆盖完整配置流程

**涉及功能：** 交互式邮箱选择、条件联动、表单输入、输入验证、敏感字段掩码、配置确认摘要
**需规避陷阱：** async/sync 冲突（陷阱 1）、Rich/Textual 终端冲突（陷阱 4）、TUI 测试缺失（陷阱 10）

### 阶段 4: CLI 集成与迁移

**理由：** TUI 向导和配置层就绪后，重写 CLI 入口将所有组件串联。同时处理 questionary 移除和 config.json 迁移。

**交付物：**
- CLI 入口重写（argparse + TUI + Profile 集成）
- 混合启动模式（有 profile -> 快选，无 -> 向导）
- `--profile <name>` / `--non-interactive` 快捷路径
- questionary 完全移除
- config.json -> TOML 自动迁移工具
- 端到端测试（TUI 配置 -> 确认 -> 执行 -> Dashboard）

**涉及功能：** Profile 列表与选择、混合启动模式、非交互模式、运行时 Dashboard 集成
**需规避陷阱：** questionary 残留（陷阱 6）、config.json 迁移缺失（陷阱 11）

### 阶段 5: 体验增强

**理由：** 核心流程稳定后，逐步增加差异化功能提升用户体验。

**交付物：**
- Profile 复制与派生
- Profile 删除确认
- 快捷键支持
- 配置导出/导入（脱敏）
- Dry Run 模式（连通性检查）

**涉及功能：** 差异化功能列表中的非核心项
**需规避陷阱：** UX 陷阱（步骤过多、缺少预览）

### 阶段排序理由

- **阶段 1 -> 2 必须先于 3：** 架构研究和陷阱研究一致指出，不解决全局状态和模块拆分就开始 TUI 开发是"永远不可接受"的技术债
- **阶段 1 先于 2：** ProfileManager 需要 RegisterConfig schema 作为基础，schema 定义字段就是定义接口
- **阶段 3 先于 4：** TUI 向导是独立可测试的组件，CLI 集成是最终的串联步骤
- **阶段 5 延后：** 差异化功能对核心流程无阻塞依赖，可根据用户反馈调整优先级

### 研究标记

**需要深入研究的阶段：**
- **阶段 3（TUI 向导）：** Textual Screen 间状态传递、条件字段联动的具体实现模式需要参考官方示例验证
- **阶段 4（CLI 集成）：** config.json 到 TOML 的字段映射需要逐一确认现有配置的所有 edge case

**已有成熟模式的阶段（可跳过深入研究）：**
- **阶段 1（配置层）：** Pydantic BaseModel + tomllib/tomli-w 组合有充足的文档和社区实践
- **阶段 2（模块拆分）：** 标准 Python 包化重构，无特殊技术挑战

## 置信度评估

| 领域 | 置信度 | 说明 |
|------|--------|------|
| 技术栈 | HIGH | 所有库版本经 PyPI 验证，官方文档确认功能集，Textual 社区活跃 |
| 功能规划 | HIGH | 基于项目现有 config.json 实际分析 + CLI 工具领域最佳实践 |
| 架构方案 | HIGH | "TUI 仅生成配置"模式经 Textual 官方文档验证，App.exit(result) API 确认可行 |
| 陷阱预防 | HIGH | 大部分陷阱来自代码库实际分析和 Textual 官方文档/GitHub Discussion |

**整体置信度：** HIGH

### 待解决的空白

- **Python 最低版本决策：** 研究建议提升至 3.11（获得 tomllib 标准库支持，3.10 接近 EOL），但需要确认是否有用户群体仍在使用 3.10，这是一个产品决策
- **敏感信息存储方案细节：** 环境变量引用语法（`${ENV_VAR}`）的具体实现需要在阶段 1 中详细设计，涉及 Pydantic validator 的自定义逻辑
- **Sub2API group 选择时机：** 是在 TUI 配置阶段完成还是延迟到执行阶段动态拉取，取决于 Sub2API 的 API 响应速度和可用性

## 来源

### 高置信度（官方文档 / PyPI 验证）
- [Textual PyPI](https://pypi.org/project/textual/) — v8.0.2, 2026-03-03
- [Textual 官方文档](https://textual.textualize.io/) — Screen 系统、Widget 库、Workers、App.exit() API
- [Textual GitHub](https://github.com/Textualize/textual) — 33.5K stars
- [Python tomllib 标准库文档](https://docs.python.org/3/library/tomllib.html)
- [Pydantic 官方文档](https://docs.pydantic.dev/)
- [platformdirs PyPI](https://pypi.org/project/platformdirs/) — v4.9.4
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) — v2.13.1（评估后不采用）
- [tomlkit PyPI](https://pypi.org/project/tomlkit/) — v0.14.0（评估后不采用）
- [AWS CLI 配置模式](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) — Profile 管理参考
- 项目代码库实际分析 — 全局状态、配置加载、线程模型

### 中等置信度（社区实践 / 教程）
- [Textual GitHub Discussion #1828](https://github.com/Textualize/textual/discussions/1828) — 同步代码集成
- [Real Python - Python Textual](https://realpython.com/python-textual/) — TUI 最佳实践
- [Real Python - Python TOML](https://realpython.com/python-toml/) — tomllib vs tomlkit 对比
- [CLI UX 模式参考](https://lucasfcosta.com/2022/06/01/ux-patterns-cli-tools.html)
- [Command Line Interface Guidelines](https://clig.dev/)
- [Temporal CLI TOML Profile 模式](https://docs.temporal.io/develop/environment-configuration)

### 低置信度（评估后排除）
- [textual-wizard 第三方库](https://github.com/SkwalExe/textual-wizard) — 功能不足，决定不采用

---
*研究完成: 2026-03-07*
*路线图就绪: 是*
