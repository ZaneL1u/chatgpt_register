# 功能全景

**领域:** TUI 配置向导 + Profile 管理（CLI 自动化工具场景）
**调研日期:** 2026-03-07

## 基线功能（Table Stakes）

缺少以下任何一项，用户会认为工具不完整或不可用。

| 功能 | 为什么必须有 | 复杂度 | 备注 |
|------|-------------|--------|------|
| 交互式邮箱平台选择 | 当前已有 questionary 实现，用户期望至少保持同等体验 | 低 | Textual 的 `Select` / `RadioSet` 直接替代 questionary |
| 配置项表单输入（账号数量、并发数、代理等） | 核心注册参数，无法跳过 | 中 | 需要为数值型字段提供 `Input` + `Integer` / `Number` 验证器 |
| 敏感字段掩码输入 | Bearer token、API key 等必须掩码显示 | 低 | Textual `Input(password=True)` 原生支持 |
| 配置确认摘要页 | 避免误操作，所有严肃 CLI 工具的标配（参考 `aws configure`、`npm init`） | 低 | 在执行前以只读表格/面板展示完整配置，含"确认 / 返回修改"操作 |
| TOML 配置文件读写 | 项目约束要求 TOML 替代 config.json | 中 | 写入用 `tomlkit`（保留注释），读取用 `tomllib`（Python 3.11 标准库） |
| Profile 保存与加载 | 多套配置是本次迭代核心需求 | 中 | 存储到 `~/.chatgpt-register/profiles/<name>.toml` |
| Profile 列表与选择 | 有保存的 profile 后，用户需要能快速选一个用 | 低 | Textual `OptionList` 或 `Select`，展示 profile 名 + 摘要信息 |
| 条件字段联动 | 选择不同邮箱平台后，只展示对应平台的配置项 | 中 | 例如选 `duckmail` 只出现 bearer token，选 `mailcow` 出现 IMAP 系列字段 |
| 上传目标选择与配置 | 当前支持 CPA / Sub2API / both / none | 中 | 多选复选框 + 条件展开对应配置字段 |
| 输入验证与即时错误提示 | 防止用户填错后到执行阶段才发现 | 中 | Textual 的 `validate_on` 机制支持 blur / change / submit 三种时机 |
| 非交互模式兼容 | CI/CD 场景和脚本化调用必须保留 | 中 | `--profile <name>` 直接加载 profile 跳过 TUI，`--non-interactive` 标志 |

## 差异化功能（Differentiators）

不是用户预期内的，但提供后会显著提升体验和竞争力。

| 功能 | 价值主张 | 复杂度 | 备注 |
|------|---------|--------|------|
| 混合启动模式 | 首次使用走完整向导，后续自动呈现 profile 快选列表 | 中 | 检测 `~/.chatgpt-register/profiles/` 是否有文件，有则展示选择+新建入口，无则直接进向导 |
| Profile 预览与编辑 | 选择已有 profile 时先展示摘要，允许临时修改再运行 | 高 | 类似 `aws configure` 的"显示当前值，回车保留"模式 |
| Profile 复制与派生 | 基于已有 profile 创建变体（如换一个邮箱提供者） | 低 | 复制 TOML 文件改名，在向导中预填字段 |
| Profile 删除确认 | 防止误删有价值的配置 | 低 | 二次确认弹窗 |
| 分步向导（多屏 Wizard） | 将配置拆成"邮箱 -> 注册参数 -> 上传 -> 确认"多步，降低认知负荷 | 高 | 用 Textual 的 Screen push/pop 实现步骤导航，带"上一步 / 下一步"按钮和步骤指示条 |
| 配置差异对比 | 修改 profile 时高亮显示与原始值的差异 | 中 | 在确认页用颜色标记变更项，类似 `git diff` 体验 |
| 配置导出/导入 | 允许分享 profile 给团队成员（脱敏后） | 低 | `--export-profile` / `--import-profile` 子命令，导出时自动清除 secret 字段 |
| 快捷键支持 | 高级用户可通过快捷键跳过步骤或快速操作 | 低 | Textual `Binding` 原生支持，如 `Ctrl+S` 保存、`Escape` 返回 |
| 运行时 Dashboard 集成 | 配置确认后无缝过渡到现有 Rich RuntimeDashboard | 中 | TUI 配置完成 -> 返回配置字典 -> 启动批处理 -> 切换到 Dashboard |
| Dry Run 模式 | 配置完成后只验证连通性，不真正注册 | 中 | 测试邮箱 API、代理可达性、上传目标可用性，给出检查报告 |

## 反功能（Anti-Features）

明确不应该构建的功能，避免范围膨胀或架构方向错误。

| 反功能 | 为什么不做 | 替代方案 |
|--------|-----------|---------|
| Web UI 配置界面 | 项目定位是本地 CLI 工具，Web UI 引入服务器组件，大幅增加复杂度 | Textual 本身支持 `textual serve` 浏览器模式，必要时可零成本开放 |
| 配置加密存储 | 增加实现复杂度，CLI 工具通常依赖文件系统权限而非自建加密 | 文件权限设为 600，文档提醒用户保护 profile 目录 |
| 图形化进度嵌入向导 | TUI 向导和运行时面板是两个不同的生命周期，强行合并会导致职责混乱 | 向导输出配置 -> 启动独立的 RuntimeDashboard |
| 多用户权限管理 | 单用户本地工具，无此需求 | 不做 |
| 配置历史版本控制 | 过度工程，TOML 文件本身适合 Git 追踪 | 文档建议用户将 profile 目录纳入版本控制 |
| 内置 TOML 编辑器 | Textual 虽有 TextArea 组件，但再造一个 TOML 编辑器意义不大 | 向导表单是结构化编辑的最佳方式；高级用户直接用文本编辑器改 TOML |
| 实时远程配置同步 | 超出 CLI 工具范畴 | 用户自行通过网盘或 Git 同步 profile 目录 |
| `textual-wizard` 第三方库依赖 | 该库（SkwalExe/textual-wizard）功能简单、维护活跃度不确定，且项目需要的定制化程度超出其抽象能力 | 直接基于 Textual 原生 Screen + Widget 构建自定义向导 |

## 功能依赖关系

```
TOML 配置文件读写 -> Profile 保存与加载 -> Profile 列表与选择 -> 混合启动模式
                                          -> Profile 预览与编辑
                                          -> Profile 复制与派生
                                          -> Profile 删除确认

交互式邮箱平台选择 -> 条件字段联动（选择平台后展示对应字段）

配置项表单输入 -> 输入验证与即时错误提示
              -> 配置确认摘要页 -> Dry Run 模式（可选）
                               -> 运行时 Dashboard 集成

分步向导（多屏 Wizard）-> 依赖以上所有表单类功能

非交互模式兼容 -> 依赖 Profile 加载（`--profile` 参数）
```

## MVP 建议

### 优先实现（Phase 1 核心）

1. **TOML 配置文件读写** -- 一切 profile 功能的地基
2. **交互式邮箱平台选择 + 条件字段联动** -- 核心配置流程
3. **配置项表单输入 + 输入验证** -- 保证配置有效性
4. **配置确认摘要页** -- 防误操作的安全网
5. **Profile 保存与加载** -- 实现"配置一次，反复使用"

### 优先实现（Phase 2 体验提升）

6. **Profile 列表与选择** -- 多 profile 管理入口
7. **混合启动模式** -- 智能判断首次/后续使用场景
8. **非交互模式兼容** -- CI/CD 和脚本化支持
9. **分步向导（多屏 Wizard）** -- 降低认知负荷

### 延后实现

- **Profile 预览与编辑**: 依赖完整的向导流程，在 MVP 后迭代
- **Dry Run 模式**: 有价值但非核心，可在运行稳定后加入
- **配置导出/导入**: 团队使用场景的补充功能
- **配置差异对比**: 锦上添花，等 profile 编辑功能稳定后再加

## 来源

- [Textual 官方文档 - 验证模块](https://textual.textualize.io/api/validation/) -- HIGH 置信度
- [Textual 官方文档 - Input 组件](https://textual.textualize.io/widgets/input/) -- HIGH 置信度
- [Textual 官方教程](https://textual.textualize.io/tutorial/) -- HIGH 置信度
- [CLI UX 模式参考](https://lucasfcosta.com/2022/06/01/ux-patterns-cli-tools.html) -- MEDIUM 置信度
- [Command Line Interface Guidelines](https://clig.dev/) -- MEDIUM 置信度
- [AWS CLI 配置模式参考](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) -- HIGH 置信度
- [Temporal CLI TOML Profile 模式](https://docs.temporal.io/develop/environment-configuration) -- MEDIUM 置信度
- [textual-wizard 第三方库](https://github.com/SkwalExe/textual-wizard) -- LOW 置信度（评估后决定不采用）
- [Pydantic + TOML 结构化配置模式](https://www.maskset.net/blog/2025/07/01/improving-python-clis-with-pydantic-and-dataclasses) -- MEDIUM 置信度
- 项目现有 `config.example.json` -- 直接分析，HIGH 置信度
