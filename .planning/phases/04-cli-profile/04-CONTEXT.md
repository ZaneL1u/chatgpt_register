# Phase 4: CLI 集成与 Profile 管理 - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

> 本文件基于 `$gsd-discuss-phase 4 --auto` 自动收敛：未再向用户追问，而是按路线图、既有阶段决策、当前代码现状与已知陷阱，为剩余灰区锁定默认方案。

<domain>
## 阶段边界

将现有 Textual 向导、`ProfileManager` 与 `chatgpt-register` CLI 入口完整串联，使 TOML profile 成为唯一配置入口。交互式启动时，如果已有 profile，则优先进入 profile 选择；如果没有，则直接进入向导。支持 `--profile <name>` 直接加载并执行，支持基于已有 profile 派生新配置，并完全移除主 CLI 对 `config.json`、环境变量覆盖和 `input()` / `questionary` 式配置收集的依赖。

不包含：旧 `config.json` 自动迁移工具、profile 删除/重命名、配置加密存储、Dry Run、profile 差异对比。

</domain>

<decisions>
## 实现决策

### 启动入口与模式切换
- `--profile <name>` 是最高优先级入口：提供后直接加载指定 profile 并执行，不再进入 profile 列表或向导。
- 只有在交互式 TTY 且未显式指定 `--profile` 时，CLI 才进入交互流程；此时“有 profile 先选 profile，无 profile 直达向导”是默认路由。
- `--non-interactive` 模式下不允许再出现任何补问；如果未提供 `--profile`，应直接失败并给出明确中文提示，而不是退回旧 `input()` 逻辑。
- 交互式流程完成后，CLI 统一拿到 `RegisterConfig` 再调用 `run_batch(config)`；运行阶段不再回头补采配置。

### Profile 列表呈现与可选动作
- Profile 选择界面采用“快速选择优先”的紧凑列表，不做复杂管理台。
- 每个 profile 至少展示：名称、邮箱平台、上传目标、注册数量、并发数；这些信息直接出现在列表项的副文案中，不要求单独的详情页才能判断。
- 列表默认按 profile 名称稳定排序，保证可预测；本阶段不引入“最近使用”“收藏”等额外排序语义。
- 在有 profile 的交互入口中，用户可执行三类主动作：直接运行选中 profile、基于选中 profile 派生新配置、创建全新配置；删除/重命名不进入本阶段。

### 基于已有 Profile 的派生流程
- “复制派生”不会原地修改源 profile，而是始终生成一份新的配置草稿。
- 派生流程复用 Phase 3 已完成的向导与摘要页能力：以选中 profile 预填 `WizardState`，但仍从第一步进入，保持“线性前进、最终在摘要页统一回改”的既有交互原则。
- 新 profile 的名称在最终保存时单独确认；若名称冲突，应要求用户显式更换名称，不默认覆盖原 profile。
- 用户取消派生流程时，原 profile 保持不变，不产生半成品文件。

### 非交互完整性与 Sub2API 补全策略
- 非交互路径加载 profile 后必须具备可直接执行的完整配置；不允许在执行前再弹出额外交互来补齐缺失项。
- Sub2API 分组选择属于“配置完成”的一部分，而不是“运行时再问”的一部分；交互式创建/派生 profile 时就应把最终 `group_ids` 固化进 profile。
- 如果用户通过 `--profile` 加载的 profile 缺少执行所需的 Sub2API 绑定信息，CLI 应失败并提示用户回到交互式配置流程修复，而不是回退到 `questionary` 或 `input()`。
- 交互式快捷运行已保存 profile 时，也应默认信任 profile 内已有配置；除非配置校验失败，否则不要在执行前追加“确认这个、补那个”的分叉流程。

### 旧配置方式的退场策略
- 主 CLI 完全停止读取 `config.json`，也不再接受“环境变量覆盖配置模型”的旧优先级链路。
- 仓库中的 `config.example.json`、README 中的旧教程、以及依赖中的 `questionary` 均视为本阶段需要清理的遗留物。
- 如果用户工作目录中仍存在 `config.json`，CLI 只给出明确告知：该方式已废弃；请使用 TOML profile 或交互式向导。不会自动加载，也不会静默忽略后继续沿用旧行为。
- 任何旧路径的报错都应是可操作的中文文案，帮助用户迁移到“TUI / TOML 是唯一入口”的新模型。

### Claude's Discretion
- Profile 选择界面是单独 `Screen`、独立小型 `App`，还是并入现有 `WizardApp` 前置入口。
- Profile 列表项的具体视觉样式（两行摘要、表格式、卡片式）与快捷键设计。
- Profile 名称输入是在派生末尾单独弹窗、摘要页内联字段，还是独立保存步骤。
- 是否为 `ProfileManager` 增加“读取摘要元信息”的辅助 API，或在 UI 层按需加载 `RegisterConfig` 后即时拼装摘要。

</decisions>

<specifics>
## 具体想法

- Phase 4 的核心不是“再做一个新 TUI”，而是把“选 profile / 新建 / 派生 / 运行”这四条路径收口成一个可预测的 CLI 启动体验。
- 交互式用户进入后应尽快看到可运行的 profile，而不是再经历一轮 `input()` 式问答。
- 已有 profile 的派生必须尽量复用现成向导状态灌入能力，避免维护第二套编辑器。
- “不再有运行时补问”是本阶段最关键的行为边界之一，尤其适用于 `--profile` 与未来自动化场景。
- 对旧 `config.json` 的态度要明确：给清晰出路，但不继续兼容。

</specifics>

<code_context>
## 现有代码洞察

### 可复用资产
- `chatgpt_register/config/profile.py` 已具备 `save()`、`load()`、`list_profiles()`、`exists()`、`delete()` 基础能力，足以支撑 Phase 4 的列表、加载和“读取后另存为”派生路径。
- `chatgpt_register/tui/app.py` 的 `WizardApp(initial_config_dict=...)` 已支持从初始配置灌入向导状态，可直接作为“基于已有 profile 派生”的承载入口。
- `chatgpt_register/tui/state.py` 的 `WizardState.from_config_dict()` 已支持从配置字典恢复邮箱、注册参数、上传目标和 OAuth 草稿，并保留未选中分支的数据。
- `chatgpt_register/tui/screens/summary.py` 已实现最终摘要页原地编辑和即时校验，适合作为派生流程的最后确认与保存前检查点。
- `tests/test_cli_tui.py` 与 `tests/test_profile_manager.py` 已覆盖 CLI→TUI 基本路由和 ProfileManager 持久化，可扩展为 Phase 4 的首批回归测试基础。

### 已建立的模式
- Phase 3 已锁定“只能线性前进，不能回头，最终在摘要页统一修改”的交互规则；Phase 4 的派生能力必须服从这一规则，不能引入任意跳转式编辑体验。
- 项目当前统一以 `RegisterConfig` 作为执行入口数据结构；CLI 最终仍应收口到 `run_batch(config)`，不要重新发明平行配置对象。
- 当前 `chatgpt_register/cli.py` 仍保留 `_load_legacy_config()`、环境变量覆盖、`input()` 补问与 `_apply_cli_overrides()` 的旧链路；这是 Phase 4 的主要清理对象。
- 当前 `chatgpt_register/upload/sub2api.py` 仍含 `questionary` 与 `input()` 分支，说明“运行时补齐 Sub2API 配置”的旧思路尚未完全退出。
- `ProfileManager.list_profiles()` 目前仅返回名称列表，尚未提供摘要信息或最近修改时间，这会直接影响 profile 列表 UI 的数据获取方式。

### 集成点
- `chatgpt_register/cli.py` 是 Phase 4 的总路由入口：需要在这里统一交互式启动、`--profile` 快速路径、非交互失败策略与遗留逻辑退场。
- `chatgpt_register/config/profile.py` 是 profile 读写与名称合法性约束中心，后续如需派生保存、摘要提取或覆盖保护，优先在这里补齐配套 API。
- `chatgpt_register/tui/` 目录是新增 profile 选择/派生入口的自然落点；应与已有 `WizardApp`、`Screen` 模式保持一致，避免再起一套命令行菜单系统。
- `README.md`、`pyproject.toml`、`uv.lock` 与 `config.example.json` 体现了旧配置方式仍暴露在对外表面；Phase 4 需要同步清理文档和依赖层，避免功能已切换但对外说明仍误导用户。

</code_context>

<deferred>
## 延迟想法

- `config.json` 自动迁移工具属于 `EXP-05`，是独立增强项；本阶段只负责停止兼容旧格式，不负责提供完整迁移器。
- Profile 删除、重命名、最近使用、收藏、搜索过滤等管理增强，不纳入本阶段。
- TOML 中的密钥环境变量引用、文件权限加固、显示敏感信息的额外开关，属于后续安全/体验增强议题。
- Profile 差异预览、临时编辑后不落盘运行、Dry Run 等属于后续体验增强阶段。

</deferred>

---

*Phase: 04-cli-profile*
*Context gathered: 2026-03-08*
