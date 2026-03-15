---
phase: 9
slug: anti-bot
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ |
| **Config file** | pyproject.toml [tool.pytest] |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | ANTI-01 | unit | `uv run pytest tests/test_anti_bot.py::test_sentinel_no_default_ua -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ANTI-02 | unit | `uv run pytest tests/test_anti_bot.py::test_browser_profile_dataclass -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ANTI-03 | unit | `uv run pytest tests/test_anti_bot.py::test_chrome_profiles_count -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ANTI-04 | unit | `uv run pytest tests/test_anti_bot.py::test_random_delay_gaussian -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ANTI-05 | unit | `uv run pytest tests/test_anti_bot.py::test_worker_stagger_delay -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_anti_bot.py` — stubs for ANTI-01 through ANTI-05

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 多次运行日志观察版本多样性 | ANTI-03 | 需要实际网络请求 | 运行 3 次注册，检查日志中 Chrome 版本不同 |
| 日志时间戳验证启动错开 | ANTI-05 | 需要多 worker 并发运行 | 启动 3+ worker，检查日志时间戳间隔 2-8s |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
