---
phase: 04-cli-profile
plan: 03
subsystem: cli
tags: [python, cli, profile, textual, sub2api, toml]
requires:
  - phase: 04-cli-profile
    provides: ProfileSummary 摘要接口、Profile 启动页与保存/派生闭环
provides:
  - Profile-only CLI 启动路由与 `--profile` 直载执行
  - Sub2API 运行阶段的无交互绑定校验
  - README/依赖/示例入口同步收口到 TUI + TOML
affects: [phase-04-cli-profile, cli, profile-runtime, sub2api, docs]
tech-stack:
  added: [无新增第三方库]
  patterns: [profile-only-cli-routing, runtime-sub2api-validation, docs-follow-runtime]
key-files:
  created: [.planning/phases/04-cli-profile/04-03-SUMMARY.md, tests/test_cli_profile_mode.py, tests/test_sub2api_group_binding.py]
  modified: [chatgpt_register/cli.py, chatgpt_register/upload/sub2api.py, pyproject.toml, README.md, tests/test_cli_tui.py, .planning/STATE.md, .planning/ROADMAP.md]
key-decisions:
  - "主 CLI 参数面只保留 `--profile`、`--profiles-dir`、`--non-interactive`，业务配置一律回归 profile。"
  - "运行阶段的 Sub2API 仅校验 profile 中已固化的 `api_base`、凭证和 `group_ids`，缺失时直接失败并回导 TUI 修复。"
  - "仓库对外说明与依赖表面必须跟运行时行为一致，不再把 `config.json` / `questionary` 作为主路径。"
patterns-established:
  - "Pattern 1: CLI 入口先统一输出旧 `config.json` 迁移提示，再按 `--profile` / TTY 条件分流。"
  - "Pattern 2: 交互式配置阶段负责生成完整 profile，运行阶段只接受已完成的上传绑定。"
requirements-completed: [PROF-03, CONF-05]
duration: 10min
completed: 2026-03-08
---

# Phase 04 计划 03 总结

## 一句话总结

CLI 现在已完全收口到 TOML profile：支持 `--profile` 直载执行，Sub2API 运行期不再补问，README 与依赖表面也同步移除了旧 `config.json` / `questionary` 路径暗示。

## 性能

- **Duration:** 10 min
- **Started:** 2026-03-08T08:06:00Z
- **Completed:** 2026-03-08T08:16:34Z
- **Tasks:** 3
- **Files modified:** 10

## 完成事项

- 重写 `chatgpt_register/cli.py`，只保留 `--profile`、`--profiles-dir`、`--non-interactive` 三个入口参数，并把交互式路径统一接到 `WizardApp(profile_manager=...)`。
- 移除 CLI 对 `config.json`、环境变量覆盖与 `input()` 补问的依赖；当前目录若存在 `config.json`，只输出迁移提示，不再自动加载。
- 为 Sub2API 新增纯运行态绑定校验：只接受 profile 中已固化的 `api_base`、凭证与 `group_ids`，缺失时快速失败并提示回到交互式 TUI 修复。
- 新增/更新 CLI 与 Sub2API 测试，覆盖 `--profile` 直载、非交互失败、旧 `config.json` 迁移提示、坏的 Sub2API profile 拦截与无 `questionary` 导入保证。
- 更新 `README.md`、移除 `pyproject.toml` 中的 `questionary` 依赖，并删除 `config.example.json`，让仓库对外表面与当前运行模型保持一致。

## 任务提交

各任务以原子方式提交：

1. **Task 1: 重写 CLI 启动分流为 Profile-only 模式** - `54de4f7` (feat)
2. **Task 2: 清理 Sub2API 运行时交互并固定为配置完成态** - `002c66c` (fix)
3. **Task 3: 清理遗留文档、示例文件与依赖表面** - `560155c` (chore)

**Plan metadata:** 本 summary、`STATE.md` 与 `ROADMAP.md` 会在当前文档提交中统一记录。

## 文件变更

- `chatgpt_register/cli.py` - 重写为 profile-only CLI 入口，统一 `--profile` 与交互式 TUI 分流
- `chatgpt_register/upload/sub2api.py` - 新增无交互运行态绑定校验，删除 `questionary`/`input()` 分支
- `tests/test_cli_tui.py` - 更新交互式 TUI 入口测试，断言注入 `ProfileManager`
- `tests/test_cli_profile_mode.py` - 新增 `--profile`、非交互失败、迁移提示与坏 profile 拦截测试
- `tests/test_sub2api_group_binding.py` - 新增 Sub2API 绑定成功/失败与无 `questionary` 导入测试
- `README.md` - 更新快速开始、CLI 参数、profile 说明、Sub2API 说明与排障路径
- `pyproject.toml` - 移除 `questionary` 运行依赖
- `config.example.json` - 删除旧 JSON 示例入口
- `.planning/phases/04-cli-profile/04-03-SUMMARY.md` - 记录本计划结果与验证
- `.planning/STATE.md` - 更新为 Phase 04 / 全部计划完成状态
- `.planning/ROADMAP.md` - 标记 `04-03` 完成并同步 Phase 1/4 总进度

## 决策记录

- 非交互执行的唯一入口就是 `--profile`；不再保留任何业务型 CLI 覆盖参数，避免 profile 与命令行状态漂移。
- `config.json` 只保留迁移提示，不做自动兼容或静默回退，强制仓库表面和实际行为统一到 TOML profile。
- Sub2API 分组选择继续保留在 TUI 配置阶段，运行阶段只接受完整绑定的 profile，不再把“拉组 + 选择”塞进执行流。

## 偏离计划

无 —— 在用户限定责任文件范围内按计划完成。

## 遇到的问题

- `capsys` 与伪造的 `stdout` 会互相干扰，导致“非交互失败提示”测试读不到输出；通过只伪造 `stdin` 保留 pytest 捕获链解决。

## 用户侧额外操作

无 —— 不需要额外外部服务配置。

## 下一阶段准备度

- Phase 04 全部计划已完成，CLI/TUI/Profile 已形成闭环，可直接进入里程碑审计或验收。
- 仓库仍存在内部 planning 文档中的历史 `config.json` / `questionary` 记录，它们描述的是旧上下文，不影响当前对外运行路径。

## 自检：通过

- `uv run pytest tests/test_cli_tui.py tests/test_cli_profile_mode.py -q` 通过（6 passed）
- `uv run pytest tests/test_cli_profile_mode.py tests/test_sub2api_group_binding.py -q` 通过（6 passed）
- `uv run pytest tests/ -q` 通过（70 passed）
- `uv run python -c "from chatgpt_register.cli import main; print(main.__name__)"` 成功（输出 `main`）
- `rg -n "questionary|config\.example\.json|cp config\.example\.json config\.json|CLI 参数 > 环境变量 > config\.json" README.md pyproject.toml chatgpt_register tests -S` 已确认仅测试断言保留 `questionary` 文案

---
*Phase: 04-cli-profile*
*Completed: 2026-03-08*
