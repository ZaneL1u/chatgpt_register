---
phase: 04-cli-profile
plan: 01
subsystem: config
tags: [python, profile, toml, cli, tui]
requires:
  - phase: 03-tui-config-wizard
    provides: 交互式 CLI/TUI 已统一消费 RegisterConfig，可继续接入 profile 选择与直载
provides:
  - ProfileSummary 摘要接口与稳定排序
  - Profile 仓储统一名称校验与路径构造
  - 损坏 TOML / 结构非法 profile 的稳定异常语义
affects: [phase-04-cli-profile, cli, tui, profile-selection]
tech-stack:
  added: [无新增第三方库]
  patterns: [TOML->RegisterConfig->ProfileSummary 单一事实源, Profile 仓储统一异常语义]
key-files:
  created: [.planning/phases/04-cli-profile/04-01-SUMMARY.md]
  modified: [chatgpt_register/config/__init__.py, chatgpt_register/config/profile.py, tests/test_profile_manager.py, .planning/STATE.md, .planning/ROADMAP.md]
key-decisions:
  - "摘要接口直接基于 TOML -> RegisterConfig roundtrip 构建，避免 TUI/CLI 各自重复解析文件。"
  - "save/load/exists/delete 全部通过 `_profile_path()` 收敛名称校验，确保用户输入在所有入口上语义一致。"
  - "TOML 解析失败与结构校验失败分成不同异常类型，便于上层选择跳过、警告或直接失败。"
patterns-established:
  - "Pattern 1: 仓储层先将 profile TOML 归一为 `RegisterConfig`，再对外暴露 UI 摘要对象。"
  - "Pattern 2: Profile 相关入口统一先校验名称，再处理路径、存在性和内容解析。"
requirements-completed: [PROF-02]
duration: 15min
completed: 2026-03-08
---

# Phase 04 Plan 01 Summary

## 一句话总结

为 Profile 仓储层补齐了可复用摘要接口、一致的名称校验入口，以及可直接转化为中文提示的损坏/非法 profile 异常语义。

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-08T07:35:00Z
- **Completed:** 2026-03-08T07:50:37Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- 新增 `ProfileSummary` 与 `list_profile_summaries()`，为 CLI/TUI 提供稳定排序的单一摘要事实源。
- 将名称校验收拢到 `_profile_path()`，让 `save/load/exists/delete` 对非法名称保持一致行为。
- 为不存在 profile、坏 TOML、结构非法 profile 提供稳定异常与中文消息，并补齐对应回归测试。

## Task Commits

Each task was committed atomically:

1. **Task 1: 为 ProfileManager 增加摘要读取接口** - `28788fa` (feat)
2. **Task 2: 统一所有 ProfileManager 入口的名称校验与异常语义** - `28788fa` (feat, shared repository changeset)

**Plan metadata:** 本 summary、`STATE.md` 与 `ROADMAP.md` 会在当前文档提交中统一记录。

## Files Created/Modified

- `chatgpt_register/config/profile.py` - 新增 `ProfileSummary`、摘要接口、统一路径 helper 与稳定异常语义
- `chatgpt_register/config/__init__.py` - re-export Profile 摘要类型与异常，便于上层统一导入
- `tests/test_profile_manager.py` - 覆盖摘要排序、三种邮箱平台、名称一致性与损坏 profile 行为
- `.planning/phases/04-cli-profile/04-01-SUMMARY.md` - 记录本计划交付结果与验证
- `.planning/STATE.md` - 推进当前执行位置到 Phase 04 / Plan 02 前
- `.planning/ROADMAP.md` - 标记 `04-01` 已完成

## Decisions Made

- 用 `ProfileSummary` 作为仓储层对上游 UI 的稳定摘要对象，而不是继续返回纯名称列表后让调用方自行拼接。
- `list_profiles()` 保持旧契约，只返回名称列表；新摘要接口承担 Phase 4 需要的 richer metadata。
- 仓储层内部先做 TOML 解析，再做 `RegisterConfig` 校验，从而把“文件损坏”和“配置不合法”区分开来。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 04-02 可以直接消费 `list_profile_summaries()` 构建 profile 启动页，无需再自行读取 TOML 拼摘要。
- CLI/TUI 上层只需捕获仓储层异常即可生成一致的中文提示文案。

## Self-Check: PASSED

- `uv run pytest tests/test_profile_manager.py -q` 通过（29 passed）
- `uv run python -c "from chatgpt_register.config.profile import ProfileManager; print(ProfileManager.__name__)"` 成功
- 已确认摘要接口覆盖 `duckmail` / `mailcow` / `mailtm`
- 已确认非法名称与损坏 profile 的异常信息可被上层直接转化为中文提示

---
*Phase: 04-cli-profile*
*Completed: 2026-03-08*
