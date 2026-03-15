# Project Retrospective

*每个里程碑完成后更新。经验教训向前馈入未来规划。*

## Milestone: v1.0 — TUI 化重构 MVP

**Shipped:** 2026-03-08
**Phases:** 5 | **Plans:** 10

### What Was Built

- Pydantic v2 配置数据模型 + ProfileManager TOML 持久化（save/load/list/delete）
- 2000+ 行单文件拆分为 config/core/adapters/upload/tui 多模块包结构
- questionary 交互式向导：邮箱平台 → 注册参数 → 上传目标 → 确认摘要
- Profile 启动页（列表选择 + 摘要展示 + 派生复制）
- `--profile` 非交互直载模式 + config.json 完全移除
- 70 个测试覆盖全部核心路径

### What Worked

- **配置层先行策略**：先建 Pydantic 模型再做拆分，后续模块拆分和 TUI 都能直接消费 RegisterConfig，无需回头改造
- **TDD 驱动**：每个 plan 都先写测试再实现，Phase 1-2 平均每个 plan 仅 ~8 分钟
- **TUI-as-Config-Generator 模式**：向导只负责生成 RegisterConfig，不涉及运行时逻辑，职责清晰
- **及时的架构决策切换**：发现 Textual headless 测试不稳定后果断切换到 questionary，避免了更大的沉没成本

### What Was Inefficient

- **Phase 4 验收延迟**：Phase 4 执行完后缺少 VERIFICATION.md，导致里程碑审计发现 5 个 orphaned 需求，需要额外的 Phase 5 来补闭环
- **Textual → questionary 切换**：Phase 3 最初基于 Textual 实现，后因测试问题推倒重来，Phase 3 耗时最长（~65min，含返工）
- **Planning 文档中的历史痕迹**：部分文档仍残留 config.json / questionary 的旧引用，增加了审计噪音

### Patterns Established

- VERIFICATION.md 应在每个阶段执行完毕后立即创建，不应延迟到里程碑审计时补
- Profile 相关的运行时校验（如 Sub2API group binding）属于配置态，不应在运行阶段触发交互补问
- CLI 参数面精简为 `--profile`/`--profiles-dir`/`--non-interactive`，业务配置全部回归 profile

### Key Lessons

1. 阶段级验收文件（VERIFICATION.md）是里程碑审计的关键依赖，缺失会导致需求被判定为 orphaned，即使实现和测试都已存在
2. TUI 框架选型应优先验证 headless 测试能力，而非仅看功能丰富度
3. 配置驱动架构（RegisterConfig 作为唯一参数）极大简化了模块间依赖，是本项目最成功的架构决策

### Cost Observations

- 总执行时间: ~2.35 hours（10 个 plan）
- 平均每个 plan: ~14min
- 最快: Phase 5 (~5min, 纯文档)
- 最慢: Phase 3 (~32.5min/plan, 含 Textual→questionary 返工)

---

## Milestone: v1.1 — 反风控增强

**Shipped:** 2026-03-15
**Phases:** 4 | **Plans:** 10

### What Was Built

- HumanizedPrefixGenerator：4 种人名格式邮箱前缀，集成 catchmail/maildrop 适配器
- 批次输出归档模块：output/<YYYYMMDD_HHMM>/ 自动归档 + config.model_copy 路径重定向
- ProxyPool 线程安全负载均衡 + proxy_parser 多协议解析 + 向导 4 种输入模式
- BrowserProfile frozen dataclass + 10 个 Chrome 版本，统一 register/sentinel 指纹来源
- 场景化正态延迟 random_delay() + Worker 启动 gauss(5.0, 1.5) clamp 2-8s 错开

### What Worked

- **配置模型先行**：Phase 6 先扩展 EmailConfig.humanize_email，Phase 8 先扩展 proxies 字段，后续集成自然顺畅
- **VERIFICATION.md 同步产出**：吸取 v1.0 教训，每阶段执行完毕立即验证，里程碑审计零 orphan 需求
- **config.model_copy 重定向模式**：归档集成只需深拷贝 config 修改路径，下游代码零改动，Phase 7 整阶段仅 1 plan
- **min-load 替代 round-robin**：代理分配在不均匀耗时场景下更均匀，是对需求的改进而非偏离

### What Was Inefficient

- **SUMMARY frontmatter 未填充**：Phase 6/8/9 的 SUMMARY.md `requirements_completed` 字段为空，导致审计时需要三源交叉验证才能确认覆盖
- **适配器拟人化范围界定晚**：Phase 6 设计时未显式声明「仅 catchmail/maildrop」，审计时才发现 DuckMail/Mailcow/MailTm 未接入，记为技术债务

### Patterns Established

- config.model_copy(deep=True) 路径重定向是非侵入式模块集成的有效模式
- BrowserProfile frozen dataclass 消除了多模块间浏览器信息的双维护
- ProxyPool 借出/归还模式适合并发 worker 资源管理

### Key Lessons

1. SUMMARY.md frontmatter 是审计自动化的关键数据源，必须在计划完成时完整填充
2. 功能范围（如「哪些适配器接入」）应在需求阶段显式界定，而非在审计时才发现缺口
3. 正态分布延迟比均匀分布更接近真实用户行为，是反风控的有效策略

### Cost Observations

- 总执行时间: ~4 phases, 10 plans
- 最快 phase: Phase 7（1 plan，纯模块+集成）
- 最复杂 phase: Phase 8（3 plans，含 ProxyPool 线程安全 + 向导多模式）
- 测试: 从 70 增长到 141（+71 个测试）

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
| --------- | ------ | ----- | ---------- |
| v1.0 | 5 | 10 | 初始里程碑，建立 TDD + 配置驱动架构模式 |
| v1.1 | 4 | 10 | 反风控增强，VERIFICATION 同步产出，config.model_copy 重定向模式 |

### Cumulative Quality

| Milestone | Tests | Key Metric |
| --------- | ----- | ---------- |
| v1.0 | 70 | 18/18 需求全部验收通过 |
| v1.1 | 141 | 16/16 需求全部验收通过，5 项非关键技术债务 |

### Top Lessons (Verified Across Milestones)

1. 阶段级验收文件应与执行同步产出，不应延迟（v1.0 教训，v1.1 已修正）
2. 框架选型需优先验证测试基础设施兼容性
3. SUMMARY.md frontmatter 是审计自动化的关键数据源，必须完整填充
4. 功能范围应在需求阶段显式界定，而非审计时才发现缺口
