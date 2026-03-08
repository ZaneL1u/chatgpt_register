---
phase: 01-config-foundation
plan: 01
subsystem: config
tags: [pydantic, validation, data-model]

requires:
  - phase: none
    provides: first plan, no dependencies
provides:
  - RegisterConfig Pydantic v2 数据模型
  - 所有子模型（EmailConfig, RegConfig, OAuthConfig, UploadConfig, DuckMailConfig, MailcowConfig, MailTmConfig, CpaConfig, Sub2ApiConfig）
  - format_validation_errors() 中文错误格式化函数
  - 共享测试 fixtures (conftest.py)
affects: [01-02, phase-2, tui]

tech-stack:
  added: [pydantic>=2.12, tomli-w>=1.2, pytest]
  patterns: [nested-sub-models, model-validator-linkage, field-validator-normalize]

key-files:
  created:
    - config_model.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_config_model.py
  modified:
    - pyproject.toml

key-decisions:
  - "使用 Field(default_factory=...) 而非直接赋值，避免可变默认值问题"
  - "provider 通过 field_validator(mode='before') 做小写规范化"
  - "model_validator(mode='after') 实现 provider-config 和 targets-config 联动校验"

patterns-established:
  - "嵌套子模型模式: 顶层 RegisterConfig 包含 EmailConfig/RegConfig/OAuthConfig/UploadConfig"
  - "联动校验模式: model_validator 检查字段间一致性并抛出中文 ValueError"
  - "TOML 兼容序列化: model_dump(mode='json', exclude_none=True)"

requirements-completed: [CONF-03, ARCH-02]

duration: ~8min
completed: 2026-03-07
---

# Plan 01-01: RegisterConfig 数据模型 Summary

**Pydantic v2 嵌套子模型覆盖全部 20+ 全局变量，含邮箱平台/上传目标联动校验和中文错误消息**

## Performance

- **Duration:** ~8 min
- **Tasks:** 2
- **Files created:** 4
- **Files modified:** 1

## Accomplishments
- RegisterConfig 及 9 个子模型完整实现，覆盖 chatgpt_register.py:414-443 全部全局变量
- 邮箱平台联动校验：选择 provider 但缺少对应配置节时报中文错误
- 上传目标联动校验：targets 列表与对应子模型不匹配时报中文错误
- 14 个测试用例全部通过，TDD 流程完整（RED → GREEN）

## Task Commits

1. **Task 1: 安装依赖并创建测试基础设施** - `9e8c51d` (chore)
2. **Task 2 RED: 编写失败测试** - `8349cd2` (test)
3. **Task 2 GREEN: 实现 RegisterConfig** - `794a788` (feat)

## Files Created/Modified
- `config_model.py` - RegisterConfig + 所有子模型 + format_validation_errors
- `tests/__init__.py` - 测试包标记
- `tests/conftest.py` - 共享 fixtures（sample_duckmail_dict 等）
- `tests/test_config_model.py` - 14 个测试用例
- `pyproject.toml` - 新增 pydantic, tomli-w, pytest 依赖

## Decisions Made
None - 严格按照 PLAN.md 和 RESEARCH.md 骨架实现

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- config_model.py 已就绪，Plan 01-02 的 ProfileManager 可直接 import RegisterConfig
- 共享 fixtures 已在 conftest.py 中准备好，Plan 01-02 可直接使用

---
*Phase: 01-config-foundation*
*Completed: 2026-03-07*
