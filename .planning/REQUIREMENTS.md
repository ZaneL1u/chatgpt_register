# Requirements: ChatGPT Register TUI 化重构

**Defined:** 2026-03-07
**Core Value:** 用户通过 TUI 交互式向导完成所有注册配置，无需手动编辑任何配置文件

## v1 Requirements

### 配置层 (Config)

- [ ] **CONF-01**: 用户配置以 TOML 格式保存为 profile 文件到 `~/.chatgpt-register/profiles/`
- [ ] **CONF-02**: 支持通过参数指定 profile 存储路径
- [ ] **CONF-03**: Pydantic 模型校验所有配置项，即时反馈错误
- [ ] **CONF-04**: 配置完成后显示确认摘要页，确认后才开始注册
- [ ] **CONF-05**: 移除 config.json 配置方式，TUI + TOML 是唯一入口

### TUI 交互 (TUI)

- [ ] **TUI-01**: 用户通过 Textual Select/RadioSet 选择邮箱平台（DuckMail/Mailcow/Mail.tm）
- [ ] **TUI-02**: 选择不同邮箱平台后只展示对应平台的配置字段（条件联动）
- [ ] **TUI-03**: Bearer token、API key 等敏感字段使用掩码输入
- [ ] **TUI-04**: 分步向导：邮箱 → 注册参数 → 上传目标 → 确认，多屏 Screen 导航
- [ ] **TUI-05**: 用户通过 Select 选择上传目标（CPA/Sub2API/both/none），条件展开对应配置
- [ ] **TUI-06**: 用户可设置注册账号数量和并发数（数值输入 + 验证）
- [ ] **TUI-07**: 用户可设置代理地址（可选输入 + 格式验证）

### Profile 管理 (PROF)

- [ ] **PROF-01**: 有已保存 profile 时显示列表快速选择，无 profile 时直接进入向导
- [ ] **PROF-02**: Profile 列表展示名称 + 摘要信息（邮箱平台、上传目标等）
- [ ] **PROF-03**: 支持 `--profile <name>` 参数直接加载 profile 跳过 TUI（非交互模式）
- [ ] **PROF-04**: 用户可基于已有 profile 复制派生新配置

### 架构改造 (ARCH)

- [x] **ARCH-01**: 拆分 `chatgpt_register.py` 为多模块包结构
- [ ] **ARCH-02**: 收拢 20+ 全局变量为配置 dataclass/Pydantic model，`run_batch()` 接受配置参数

## v2 Requirements

### 体验增强

- **EXP-01**: Profile 预览与编辑（选择 profile 时先展示摘要，允许临时修改再运行）
- **EXP-02**: Dry Run 模式（验证连通性但不实际注册）
- **EXP-03**: 配置导出/导入（脱敏后分享给团队）
- **EXP-04**: 配置差异对比（修改 profile 时高亮变更项）
- **EXP-05**: 旧 config.json 迁移到 TOML 的迁移工具

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI 配置界面 | 项目定位为本地 CLI，Textual 自带 `textual serve` 可零成本开放浏览器模式 |
| 配置加密存储 | CLI 工具通常依赖文件系统权限，文件权限设为 600 即可 |
| 图形化进度嵌入向导 | TUI 向导和运行时面板是不同生命周期，应保持分离 |
| 多用户权限管理 | 单用户本地工具 |
| 配置历史版本控制 | TOML 文件本身适合 Git 追踪 |
| 内置 TOML 编辑器 | 向导表单是结构化编辑的最佳方式 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 1 | Done |
| CONF-02 | Phase 1 | Done |
| CONF-03 | Phase 1 | Done |
| CONF-04 | Phase 3 | Pending |
| CONF-05 | Phase 4 | Pending |
| TUI-01 | Phase 3 | Pending |
| TUI-02 | Phase 3 | Pending |
| TUI-03 | Phase 3 | Pending |
| TUI-04 | Phase 3 | Pending |
| TUI-05 | Phase 3 | Pending |
| TUI-06 | Phase 3 | Pending |
| TUI-07 | Phase 3 | Pending |
| PROF-01 | Phase 4 | Pending |
| PROF-02 | Phase 4 | Pending |
| PROF-03 | Phase 4 | Pending |
| PROF-04 | Phase 4 | Pending |
| ARCH-01 | Phase 2 | Complete |
| ARCH-02 | Phase 1 | Done |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after roadmap creation*
