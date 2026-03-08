---
phase: 2
slug: module-split
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-08
---

# Phase 2 — Validation Strategy

> 模块拆分阶段的验证策略。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (pytest 默认配置) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ARCH-01 | unit | `python -m pytest tests/test_config_model.py tests/test_profile_manager.py -x -q` | existing | pending |
| 02-01-02 | 01 | 1 | ARCH-01 | integration | `python -c "from chatgpt_register.config.model import RegisterConfig"` | needs update | pending |
| 02-02-01 | 02 | 1 | ARCH-01 | integration | `python -c "from chatgpt_register.core.batch import run_batch"` | needs create | pending |
| 02-02-02 | 02 | 1 | ARCH-01 | shell | `test ! -f chatgpt_register.py && test ! -f config_model.py && test ! -f profile_manager.py` | N/A | pending |
| 02-02-03 | 02 | 1 | ARCH-01 | regression | `python -m pytest tests/ -x -q` | existing | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- Existing `tests/test_config_model.py` and `tests/test_profile_manager.py` cover config layer
- Import paths in existing tests need updating after package restructure

*Existing infrastructure covers base requirements; import path updates are part of plan tasks.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| pyproject.toml console_scripts 正常 | ARCH-01 | 需要 pip install -e . 后执行 | `pip install -e . && chatgpt-register --help` |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
