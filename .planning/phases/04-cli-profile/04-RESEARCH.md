# Phase 4: CLI 集成与 Profile 管理 - 研究

**研究日期:** 2026-03-08
**领域:** Profile 生命周期、CLI 启动分流、Textual 启动页、遗留配置退场
**置信度:** HIGH

<user_constraints>
## 用户约束 (来自 CONTEXT.md)

### 锁定决策
- 启动时如果存在已保存 profile，交互式入口优先展示 profile 列表，而不是直接进入邮箱配置第一页。
- Profile 列表必须显示名称与摘要信息，帮助用户直接判断“跑哪个”。
- `--profile <name>` 是唯一的非交互启动路径；加载后应直接运行，不再补问字段。
- 已有 profile 的派生必须复用现有 `WizardState` 初始灌入能力，不维护第二套编辑器。
- 派生流程必须保持 Phase 3 已锁定的线性向导规则：从第一步开始走，最终仅在摘要页统一确认。
- 派生流程取消时不得改写原 profile，也不能产生半成品 TOML 文件。
- Sub2API 分组选择属于配置完成的一部分；交互式创建/派生 profile 时就要把最终 `group_ids` 固化进 profile。
- 主 CLI 不再读取 `config.json`，也不再接受“环境变量覆盖配置模型”的旧优先级链路。
- 如果用户当前目录仍有 `config.json`，CLI 只能给出明确迁移提示，不能继续沿用旧逻辑。
- 所有遗留路径的报错都应是可操作的中文文案。

### Claude 自主裁量
- Profile 启动页是独立 `Screen`、`ModalScreen`，还是并入 `WizardApp` 的前置入口。
- Profile 摘要展示用两行列表、表格还是卡片。
- 新建/派生时 profile 名称输入落在摘要页、单独保存弹窗，还是保存步骤。
- Profile 摘要接口是扩展 `ProfileManager`，还是新增只读 helper。

### 延迟事项
- Profile 删除、重命名、收藏、最近使用、搜索过滤不在本阶段。
- `config.json` 自动迁移工具属于 `EXP-05`，本阶段只负责停用旧格式。
- 临时编辑后不落盘运行、Profile 差异预览、Dry Run 属于后续体验增强。
</user_constraints>

<phase_requirements>
## 阶段需求

| ID | 描述 | 研究支撑 |
|----|------|----------|
| PROF-01 | 有 profile 时先显示列表，无 profile 时直接进向导 | 启动页分流、空列表回退规则 |
| PROF-02 | 列表展示名称 + 摘要信息 | `ProfileManager` 摘要接口 / 轻量读取策略 |
| PROF-03 | 支持 `--profile <name>` 直接运行 | CLI 入口收口、非交互失败策略 |
| PROF-04 | 支持基于已有 profile 复制派生新配置 | `WizardState.from_config_dict()` 预填、摘要页保存流程 |
| CONF-05 | 移除 `config.json`，TUI + TOML 是唯一入口 | 旧 CLI/环境变量/`questionary` 退场清单 |
</phase_requirements>

## 概要

Phase 4 的本质不是“给 CLI 再加一点参数”，而是把整个启动链路改成 **Profile-first**：

1. **交互式入口**：先看 profile 列表；无 profile 则直接进入向导。
2. **派生入口**：把现有 profile 灌入 `WizardState`，再按既有线性步骤重新确认。
3. **非交互入口**：只接受 `--profile`，加载后直接 `run_batch(config)`。
4. **运行前校验**：Profile 必须已经完整，包括 Sub2API 的 `group_ids`；运行阶段不再补问。
5. **遗留清理**：停止读取 `config.json`、停止环境变量覆盖、移除 `questionary` 依赖和 README 中的旧教程。

现有代码已经具备三个关键资产：

- `ProfileManager` 已完成 TOML 的 save/load/list/delete 基础仓储。
- `WizardApp(initial_config_dict=...)` 已能从既有配置灌入草稿状态。
- `UploadScreen` 已能获取 Sub2API 分组并把 `selected_group_id/group_ids` 写回 `WizardState`。

因此，本阶段不需要重做配置模型，只需把 **profile 元信息、TUI 启动分流、CLI 路由收口、遗留退场** 四条线接起来。

## Standard Stack

### 继续采用

| 组件 | 位置 | 用途 | 结论 |
|------|------|------|------|
| `argparse` | `chatgpt_register/cli.py` | CLI 模式分流与 `--profile` 参数 | 继续采用 |
| `ProfileManager` | `chatgpt_register/config/profile.py` | Profile 仓储与摘要来源 | 扩展能力 |
| `WizardApp` / `Screen` | `chatgpt_register/tui/` | 交互式 profile 入口与派生编辑 | 继续采用 |
| `RegisterConfig` | `chatgpt_register/config/model.py` | Profile 加载后最终执行输入 | 继续采用 |
| `fetch_sub2api_openai_groups()` | `chatgpt_register/upload/sub2api.py` | 交互式配置阶段加载分组 | 保留底层 API |

### 应移除

| 项 | 现状 | 结论 |
|----|------|------|
| `questionary` | 仅剩 Sub2API 运行时选择分组在用 | Phase 4 移除 |
| `config.json` 加载链路 | `cli.py` 仍会读取当前目录 `config.json` | Phase 4 停用 |
| 环境变量覆盖配置 | `cli.py` 仍把环境变量合并到 legacy dict | Phase 4 停用 |
| 运行时 `input()` 补问 | 代理、数量、并发、Sub2API 凭证/分组仍在 CLI 里询问 | Phase 4 停用 |

## Architecture Patterns

### 模式 1: `ProfileManager` 提供“摘要视图”，不把列表拼装逻辑散落在 UI/CLI

**结论:** 在 `chatgpt_register/config/profile.py` 中补一个只读摘要接口，例如 `list_profile_summaries()`，返回名称、路径、邮箱平台、上传目标、账号数、并发数、更新时间等元信息。

**原因:**
- `list_profiles()` 只返回名称，无法支撑 `PROF-02`。
- TUI 启动页和未来 CLI 子命令都需要同一份摘要数据。
- 摘要逻辑放仓储层最稳定，避免 UI 自己遍历 TOML 再拼字符串。

**约束:**
- 保留 `list_profiles()` 兼容现有调用。
- 名称合法性校验应扩展到 `load()`、`exists()`、`delete()`，保证 CLI 输入的一致性与路径安全。

### 模式 2: 在 `WizardApp` 内增加前置 Profile 启动页，而不是再造第二个入口程序

**结论:** 保持 `WizardApp` 作为唯一交互式壳层；当存在 profile 且没有显式初始配置时，先进入 `ProfileSelectScreen`，否则仍从 `email` 步骤开始。

**原因:**
- 现有 `WizardApp` 已统一了退出确认、Screen 安装和 `RegisterConfig | None` 返回契约。
- 若再起一个“profile launcher app”，退出语义、测试方式和结果回传都要再维护一套。
- 将 profile 入口做成命名 Screen，能复用 Textual 的既有测试模式和样式约定。

### 模式 3: 新建/派生在摘要页前保存，保存动作只写最终确认态

**结论:** 新建和派生都应在摘要页点击执行前，经过一次“保存 profile 名称”确认；只有保存成功后，CLI 才拿到最终 `RegisterConfig` 并开始执行。

**原因:**
- 这满足“Profile 是唯一配置入口”的要求：最终执行对应的就是落盘后的 TOML。
- 派生取消时不会污染原 profile；因为直到最后确认前都只在内存草稿中操作。
- 这不破坏 Phase 3 的线性向导规则：用户仍旧按四步走，只是在最后确认时补一个保存动作。

**推荐落点:**
- 新增 `SaveProfileScreen` 或 `SaveProfileModal`。
- `SummaryScreen` 负责触发保存，不直接做文件 I/O 细节。
- 名称重名时必须显式确认覆盖或要求新名称，不做静默覆盖。

### 模式 4: CLI 收口为“三段式”分流

**推荐顺序:**
1. 解析 `--profile`、`--profiles-dir`、`--non-interactive` 这类模式参数。
2. 构造 `ProfileManager` 并检测遗留 `config.json`。
3. 分流：
   - `--profile` → 加载 profile → 直接执行。
   - 交互式 TTY → 启动 `WizardApp(profile_manager=...)`。
   - 非交互且未给 `--profile` → 失败，并提示“请先在交互式流程创建 profile，再用 `--profile` 运行”。

**结论:** Phase 4 结束后，CLI 不再解析业务配置字段，例如 `--proxy`、`--upload-targets`、`--workers` 等；这些都属于 profile 内容本身，不应继续作为第二配置入口。

### 模式 5: Sub2API 只保留“拉组 API”与“执行上传 API”，去掉运行时选择器

**结论:** `fetch_sub2api_openai_groups()` 保留；`prepare_sub2api_group_binding()` 应重构为“验证已有 `group_ids`/选中组是否完整”的纯逻辑，或直接由 CLI 在加载 profile 后做静态校验。

**原因:**
- `questionary` 与 `input()` 已违背 “TUI/TOML 是唯一入口”。
- Phase 3 上传页已经能把用户选择的分组固化到 `WizardState`；Phase 4 只需确保这份数据被保存和复用。
- 非交互路径若 profile 缺组信息，应明确失败并指回交互式修复，而不是现场补问。

## Common Pitfalls

### 陷阱 1: 只在 TUI 层拼摘要，CLI 又重新读 TOML 做第二套摘要

**问题:** 这会造成摘要字段与排序规则漂移。

**结论:** 摘要生成逻辑集中到 `ProfileManager` 或同一只读 helper。

### 陷阱 2: 让 `WizardApp` 直接做文件读写和覆盖策略判断

**问题:** 会把 UI 壳层变成业务控制器，后续难测。

**结论:** App 只编排动作；Profile 仓储和名称/覆盖判断放到配置层或单独 helper。

### 陷阱 3: 派生时直接跳到摘要页

**问题:** 这违背 Phase 3 的“线性推进”约束，也会让用户错过前面步骤的页面级校验。

**结论:** 派生应从 `email` 步骤重新开始，但字段预填。

### 陷阱 4: `--profile` 仍允许用 `--proxy`、`--workers` 等参数二次覆盖

**问题:** 这会重新引入第二配置入口，直接破坏 `CONF-05`。

**结论:** Phase 4 只保留模式参数，不保留业务字段覆盖参数。

### 陷阱 5: 检测到 `config.json` 后仍悄悄忽略并继续执行

**问题:** 用户会误以为配置生效，迁移成本被隐藏。

**结论:** 必须打印清晰废弃提示；非交互场景应失败，交互场景可提示后进入新入口。

### 陷阱 6: 仍保留 `questionary` 作为 Sub2API 后备方案

**问题:** 只要留下这条链路，README、依赖和运行语义就无法真正收口。

**结论:** 运行阶段彻底移除 `questionary`。

## Validation Architecture

### 自动化验证主线

- Profile 仓储层：继续以 `tests/test_profile_manager.py` 为主，新增摘要接口、名称校验一致性、损坏 profile 的异常路径。
- TUI 启动与派生：新增 `tests/test_tui_profile_screen.py`，覆盖“有 profile 时先列表、无 profile 时直进向导、运行/派生/新建分流、保存后返回配置”。
- CLI 模式分流：新增 `tests/test_cli_profile_mode.py`，覆盖 `--profile` 直载、非交互无 profile 失败、检测 `config.json` 时的提示、`run_batch(config)` 调用。
- Sub2API 运行边界：新增 `tests/test_sub2api_group_binding.py` 或在 CLI 测试中覆盖“缺少 `group_ids` 明确失败、不再触发 `questionary`/`input()`”。

### 建议命令

- 快速反馈：`uv run pytest tests/test_profile_manager.py tests/test_tui_profile_screen.py tests/test_cli_profile_mode.py -q`
- 阶段全量：`uv run pytest tests/ -q`
- 文档/遗留扫描：`rg -n "config\.json|questionary|EMAIL_PROVIDER|SUB2API_GROUP_IDS" README.md pyproject.toml chatgpt_register tests`

### 通过标准

- 所有 Phase 4 requirement 都能映射到至少一个自动化测试命令。
- 不允许再出现运行时 `input()` / `questionary` 路径。
- `--profile` 路由和交互式 profile 启动页共用同一套 ProfileManager 仓储。
- README 与依赖清单不再把 `config.json` / `questionary` 描述为有效主路径。

---

*Phase: 04-cli-profile*
*Research completed: 2026-03-08*
