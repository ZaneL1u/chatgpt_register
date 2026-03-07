# Architecture

**Analysis Date:** 2026-03-07

## Pattern Overview

**Overall:** Monolithic Python CLI automation tool with provider adapters and worker-pool concurrency

**Key Characteristics:**
- Single primary executable module `chatgpt_register.py`
- Network-heavy workflow built around direct HTTP session orchestration
- Provider strategy pattern for temporary email backends
- File-based outputs instead of a database or service backend
- Secondary standalone utility `codex/protocol_keygen.py` that overlaps conceptually with the main tool

## Layers

**CLI / Interaction Layer:**
- Purpose: Parse arguments, prompt for optional interactive choices, and print progress
- Contains: `main()`, `_build_cli_parser()`, `_resolve_proxy_from_inputs()`, `_prompt_upload_targets()`, `RuntimeDashboard`
- Depends on: Config globals and batch execution layer
- Used by: User terminal invocation through `chatgpt-register`

**Configuration Layer:**
- Purpose: Merge `config.json`, environment variables, and CLI overrides into runtime globals
- Contains: `_load_config()`, `_apply_cli_overrides()`, provider validation helpers
- Depends on: Local filesystem and environment variables
- Used by: All downstream registration and upload logic

**Execution Layer:**
- Purpose: Coordinate concurrent account registration tasks and summarize outcomes
- Contains: `run_batch()`, `_register_one()` in `chatgpt_register.py`, plus `run_batch()` / `register_one()` in `codex/protocol_keygen.py`
- Depends on: Worker functions, locks, output writers, and external HTTP services
- Used by: CLI entry points only

**Integration Layer:**
- Purpose: Interact with external mail providers, OpenAI endpoints, and upload targets
- Contains: `EmailAdapter` implementations, `ChatGPTRegister`, upload helpers, sentinel-token helpers
- Depends on: `curl-cffi`, `imaplib`, `requests` in the protocol utility, and remote services
- Used by: Execution layer

## Data Flow

**Main registration flow:**
1. User runs `chatgpt-register` from the console script defined in `pyproject.toml`
2. `main()` parses CLI flags and merges them with config and environment values
3. `run_batch()` creates a thread pool and schedules `_register_one()` for each account
4. `_register_one()` builds a `ChatGPTRegister` instance and selects an email adapter via `_build_email_adapter()`
5. The adapter creates a mailbox, polling later for OTP messages
6. `ChatGPTRegister` performs homepage, CSRF, registration, OTP, and account-creation HTTP steps against OpenAI auth endpoints
7. Optional OAuth login runs, tokens are decoded and persisted, and optional CPA / Sub2API uploads fire
8. Results are appended to output files and summarized to the terminal dashboard or plain logs

**State Management:**
- Mostly stateless across runs; runtime state is in memory per process and per worker
- Durable state is just local artifact files written under the repository root
- Global module variables hold config and upload settings for the lifetime of the process

## Key Abstractions

**EmailAdapter:**
- Purpose: Normalize temporary-mail operations across providers
- Examples: `DuckMailAdapter`, `MailcowAdapter`, `MailTmAdapter`
- Pattern: Strategy / adapter object selected from a provider registry

**ChatGPTRegister:**
- Purpose: Encapsulate the main multi-step OpenAI registration and OAuth flow
- Examples: Session creation, sentinel token usage, redirect following, OTP submission
- Pattern: Stateful service object bound to one worker and one HTTP session

**RuntimeDashboard:**
- Purpose: Provide a Rich-based concurrent execution view
- Examples: Summary panel, worker-state table, log panel
- Pattern: In-memory UI state container with synchronized updates

## Entry Points

**Primary CLI entry:**
- Location: `chatgpt_register.py`
- Triggers: `chatgpt-register` console script or `python chatgpt_register.py`
- Responsibilities: Validate config, gather interactive options, run concurrent registration

**Secondary utility entry:**
- Location: `codex/protocol_keygen.py`
- Triggers: Direct script execution
- Responsibilities: Run a parallel HTTP-only registration and OAuth flow, then persist keys

## Error Handling

**Strategy:** Raise exceptions inside integration helpers, catch near worker or CLI boundaries, and print operator-readable messages

**Patterns:**
- Provider and upload config is checked up front with helper functions
- Worker tasks convert failures into `(ok, email, err)` style tuples where possible
- External-call failures are often handled with broad `except Exception` blocks and partial recovery

## Cross-Cutting Concerns

**Logging:**
- Terminal-first logging through `print()` and optional Rich live panels
- Logs focus on step progress and remote response status rather than structured telemetry

**Validation:**
- Manual validation only; no schema library is used for config or API responses
- Provider-specific checks are split across helper functions and runtime branches

**Authentication / Secrets:**
- Credentials and tokens are read from config / env vars and sometimes persisted back to disk
- No encryption, secret redaction, or secret-scoped storage layer exists

---

*Architecture analysis: 2026-03-07*
*Update when major patterns change*
