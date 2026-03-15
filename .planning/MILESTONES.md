# Milestones

## v1.1 反风控增强 (Shipped: 2026-03-15)

**Phases completed:** 4 phases, 10 plans
**Timeline:** 17 days (2026-02-26 → 2026-03-15)
**Files changed:** 57 | **Python LOC:** 9,203 (净增 +5,222 行)
**Git range:** feat(06-01)..docs(v1.1)
**Requirements:** 16/16 v1.1 requirements satisfied

**Key accomplishments:**

- 邮箱拟人化引擎（HumanizedPrefixGenerator）：4 种真实人名格式，集成 catchmail/maildrop 适配器
- 批次输出归档：output/<YYYYMMDD_HHMM>/ 自动归档，config.model_copy 路径重定向零侵入
- 多代理池调度：ProxyPool 线程安全负载均衡 + 向导 4 种输入模式 + 旧 proxy 字段自动迁移
- 统一浏览器指纹：BrowserProfile dataclass + 10 个 Chrome 版本，消除双维护
- 场景化正态延迟分布 + Worker 启动错开（gauss 2-8s）

**Tech Debt (accepted):**

- DuckMail/Mailcow/MailTm 适配器未接入 humanize_email（设计范围外，v1.2 覆盖）
- PROXY-03 需求描述 round-robin vs 实际实现 min-load（功能更优，文档未对齐）
- 部分 SUMMARY.md frontmatter requirements_completed 未填充

---

## v1.0 TUI 化重构 MVP (Shipped: 2026-03-08)

**Phases completed:** 5 phases, 10 plans
**Timeline:** 11 days (2026-02-26 → 2026-03-08)
**Commits:** 48 | **Files changed:** 219 | **Python LOC:** 7,353
**Git range:** feat(01-01)..chore: 更新 README.md
**Requirements:** 18/18 v1 requirements satisfied

**Key accomplishments:**

- RegisterConfig Pydantic v2 数据模型 + ProfileManager TOML 持久化
- 2000+ 行单文件拆分为多模块包结构，run_batch() 配置驱动
- Textual TUI 多屏向导：邮箱 → 注册参数 → 上传目标 → 确认摘要
- Profile 启动页 + `--profile` 非交互直载 + 派生复制
- config.json 完全移除，TUI + TOML 成为唯一配置入口
- 全部 18 个需求验收通过，70 个测试全部通过

---

