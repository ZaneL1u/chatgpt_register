# Milestones

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

