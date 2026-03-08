---
phase: 03-tui-config-wizard
plan: 01
subsystem: ui
tags: [python, textual, tui, registerconfig, validation]
requires:
  - phase: 02-module-split
    provides: 配置驱动的 CLI、RegisterConfig 模型与 run_batch(config) 执行入口
provides:
  - registration.workers 配置从模型贯通到 CLI 与 run_batch
  - WizardState 与 WizardApp 多屏向导骨架
  - EmailScreen 邮箱平台条件联动与敏感字段显隐
  - RegistrationScreen 注册参数校验与线性导航门禁
affects: [phase-03-upload-summary, phase-04-cli-profile, textual-ui]
tech-stack:
  added: [textual, textual-dev, pytest-asyncio]
  patterns: [集中草稿状态, Screen 线性切换, 双层表单校验]
key-files:
  created: [chatgpt_register/tui/app.py, chatgpt_register/tui/state.py, chatgpt_register/tui/screens/email.py, chatgpt_register/tui/screens/registration.py, tests/test_tui_email_screen.py, tests/test_tui_registration_screen.py]
  modified: [pyproject.toml, chatgpt_register/config/model.py, chatgpt_register/core/batch.py, chatgpt_register/cli.py, tests/test_config_model.py]
key-decisions:
  - "WizardState 保存所有平台和上传目标的草稿值，隐藏字段只隐藏不清空。"
  - "主流程首屏用 push，后续步骤间用 switch_screen，既避开 Textual 初始栈问题，也保持不可回退。"
  - "代理格式校验放在注册参数屏幕即时执行，最终并发数仍通过 RegisterConfig 与 run_batch 双重兜底。"
patterns-established:
  - "Pattern 1: Screen 只读写 WizardState，业务配置最终统一由 build_config()/RegisterConfig 收口。"
  - "Pattern 2: 每个输入字段都配套独立错误区，页面顶部再汇总错误。"
requirements-completed: [TUI-01, TUI-02, TUI-03, TUI-04, TUI-06, TUI-07]
duration: 34min
completed: 2026-03-08
---

# Phase 03 Plan 01 Summary

## 一句话总结

搭建了 Textual 向导底座，把并发配置贯通到执行层，并交付邮箱平台页与注册参数页的条件联动、即时校验和线性导航。

## Performance

- **Duration:** 34 min
- **Started:** 2026-03-08T00:35:00Z
- **Completed:** 2026-03-08T01:09:00Z
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments

- 新增 `textual` 依赖、`workers` 配置字段及其 CLI/run_batch 执行链路
- 创建 `WizardState`、`WizardApp`、`EmailScreen`、`RegistrationScreen`，实现前两步向导与错误汇总
- 增加 Textual 自动化测试，覆盖平台切换保值、敏感字段显隐、数值校验和线性导航

## Task Commits

Each task was committed atomically:

1. **Task 1: 补齐 TUI 依赖与注册执行字段** - `e95b5d3` (feat)
2. **Task 2: 创建 WizardState 与邮箱平台步骤** - `44712c4` (feat)
3. **Task 3: 实现注册参数步骤与线性导航门禁** - `44712c4` (feat, same changeset as Task 2 due shared app shell)

**Plan metadata:** 本 summary 及路线图同步将在后续文档提交中记录。

## Files Created/Modified

- `pyproject.toml` - 新增 Textual/TUI 测试依赖
- `chatgpt_register/config/model.py` - 为 `RegConfig` 增加 `workers`
- `chatgpt_register/core/batch.py` - 运行批处理时读取配置中的并发数
- `chatgpt_register/cli.py` - 旧配置与 CLI 参数现在保留 `workers`
- `chatgpt_register/tui/state.py` - 保存跨 Screen 草稿状态与最终配置导出
- `chatgpt_register/tui/app.py` - 统一注册命名 Screen、退出确认和线性切换
- `chatgpt_register/tui/screens/email.py` - 邮箱平台条件联动表单
- `chatgpt_register/tui/screens/registration.py` - 注册参数输入与双层校验反馈
- `tests/test_tui_email_screen.py` - 邮箱步骤交互测试
- `tests/test_tui_registration_screen.py` - 注册参数步骤交互测试

## Decisions Made

- 用 `WizardState` 保存未选中平台/目标的值，确保切回后恢复原输入。
- 维持“无上一步返回”的交互约束，只允许向前切屏；退出通过统一 modal 处理。
- 注册参数页先做即时校验，再在“下一步”时统一汇总错误，避免错误静默堆积到摘要页。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Textual 初始 screen stack 不支持在 `on_mount()` 直接 `switch_screen()`**
- **Found during:** Task 2 / Task 3 共享的向导骨架实现
- **Issue:** 初次 mount 时直接切屏会触发 `Screen(id='_default')._pop_result_callback()` 异常，导致测试无法启动
- **Fix:** 首屏改为 `push_screen("email")`，后续步骤仍保持 `switch_screen()` 线性推进
- **Files modified:** `chatgpt_register/tui/app.py`
- **Verification:** `uv run pytest tests/test_tui_email_screen.py tests/test_tui_registration_screen.py -q`
- **Committed in:** `44712c4`

---

**Total deviations:** 1 auto-fixed（Rule 3: 1）
**Impact on plan:** 仅修复 Textual 生命周期阻塞，不改变计划目标或交互约束。

## Issues Encountered

- Textual Pilot 在默认测试窗口下点击长页面底部按钮会越界，测试改为更大 `size=(120, 40)` 并对部分按钮直接调用 `press()`，不影响实际 UI 行为。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 上传目标页和摘要页可以直接复用当前 `WizardState` 与 `WizardApp` 壳层，不必重做状态结构。
- CLI 入口尚未接入 TUI，Sub2API 分组选择仍是旧交互，属于 Plan 02 收口项。

## Self-Check: PASSED

- `uv run pytest tests/test_config_model.py tests/test_tui_email_screen.py tests/test_tui_registration_screen.py -q` 通过
- `uv run python -c "from chatgpt_register.tui.app import WizardApp; print(WizardApp.__name__)"` 通过
- 已确认 `run_batch()` 源码包含 `config.registration.workers`

---
*Phase: 03-tui-config-wizard*
*Completed: 2026-03-08*
