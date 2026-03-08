# Phase 3: TUI 配置向导 - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

为现有注册工具新增基于 Textual 的多屏 TUI 配置向导，让用户无需手动编辑文件即可完成邮箱平台、注册参数、上传目标和最终确认。Phase 3 只负责向导本身与确认后启动执行的交接，不包含 profile 列表选择、profile 复制/派生、`--profile` 快速启动等 Phase 4 能力。

</domain>

<decisions>
## Implementation Decisions

### 向导导航方式
- 向导必须严格线性推进，只能从第一步开始逐步完成，不能跳步。
- 当前步骤只有在校验通过后才能进入下一步，不允许带错前进到最后统一检查。
- 不提供常规“上一步”返回能力。
- 用户中途退出时必须弹出一次确认，避免误退。
- 前面步骤一旦提交通过，就不再返回；最终摘要页是唯一允许回改配置的界面。

### 条件联动的数据保留策略
- 用户切换邮箱平台时，已填写过的其他平台配置保留在内存中；如果后续切回，应恢复之前输入。
- 用户切换上传目标时，被隐藏的目标配置同样保留，不自动清空。
- 这些已填写过但当前未选中的配置，仍应在 TOML 中保留。
- 条件字段应尽量预填合理默认值，减少空白表单。
- 当某个选择会导致后续字段集合变化时，界面应显示说明文字，而不是静默刷新。

### 表单反馈风格
- 字段在失焦时就进行校验提示；点击“下一步”时再次统一校验当前页。
- 错误提示同时提供两层反馈：字段下方逐项提示 + 页面顶部错误汇总。
- Bearer token、API key 等敏感字段默认掩码显示，但允许用户手动切换为可见。
- 数值类和地址类输入应尽量做实时格式校验，尽早指出问题。

### 确认摘要页
- 摘要页展开显示所有配置项，而不是只显示摘要字段。
- 敏感字段在摘要页默认脱敏，但允许用户临时展开查看。
- 摘要页直接允许原地修改字段，并在修改时即时校验。
- 最终执行按钮不需要二次确认弹窗，可直接执行；文案倾向于“我已确认，立即执行”。

### Claude's Discretion
- 每一步内部采用何种 Textual 组件组合来承载这些交互要求。
- 页面顶部步骤提示条、说明文案样式和错误汇总区域的具体视觉布局。
- 摘要页原地编辑是以内联表单、弹出编辑区还是分组编辑面板实现。
- 字段默认值的具体覆盖范围，以及哪些说明文案需要常驻、哪些只在切换后出现。

</decisions>

<specifics>
## Specific Ideas

- “不能跳、不能回头，最后统一在摘要页改”是本阶段最重要的交互原则。
- 用户希望切换邮箱平台或上传目标后，之前填过的数据不要丢；即使暂时隐藏，也继续保留到 TOML。
- 最终确认按钮可以直接命名为“我已确认，立即执行”。

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `chatgpt_register/config/model.py` 中的 `RegisterConfig` 已覆盖邮箱、注册参数、OAuth、上传目标等结构，可作为向导字段分组的单一数据源。
- `chatgpt_register/config/profile.py` 中的 `ProfileManager` 已具备 TOML 保存/加载能力，后续 Phase 4 可直接复用。
- `chatgpt_register/cli.py` 已有旧配置到 `RegisterConfig` 的映射逻辑，可作为 TUI 退出后交接执行流程的参考。
- `chatgpt_register/upload/sub2api.py` 中已有 Sub2API 分组绑定准备逻辑，后续规划需明确它在向导阶段还是执行前阶段触发。

### Established Patterns
- 项目当前已锁定 “TUI 只产出配置，退出后再运行 `run_batch(config)`” 的串行模式，不与 `RuntimeDashboard` 并存。
- `chatgpt_register/core/batch.py` 当前从 `config.registration.total_accounts` 读取注册数量，但并发数仍是写死上限 `3`，与本阶段需求存在模型扩展缺口。
- 现有 CLI 仍保留 `input()` 式交互和 `config.json` 兼容层；Phase 3 的向导需要在不扩大到 Phase 4 范围的前提下替代这部分人工输入体验。
- 现有测试集中在配置模型与 ProfileManager，TUI 相关测试尚未建立。

### Integration Points
- 新的 TUI 子包预计挂在 `chatgpt_register/tui/`，并由 [`chatgpt_register/cli.py`](/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/cli.py) 调起。
- 向导完成后需要输出可直接构造 `RegisterConfig` 的数据，再交给 `run_batch(config)`。
- 摘要页原地编辑能力要求字段元数据、校验与显示格式尽量围绕 `RegisterConfig` 统一组织，避免再造第二套表单 schema。

</code_context>

<deferred>
## Deferred Ideas

- profile 列表快速选择、已有 profile 预览、复制/派生与 `--profile` 启动路径属于 Phase 4，不在本阶段实现。
- 完整移除 `config.json` 兼容层也属于 Phase 4 的 CLI 收口工作，不在本阶段决策范围内。

</deferred>

---

*Phase: 03-tui-config-wizard*
*Context gathered: 2026-03-08*
