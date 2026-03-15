---
phase: 09
status: passed
verified: 2026-03-15
---

# Phase 9: 反机器人加固 — Verification

## Goal
统一浏览器指纹来源、扩充 Chrome 版本覆盖范围、将请求延迟改为场景化正态分布、错开并发 worker 启动时间，全面降低注册流程的机器人行为特征

## Success Criteria Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | SentinelTokenGenerator 不再使用硬编码默认 UA Chrome/145.0.0.0 | ✓ Passed | sentinel.py 中无 Chrome/145 字符串；不传 user_agent 抛 ValueError |
| 2 | register.py 和 sentinel.py 的浏览器标识来自同一 BrowserProfile 数据类 | ✓ Passed | BrowserProfile frozen dataclass 定义在 http.py；register.py 通过属性访问传给 sentinel |
| 3 | CHROME_PROFILES 包含 8-12 个不同 Chrome 版本 | ✓ Passed | 10 个 profile，覆盖 chrome131/133a/136/142 |
| 4 | 请求延迟使用正态分布，OTP 等高延迟场景单独调参 | ✓ Passed | random_delay 使用 random.gauss(mean, std)；13 处调用按三档场景标注 |
| 5 | 多 worker 并发启动时错开 2-8 秒 | ✓ Passed | batch.py 提交循环含 gauss(5.0, 1.5) clamp 2-8s 延迟 |

## Requirement Coverage

| ID | Description | Plan | Status |
|----|-------------|------|--------|
| ANTI-01 | 修复 SentinelTokenGenerator 默认 UA | 09-02 | ✓ |
| ANTI-02 | 统一 BrowserProfile 数据类 | 09-01 | ✓ |
| ANTI-03 | CHROME_PROFILES 扩充到 8-12 个 | 09-01 | ✓ |
| ANTI-04 | 延迟改为场景化正态分布 | 09-02 | ✓ |
| ANTI-05 | Worker 启动错开 2-8s | 09-03 | ✓ |

## Test Results
141 tests passed, 0 failed (full suite)

## Verdict
**PASSED** — All 5 success criteria verified, all 5 requirements covered.
