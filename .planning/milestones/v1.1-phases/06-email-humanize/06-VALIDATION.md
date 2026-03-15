---
phase: 6
slug: email-humanize
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 9.0.2 |
| **Config file** | pyproject.toml (`[dependency-groups] dev`) |
| **Quick run command** | `pytest tests/test_humanize.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_humanize.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | HUMAN-01~04 | unit | `pytest tests/test_humanize.py -x -q` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | HUMAN-01 | unit | `pytest tests/test_humanize.py::test_prefix_is_human_format -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | HUMAN-02 | unit | `pytest tests/test_humanize.py::test_at_least_3_formats -x` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 1 | HUMAN-03 | unit | `pytest tests/test_humanize.py::test_uniqueness_across_batch -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 1 | HUMAN-04 | unit | `pytest tests/test_humanize.py::test_backward_compatibility -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_humanize.py` — stubs for HUMAN-01 ~ HUMAN-04
- [ ] `tests/conftest.py` — 新增含 humanize_email 字段的配置 fixture

*Existing pytest infrastructure covers framework needs; only test files are missing.*

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
