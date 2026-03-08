---
phase: 04
slug: cli-profile
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-08
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_profile_manager.py tests/test_tui_profile_screen.py tests/test_cli_profile_mode.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_profile_manager.py tests/test_tui_profile_screen.py tests/test_cli_profile_mode.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | PROF-02 | unit | `uv run pytest tests/test_profile_manager.py -q` | ✅ | ⬜ pending |
| 04-01-02 | 01 | 1 | PROF-02 | unit | `uv run pytest tests/test_profile_manager.py -q` | ✅ | ⬜ pending |
| 04-02-01 | 02 | 2 | PROF-01 | integration | `uv run pytest tests/test_tui_profile_screen.py -q` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | PROF-04 | integration | `uv run pytest tests/test_tui_profile_screen.py tests/test_tui_summary_screen.py -q` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | PROF-03 | integration | `uv run pytest tests/test_cli_tui.py tests/test_cli_profile_mode.py -q` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | CONF-05 | regression | `uv run pytest tests/test_cli_profile_mode.py tests/test_sub2api_group_binding.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tui_profile_screen.py` — 覆盖 profile 启动页、运行/新建/派生路径
- [ ] `tests/test_cli_profile_mode.py` — 覆盖 `--profile`、非交互失败、遗留配置提示
- [ ] `tests/test_sub2api_group_binding.py` — 覆盖缺失分组绑定失败与无交互保证

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Profile 列表摘要在终端宽度 100 左右时仍可读 | PROF-02 | 视觉密度与换行效果难用单元测试断言 | 运行交互式入口，准备 3 个不同 profile，确认名称、邮箱平台、上传目标、并发摘要不挤压失真 |
| 当前目录存在 `config.json` 时的迁移提示文案是否清晰 | CONF-05 | 文案可操作性需要人工判断 | 在仓库根目录放置临时 `config.json`，运行交互式和非交互式入口，确认提示明确指向 TUI/TOML 新路径 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

