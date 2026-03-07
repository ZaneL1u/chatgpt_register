---
phase: 1
slug: config-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (需新增安装) |
| **Config file** | none — Wave 0 installs |
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
| 01-01-01 | 01 | 1 | CONF-03 | unit | `python -m pytest tests/test_config_model.py::test_validation_errors -x` | W0 | pending |
| 01-01-02 | 01 | 1 | ARCH-02 | unit | `python -m pytest tests/test_config_model.py::test_field_coverage -x` | W0 | pending |
| 01-02-01 | 02 | 2 | CONF-01 | unit | `python -m pytest tests/test_profile_manager.py::test_save_and_load -x` | W0 | pending |
| 01-02-02 | 02 | 2 | CONF-02 | unit | `python -m pytest tests/test_profile_manager.py::test_custom_base_dir -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — 空文件，标记为 Python 包
- [ ] `tests/conftest.py` — 共享 fixtures（示例 RegisterConfig 实例、临时目录）
- [ ] `tests/test_config_model.py` — 覆盖 CONF-03, ARCH-02
- [ ] `tests/test_profile_manager.py` — 覆盖 CONF-01, CONF-02
- [ ] 框架安装: `uv add --dev pytest` — 当前未检测到 pytest

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
