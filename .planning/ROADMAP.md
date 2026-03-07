# 路线图: ChatGPT Register TUI 化重构

## 概述

将 ChatGPT 批量注册 CLI 工具从散乱的配置体验（config.json + CLI 参数 + 环境变量）重构为基于 Textual 的交互式 TUI 向导 + TOML Profile 机制。路径清晰：先建配置层地基（Pydantic schema + ProfileManager），再拆分 2000+ 行单文件为模块化包结构，然后构建完整的 Textual 多屏向导，最后将所有组件通过 CLI 入口串联并实现 Profile 管理。

## Phases

**阶段编号说明：**
- 整数阶段 (1, 2, 3): 规划好的里程碑工作
- 小数阶段 (2.1, 2.2): 紧急插入（标记 INSERTED）

小数阶段按数值顺序插入到相邻整数阶段之间。

- [ ] **Phase 1: 配置层基础** - Pydantic 配置模型 + TOML ProfileManager + 全局变量收拢
- [ ] **Phase 2: 模块拆分** - 单文件拆为多模块包结构，run_batch() 接受配置参数
- [ ] **Phase 3: TUI 配置向导** - Textual 多屏分步向导，覆盖完整配置流程
- [ ] **Phase 4: CLI 集成与 Profile 管理** - 混合启动模式、非交互模式、移除旧配置方式

## Phase Details

### Phase 1: 配置层基础
**Goal**: 所有配置字段有统一的 Pydantic 数据模型和 TOML 持久化能力，ProfileManager 可以完成 Profile 的创建/读取/保存/列举
**Depends on**: Nothing (first phase)
**Requirements**: CONF-01, CONF-02, CONF-03, ARCH-02
**Success Criteria** (what must be TRUE):
  1. RegisterConfig Pydantic 模型能表达所有邮箱平台（DuckMail/Mailcow/Mail.tm）、上传目标（CPA/Sub2API）、代理等配置项，校验失败时返回清晰错误
  2. ProfileManager 能将 RegisterConfig 实例保存为 TOML 文件到 `~/.chatgpt-register/profiles/`，并能从 TOML 文件还原为 RegisterConfig 实例
  3. 可通过参数指定 profile 存储路径，不依赖默认路径
  4. 现有 20+ 个全局变量已收拢为 RegisterConfig 数据类字段，不再有散落的模块级可变状态
**Plans**: TBD

Plans:
- [ ] 01-01: TBD
- [ ] 01-02: TBD

### Phase 2: 模块拆分
**Goal**: chatgpt_register.py 拆分为清晰的多模块包结构，run_batch() 通过 RegisterConfig 参数驱动而非全局变量
**Depends on**: Phase 1
**Requirements**: ARCH-01
**Success Criteria** (what must be TRUE):
  1. 项目以 Python 包结构组织（config/、core/、adapters/、upload/、tui/ 等子模块），不再存在 2000+ 行的单文件
  2. `run_batch()` 接受 RegisterConfig 实例作为参数，执行全部注册流程
  3. 所有现有功能（批量注册、OTP 验证、token 获取、结果上传、代理支持）在拆分后保持正常工作
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

### Phase 3: TUI 配置向导
**Goal**: 用户通过 Textual TUI 交互式完成所有注册配置，无需手动编辑任何文件
**Depends on**: Phase 2
**Requirements**: TUI-01, TUI-02, TUI-03, TUI-04, TUI-05, TUI-06, TUI-07, CONF-04
**Success Criteria** (what must be TRUE):
  1. 用户通过 Select/RadioSet 选择邮箱平台后，界面只展示该平台需要的配置字段（条件联动）
  2. 用户通过 Select 选择上传目标后，界面条件展开对应的 CPA/Sub2API 配置字段
  3. 敏感字段（bearer token、API key 等）在输入时显示掩码而非明文
  4. 向导按「邮箱平台 → 注册参数 → 上传目标 → 确认摘要」分步推进，每步为独立 Screen
  5. 确认摘要页展示完整配置概览，用户确认后才进入注册流程
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: CLI 集成与 Profile 管理
**Goal**: TUI 向导、Profile 系统、CLI 入口完整串联，TUI + TOML 成为唯一配置方式
**Depends on**: Phase 3
**Requirements**: PROF-01, PROF-02, PROF-03, PROF-04, CONF-05
**Success Criteria** (what must be TRUE):
  1. 有已保存 profile 时启动后显示 profile 列表（含名称和摘要信息），用户可快速选择；无 profile 时直接进入向导
  2. 用户可通过 `--profile <name>` 参数直接加载 profile 跳过 TUI，实现非交互模式运行
  3. 用户可基于已有 profile 复制派生新配置
  4. config.json 配置方式已完全移除，TUI + TOML 是唯一配置入口
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

## Progress

**执行顺序:**
阶段按数值顺序执行: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 配置层基础 | 0/? | Not started | - |
| 2. 模块拆分 | 0/? | Not started | - |
| 3. TUI 配置向导 | 0/? | Not started | - |
| 4. CLI 集成与 Profile 管理 | 0/? | Not started | - |
