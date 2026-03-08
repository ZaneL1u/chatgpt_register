---
phase: 02-module-split
plan: 02
subsystem: api
tags: [python, package-split, cli, oauth, adapters, upload, registerconfig]
requires:
  - phase: 02-module-split
    provides: Plan 01 创建的包骨架与 config 子包迁移
provides:
  - core/register.py 中的 ChatGPTRegister 配置驱动注册流程
  - core/batch.py 中的 run_batch(config: RegisterConfig) 并发编排入口
  - cli.py 中的兼容旧 config.json 到 RegisterConfig 的 CLI 入口
  - adapters/ 与 upload/ 子包的独立实现文件
  - 删除旧 chatgpt_register.py 单文件实现
affects: [phase-03-tui, phase-04-cli-profile, register-flow, oauth, upload]
tech-stack:
  added: [无新增第三方库]
  patterns: [配置对象注入, 包结构拆分, 适配器工厂, 无模块级可变全局状态]
key-files:
  created: [chatgpt_register/core/register.py, chatgpt_register/core/batch.py, chatgpt_register/cli.py, chatgpt_register/adapters/duckmail.py, chatgpt_register/upload/sub2api.py]
  modified: [chatgpt_register/__init__.py, chatgpt_register/core/__init__.py, chatgpt_register/adapters/__init__.py, chatgpt_register/upload/__init__.py]
key-decisions:
  - "保留 config.json 兼容加载层于 cli.py，仅作为过渡方案，核心运行路径统一转换为 RegisterConfig。"
  - "run_batch 只接受 RegisterConfig，所有邮箱、OAuth、上传配置均通过配置对象向下传递。"
  - "邮件适配器与上传目标分别通过工厂函数和显式参数注入，避免再依赖模块级可变全局变量。"
patterns-established:
  - "Pattern 1: 顶层 CLI 负责兼容输入格式，核心模块只消费 RegisterConfig。"
  - "Pattern 2: 子模块通过 __init__.py 提供有限导出与工厂入口，避免横向耦合。"
requirements-completed: [ARCH-01]
duration: 15min
completed: 2026-03-08
---

# Phase 02 Plan 02: 模块拆分 Summary

## 一句话总结

将 3217 行单文件拆为 core、adapters、upload 与 cli 多模块包结构，并以 RegisterConfig 作为唯一运行配置入口。

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-07T16:53:35Z
- **Completed:** 2026-03-08T00:00:00Z
- **Tasks:** 3
- **Files modified:** 17

## Accomplishments

- 提取 `utils/http/sentinel/tokens/dashboard` 辅助模块，形成稳定可导入的基础层
- 拆分邮箱适配器与上传目标模块，并改为通过子配置对象和函数参数驱动
- 提取 `ChatGPTRegister`、`run_batch(config)`、`cli.main()`，删除旧 `chatgpt_register.py` 单文件入口

## Task Commits

Each task was committed atomically:

1. **Task 1: 提取辅助模块（utils, http, sentinel, tokens, dashboard）** - `9c01995` (feat)
2. **Task 2: 提取适配器和上传模块** - `3e22e0c` (feat)
3. **Task 3: 提取核心注册类、批处理和 CLI，删除旧文件** - `b21c20c` (feat)

**Plan metadata:** 已完成状态同步，STATE.md / ROADMAP.md / REQUIREMENTS.md 已更新，另有文档收尾提交记录本次执行结果。

## Files Created/Modified

- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/core/utils.py` - 提供文本、随机数据、JWT/URL 解析、验证码提取等通用工具函数
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/core/http.py` - 提供 Chrome 指纹、trace headers、PKCE 和随机延迟
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/core/sentinel.py` - 提供 SentinelTokenGenerator 和 sentinel token 构造能力
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/core/tokens.py` - 提供不依赖全局变量的 token 保存逻辑
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/dashboard.py` - 提供 RuntimeDashboard 与打印路由上下文
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/adapters/base.py` - 提供 EmailAdapter 基类
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/adapters/duckmail.py` - 提供 DuckMailAdapter，构造时注入 DuckMailConfig
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/adapters/mailcow.py` - 提供 MailcowAdapter 与 Mailcow API/IMAP 辅助函数
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/adapters/mailtm.py` - 提供 MailTmAdapter，构造时注入 MailTmConfig
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/upload/common.py` - 提供上传会话和统一分发入口
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/upload/cpa.py` - 提供 CPA 上传实现
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/upload/sub2api.py` - 提供 Sub2API 上传、鉴权与分组绑定逻辑
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/core/register.py` - 提供 ChatGPTRegister 配置驱动注册流程
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/core/batch.py` - 提供 run_batch(config: RegisterConfig) 并发执行入口
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/cli.py` - 提供 CLI 入口与旧配置兼容转换层
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register/__init__.py` - re-export `RegisterConfig` 与 `run_batch`
- `/Users/zaneliu/Projects/open-source/chatgpt_register/chatgpt_register.py` - 已删除旧单文件实现

## Decisions Made

- 保留 `config.json` 到 `RegisterConfig` 的兼容转换，仅放在 `cli.py`，避免污染核心模块。
- `run_batch()` 收敛为单一签名 `run_batch(config: RegisterConfig)`，后续 Phase 3/4 可直接复用。
- Mailcow 清理能力跟随适配器实现，避免在批处理层直接依赖旧式全局函数。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] 本地环境缺少 `tomli_w` 导致模块导入失败**

- **Found during:** Task 2（提取适配器和上传模块）
- **Issue:** 校验导入时，`chatgpt_register.config.profile` 依赖 `tomli_w`，当前环境未安装，导致适配器模块导入链路失败。
- **Fix:** 执行 `uv sync` 安装项目声明依赖后，改用 `uv run python` 完成校验。
- **Files modified:** 无代码文件变更
- **Verification:** `uv run python -c "from chatgpt_register.adapters import build_email_adapter; ...; print('OK')"`
- **Committed in:** `3e22e0c`（任务提交的一部分）

---

**Total deviations:** 1 auto-fixed（Rule 3: 1）
**Impact on plan:** 仅修复执行环境阻塞项，不影响计划范围，且有助于保证验证结果可靠。

## Issues Encountered

- `Read` 工具读取普通文本文件时误传 `pages` 参数导致一次工具调用失败，随后改为正常读取，不影响实现。
- 当前 shell 环境提示 `VIRTUAL_ENV` 与项目 `.venv` 不一致，因此验证统一改用 `uv run`，结果稳定通过。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 可以直接在现有包结构上引入 `tui/` 子包，并复用 `RegisterConfig`、`run_batch(config)`、适配器工厂与上传模块。
- CLI 仍保留旧 `config.json` 兼容层，这是后续 Phase 4 移除旧配置方式时需要替换的最后过渡点。

## Self-Check: PASSED

- 已确认关键产物存在：`chatgpt_register/core/register.py`、`chatgpt_register/core/batch.py`、`chatgpt_register/cli.py`、`chatgpt_register/adapters/duckmail.py`、`chatgpt_register/upload/sub2api.py`
- 已确认任务提交存在：`9c01995`、`3e22e0c`、`b21c20c`

---

*Phase: 02-module-split*
*Completed: 2026-03-08*
