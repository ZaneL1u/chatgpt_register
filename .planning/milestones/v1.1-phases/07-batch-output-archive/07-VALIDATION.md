---
phase: 7
slug: batch-output-archive
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (已安装) |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_archive.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_archive.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 0 | BATCH-01 | unit | `python -m pytest tests/test_archive.py -x` | :x: W0 | :white_large_square: pending |
| 07-01-02 | 01 | 1 | BATCH-01 | unit | `python -m pytest tests/test_archive.py::test_create_archive_dir -x` | :x: W0 | :white_large_square: pending |
| 07-01-03 | 01 | 1 | BATCH-01 | unit | `python -m pytest tests/test_archive.py::test_path_redirection -x` | :x: W0 | :white_large_square: pending |
| 07-01-04 | 01 | 1 | BATCH-01 | integration | `python -m pytest tests/test_archive.py::test_run_batch_archive -x` | :x: W0 | :white_large_square: pending |

*Status: :white_large_square: pending / :white_check_mark: green / :x: red / :warning: flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_archive.py` — stubs for BATCH-01 (归档目录生成、路径重定向、集成)

*Existing conftest.py already provides shared fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard 显示归档路径 | BATCH-01 | rich Live UI 无法在 pytest 中验证 | 手动运行 batch，检查 Dashboard 面板 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
