---
phase: 09-anti-bot
plan: 02
status: complete
started: 2026-03-15
completed: 2026-03-15
requirements_completed: [ANTI-01, ANTI-04]
---

# Plan 09-02 Summary

## What was built
改造 `random_delay` 从均匀分布改为正态分布 `gauss(mean, std)` 并 clamp 到下限；移除 `SentinelTokenGenerator` 中硬编码的 `Chrome/145.0.0.0` 默认 UA（改为必传参数）；移除 `fetch_sentinel_challenge` 中硬编码的 `sec_ch_ua` 回退值；适配 `register.py` 使用 `BrowserProfile` 属性访问，13 处 `random_delay` 调用按场景标注三档参数。

## Key files
- `chatgpt_register/core/http.py` — random_delay 改为 gauss(mean, std, min_bound)
- `chatgpt_register/core/sentinel.py` — 移除硬编码默认 UA 和 sec_ch_ua
- `chatgpt_register/core/register.py` — BrowserProfile 属性访问 + 场景化延迟参数
- `tests/test_anti_bot.py` — 新增 6 个测试

## Requirements addressed
- ANTI-01: 修复 SentinelTokenGenerator 默认 UA
- ANTI-04: 延迟改为场景化正态分布

## Deviations
None.

## Self-Check: PASSED
- [x] random_delay 使用 random.gauss
- [x] sentinel.py 中无 Chrome/145 硬编码
- [x] register.py 13 处延迟按场景分三档
- [x] 全部 138 个测试通过
