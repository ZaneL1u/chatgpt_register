# Phase 5: Phase 4 验收闭环 - Research

**Researched:** 2026-03-08
**Domain:** 验收闭环 / 文档同步 / 需求追踪
**Confidence:** HIGH

## Summary

Phase 5 是一个**纯文档性验收阶段**，不涉及任何代码变更。其核心目标是补齐 Phase 4 的验收文件缺口，将已实现但未正式验收的 5 个需求（PROF-01~04、CONF-05）从"orphaned"状态转变为"satisfied"状态。

根据 `v1.0-MILESTONE-AUDIT.md` 的审计结论，Phase 4 的实现与测试已全部完成（70 passed），但缺少正式的 `04-VERIFICATION.md` 文件，导致需求在三方交叉审计中无法通过。本阶段只需创建验收文档并更新追踪表即可完成里程碑闭环。

**Primary recommendation:** 基于现有 SUMMARY.md 证据和测试结果，按 Phase 1-3 的 VERIFICATION.md 格式创建 Phase 4 验收文件，然后同步更新 REQUIREMENTS.md。

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROF-01 | 有 profile 时显示列表快速选择，无 profile 时直接进入向导 | 04-02-SUMMARY.md 记录 ProfileSelectScreen 实现；tests/test_tui_profile_screen.py 覆盖启动分流 |
| PROF-02 | Profile 列表展示名称 + 摘要信息 | 04-01-SUMMARY.md 记录 ProfileSummary 接口；04-02-SUMMARY.md 记录 TUI 消费；tests/test_profile_manager.py 覆盖 |
| PROF-03 | 支持 `--profile <name>` 参数直接加载 profile 跳过 TUI | 04-03-SUMMARY.md 记录 CLI 重写；tests/test_cli_profile_mode.py 覆盖直载与失败路径 |
| PROF-04 | 用户可基于已有 profile 复制派生新配置 | 04-02-SUMMARY.md 记录派生路径；tests/test_tui_profile_screen.py 覆盖预填与保存闭环 |
| CONF-05 | 移除 config.json 配置方式，TUI + TOML 是唯一入口 | 04-03-SUMMARY.md 记录迁移提示与 questionary 移除；tests/test_cli_profile_mode.py + tests/test_sub2api_group_binding.py 验证 |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| 无新增依赖 | - | 本阶段无代码变更 | 纯文档验收阶段 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.x | 验证现有测试通过 | 确认 70 passed 状态 |

**Installation:**
无需安装任何依赖。

## Architecture Patterns

### Recommended Project Structure

```
.planning/
├── REQUIREMENTS.md           # 需要更新 Traceability 状态
├── v1.0-MILESTONE-AUDIT.md   # 审计依据（只读参考）
└── phases/
    ├── 04-cli-profile/
    │   ├── 04-01-SUMMARY.md  # Plan 1 证据
    │   ├── 04-02-SUMMARY.md  # Plan 2 证据
    │   ├── 04-03-SUMMARY.md  # Plan 3 证据
    │   ├── 04-VALIDATION.md  # 验证策略（已存在）
    │   └── 04-VERIFICATION.md # 需要创建
    └── 05-phase4-verification-closure/
        └── 05-RESEARCH.md     # 本文件
```

### Pattern 1: VERIFICATION.md 结构

**What:** Phase 级别验收文档，汇总该阶段所有需求的实现状态
**When to use:** 每个 Phase 完成后
**Example:**

```markdown
---
phase: 04
slug: cli-profile
status: passed
created: 2026-03-08
requirements:
  - PROF-01
  - PROF-02
  - PROF-03
  - PROF-04
  - CONF-05
summary_score: 5/5
---

# Phase 04 验证报告

## 结论
[一句话总结]

## Goal Check
[逐条 Must-have 验证]

## Requirement Traceability
| Requirement | Result | Evidence |
|-------------|--------|----------|
| ... | ... | ... |

## Additional Checks
[测试结果、其他验证]

## Human Verification
[是否需要人工阻塞]

## Final Status
**passed**
```

### Pattern 2: REQUIREMENTS.md Traceability 更新

**What:** 将 Phase 4 需求状态从 `Pending` 更新为 `Done`
**When to use:** VERIFICATION.md 创建后

当前状态：
```markdown
| CONF-05 | Phase 4 | Pending |
| PROF-01 | Phase 4 | Pending |
| PROF-02 | Phase 4 | Pending |
| PROF-03 | Phase 4 | Pending |
| PROF-04 | Phase 4 | Pending |
```

目标状态：
```markdown
| CONF-05 | Phase 4 | Done |
| PROF-01 | Phase 4 | Done |
| PROF-02 | Phase 4 | Done |
| PROF-03 | Phase 4 | Done |
| PROF-04 | Phase 4 | Done |
```

同时更新覆盖计数：
```markdown
**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0
- Satisfied: 18/18  # 新增此行
```

### Anti-Patterns to Avoid

- **不要修改代码：** 本阶段是纯验收，实现已完成
- **不要重新测试：** 70 passed 已通过，只需引用结果
- **不要添加新需求：** 只处理 PROF-01~04 和 CONF-05

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 验收文档格式 | 自创格式 | 复用 Phase 1-3 VERIFICATION.md 模板 | 保持一致性，便于审计 |
| 需求状态更新 | 手动计算 | 直接修改 REQUIREMENTS.md Traceability 表 | 单一事实源 |

**Key insight:** 本阶段无技术复杂度，关键在于**准确引用现有证据**。

## Common Pitfalls

### Pitfall 1: 遗漏需求映射

**What goes wrong:** VERIFICATION.md 没有覆盖全部 5 个需求
**Why it happens:** 没有仔细核对 REQUIREMENTS.md 和 MILESTONE-AUDIT.md
**How to avoid:** 对照 MILESTONE-AUDIT.md 的"gaps.requirements"列表，确保 5 个需求全部在 VERIFICATION.md 中有对应条目
**Warning signs:** summary_score 不是 5/5

### Pitfall 2: 证据引用不完整

**What goes wrong:** Evidence 列没有指向具体测试文件或代码
**Why it happens:** 只写了"已实现"没有具体证据
**How to avoid:** 每个 Requirement 至少引用一个测试文件或 SUMMARY.md
**Warning signs:** Evidence 列只有描述性文字，没有文件路径

### Pitfall 3: REQUIREMENTS.md 更新不完整

**What goes wrong:** 只更新了部分 Traceability 状态
**Why it happens:** 手动编辑遗漏
**How to avoid:** 使用编辑器搜索 "Phase 4 | Pending" 确保全部替换
**Warning signs:** Coverage 计数仍为 13/18 而非 18/18

## Code Examples

### VERIFICATION.md 完整模板

```markdown
---
phase: 04
slug: cli-profile
status: passed
created: 2026-03-08
updated: 2026-03-08
requirements:
  - PROF-01
  - PROF-02
  - PROF-03
  - PROF-04
  - CONF-05
summary_score: 5/5
---

# Phase 04 验证报告

## 结论

Phase 04 已达成目标：CLI 完全收口到 TOML profile，支持 `--profile` 直载、TUI profile 启动页、派生配置和保存确认，且旧 config.json 路径已废弃。

## Goal Check

**阶段目标**：用户通过 Profile 管理已保存配置，支持列表选择、直接加载、派生复制，且 config.json 配置方式已完全移除。

### Must-have 1

**要求**：有已保存 profile 时显示列表快速选择，无 profile 时直接进入向导。

**验证结果**：通过

**证据**：
- `chatgpt_register/tui/app.py` 中 `WizardApp._resolve_start_screen()` 根据_profile_manager.list_profiles()决定起始页
- `chatgpt_register/tui/screens/profile_select.py` 实现列表展示
- `tests/test_tui_profile_screen.py::test_profile_select_shows_when_profiles_exist` 覆盖有 profile 场景
- `tests/test_tui_profile_screen.py::test_profile_select_hidden_when_no_profiles` 覆盖无 profile 场景

### Must-have 2

**要求**：Profile 列表展示名称 + 摘要信息（邮箱平台、上传目标等）。

**验证结果**：通过

**证据**：
- `chatgpt_register/config/profile.py` 中 `ProfileSummary` 类定义摘要字段
- `chatgpt_register/tui/screens/profile_select.py` 消费 `list_profile_summaries()` 展示
- `tests/test_profile_manager.py` 覆盖摘要接口与排序

### Must-have 3

**要求**：支持 `--profile <name>` 参数直接加载 profile 跳过 TUI。

**验证结果**：通过

**证据**：
- `chatgpt_register/cli.py` 中 `--profile` 参数处理
- `tests/test_cli_profile_mode.py::test_profile_flag_loads_and_runs` 覆盖直载成功
- `tests/test_cli_profile_mode.py::test_profile_flag_fails_if_missing` 覆盖失败路径

### Must-have 4

**要求**：用户可基于已有 profile 复制派生新配置。

**验证结果**：通过

**证据**：
- `chatgpt_register/tui/app.py` 中 `derive_profile()` 方法
- `chatgpt_register/tui/screens/profile_select.py` 派生按钮触发
- `tests/test_tui_profile_screen.py::test_derive_profile_prefills_wizard` 覆盖预填

### Must-have 5

**要求**：移除 config.json 配置方式，TUI + TOML 是唯一入口。

**验证结果**：通过

**证据**：
- `chatgpt_register/cli.py` 中 `_warn_legacy_config_if_present()` 仅提示不加载
- `pyproject.toml` 已移除 `questionary` 依赖
- `config.example.json` 已删除
- `tests/test_cli_profile_mode.py::test_legacy_config_warning` 覆盖迁移提示
- `tests/test_sub2api_group_binding.py::test_no_questionary_import` 验证无 questionary 残留

## Requirement Traceability

| Requirement | Result | Evidence |
|-------------|--------|----------|
| PROF-01 | Passed | ProfileSelectScreen + tests/test_tui_profile_screen.py |
| PROF-02 | Passed | ProfileSummary + tests/test_profile_manager.py |
| PROF-03 | Passed | cli.py --profile + tests/test_cli_profile_mode.py |
| PROF-04 | Passed | derive_profile() + tests/test_tui_profile_screen.py |
| CONF-05 | Passed | 迁移提示 + questionary 移除 + tests/test_cli_profile_mode.py |

## Additional Checks

- `uv run pytest tests/ -q` 通过，结果：`70 passed`。
- Phase 4 全部计划 SUMMARY.md 齐全：04-01-SUMMARY.md、04-02-SUMMARY.md、04-03-SUMMARY.md。
- 04-VALIDATION.md 已存在，nyquist_compliant: true。

## Human Verification

无必须阻塞项。当前自动化测试已覆盖全部 Phase 4 需求。

## Final Status

**passed**
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 审计后手动验收 | MILESTONE-AUDIT.md 自动识别缺口 | 2026-03-08 | 验收缺口可视化 |

**Deprecated/outdated:**
- 无

## Open Questions

1. **是否需要创建 05-VERIFICATION.md？**
   - What we know: Phase 5 本身是验收阶段，不需要验收自己的验收
   - What's unclear: 是否需要为 Phase 5 创建自我验收文档
   - Recommendation: 不需要。Phase 5 的完成标志是 Phase 4 VERIFICATION.md 存在且 REQUIREMENTS.md 状态更新。Phase 5 没有"实现需求"，只是文档操作。

## Validation Architecture

> workflow.nyquist_validation 为 true，包含此部分。

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/ -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROF-01 | Profile 启动分流 | integration | `uv run pytest tests/test_tui_profile_screen.py -q` | ✅ |
| PROF-02 | Profile 摘要展示 | unit | `uv run pytest tests/test_profile_manager.py -q` | ✅ |
| PROF-03 | --profile 直载 | integration | `uv run pytest tests/test_cli_profile_mode.py -q` | ✅ |
| PROF-04 | 派生预填 | integration | `uv run pytest tests/test_tui_profile_screen.py -q` | ✅ |
| CONF-05 | config.json 废弃 | regression | `uv run pytest tests/test_cli_profile_mode.py tests/test_sub2api_group_binding.py -q` | ✅ |

### Sampling Rate

- **Phase 5 开始前:** 确认 70 passed 状态
- **无代码变更:** 无需运行测试

### Wave 0 Gaps

None — 本阶段无测试需求，仅引用现有测试结果。

## Sources

### Primary (HIGH confidence)

- `.planning/v1.0-MILESTONE-AUDIT.md` - 里程碑审计结果，识别 5 个 orphaned 需求
- `.planning/phases/04-cli-profile/04-01-SUMMARY.md` - Plan 1 完成证据
- `.planning/phases/04-cli-profile/04-02-SUMMARY.md` - Plan 2 完成证据
- `.planning/phases/04-cli-profile/04-03-SUMMARY.md` - Plan 3 完成证据
- `.planning/phases/04-cli-profile/04-VALIDATION.md` - 验证策略
- `.planning/REQUIREMENTS.md` - 需求追踪表

### Secondary (MEDIUM confidence)

- `.planning/phases/01-config-foundation/01-VERIFICATION.md` - VERIFICATION 模板参考
- `.planning/phases/02-module-split/02-VERIFICATION.md` - VERIFICATION 模板参考
- `.planning/phases/03-tui-config-wizard/03-VERIFICATION.md` - VERIFICATION 模板参考

### Tertiary (LOW confidence)

- 无

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 无技术栈，纯文档操作
- Architecture: HIGH - VERIFICATION.md 格式已由 Phase 1-3 确立
- Pitfalls: HIGH - 基于审计结果，缺口清晰明确

**Research date:** 2026-03-08
**Valid until:** 项目里程碑 v1.0 完成后本阶段自动失效
