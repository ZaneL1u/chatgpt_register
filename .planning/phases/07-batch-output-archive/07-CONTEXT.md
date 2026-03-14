# Phase 7: 批次输出归档 - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

每次注册批次完成后，所有结果文件（registered_accounts.txt、ak.txt、rk.txt、codex_tokens/）自动写入 `output/YYYYMMDD_HHMM/` 归档子目录，不再追加到同一文件。多次运行产生独立归档目录，历史结果不被覆盖。

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

以下决策均由用户委托 Claude 自行决定：

**归档目录策略：**
- 在 `run_batch()` 开始时创建归档目录 `output/YYYYMMDD_HHMM/`，所有文件直接写入该目录
- 时间戳使用本地时间（与现有日志时间一致）
- 同一分钟内多次运行时追加 `_N` 后缀（如 `20260315_1430_2`）
- 日志文件（log_file）也一并写入归档目录

**配置与兼容性：**
- 归档行为默认开启，无需额外开关
- `RegConfig` 中的 `output_file`、`ak_file`、`rk_file`、`token_json_dir` 字段仅作为文件名使用（忽略路径前缀），实际写入归档目录
- `output/` 前缀固定，不提供额外配置项（保持简单）
- 旧配置无需修改即可生效

**归档后的用户反馈：**
- 注册完成后终端摘要中显示归档目录完整路径
- Dashboard 面板启动时显示当前归档目录路径

**历史数据迁移：**
- 不处理已存在的旧格式结果文件
- 只影响新运行，旧文件保留原位

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RegConfig` (config/model.py): 已有 output_file、ak_file、rk_file、token_json_dir 字段，可复用为文件名来源
- `save_codex_tokens()` (core/tokens.py): 接受文件路径参数，改传归档路径即可
- `_open_log_file()` (core/batch.py): 已支持自动创建父目录

### Established Patterns
- 文件写入全部通过 `file_lock` 线程锁保护
- 路径构造使用 `os.path` 和 `Path`
- 配置字段通过 Pydantic model 管理

### Integration Points
- `run_batch()` (core/batch.py:150): 主入口，需在此创建归档目录并修改所有文件路径
- `_register_one()` (core/batch.py:60): 接收 output_file 参数，需传入归档路径
- `ChatGPTRegister.save_tokens()` (core/register.py:956): 内部调用 save_codex_tokens，需传入归档路径下的 ak/rk/token_json_dir

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-batch-output-archive*
*Context gathered: 2026-03-15*
