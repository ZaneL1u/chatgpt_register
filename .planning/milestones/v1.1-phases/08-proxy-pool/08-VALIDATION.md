---
phase: 8
slug: proxy-pool
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 9.0.2 |
| **Config file** | pyproject.toml (`[project.optional-dependencies]`) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | PROXY-01 | unit | `pytest tests/test_config_model.py::test_proxies_field -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | PROXY-02 | unit | `pytest tests/test_proxy_parser.py::test_mixed_formats -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | PROXY-05 | unit | `pytest tests/test_config_model.py::test_proxy_migration -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | PROXY-03 | unit | `pytest tests/test_proxy_pool.py::test_load_balance -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 1 | PROXY-04 | unit | `pytest tests/test_proxy_pool.py::test_worker_binding -x` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | PROXY-06 | unit | `pytest tests/test_wizard_proxy.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_proxy_parser.py` — 代理地址解析和校验测试（PROXY-02）
- [ ] `tests/test_proxy_pool.py` — ProxyPool 线程安全和负载均衡测试（PROXY-03, PROXY-04）
- [ ] `tests/test_config_model.py` — 扩展现有测试覆盖 proxies 字段和迁移（PROXY-01, PROXY-05）
- [ ] `tests/test_wizard_proxy.py` — 向导多代理输入测试（PROXY-06）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard 代理列显示 | PROXY-03/04 | 需要 Rich Live 终端环境 | 启动批量注册，观察 Dashboard 中代理列是否正确显示各 worker 绑定的代理 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
