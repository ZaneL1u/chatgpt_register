# Technology Stack

**Analysis Date:** 2026-03-07

## Languages

**Primary:**
- Python 3.10+ - All executable application code in `chatgpt_register.py` and `codex/protocol_keygen.py`

**Secondary:**
- TOML - Project metadata and packaging in `pyproject.toml`
- JSON - Runtime configuration shape in `config.example.json`
- Markdown - User and workflow documentation in `README.md`, `codex/README.md`, and `.codex/`

## Runtime

**Environment:**
- CPython 3.10 or newer - Required by `pyproject.toml`
- Terminal / CLI runtime - Main workflow is a command-line batch tool, not a web app or daemon
- Network access - Required for OpenAI auth endpoints, temporary mail providers, CPA upload, and Sub2API upload

**Package Manager:**
- `uv` - Recommended dependency and command runner in `README.md`
- setuptools - Build backend via `setuptools.build_meta`
- Lockfile: `uv.lock` present

## Frameworks

**Core:**
- None - The main tool is a script-style Python CLI centered on `chatgpt_register.py`

**Testing:**
- None configured in `pyproject.toml`
- No `tests/` directory or test runner config found in the repository

**Build/Dev:**
- setuptools 68+ / wheel - Packaging and console script generation
- `argparse` - CLI argument parsing in `chatgpt_register.py`
- `ThreadPoolExecutor` - Concurrency model for batch registration and protocol key generation

## Key Dependencies

**Critical:**
- `curl-cffi` 0.14.0 - Primary HTTP client with browser impersonation for the main registration flow in `chatgpt_register.py`
- `questionary` 2.1.1 - Interactive terminal menus for upload-target and group selection
- `rich` 14.3.3 - Optional live dashboard for concurrent task progress

**Infrastructure:**
- Python stdlib `imaplib` / `email` - Mailcow IMAP polling and message parsing in `chatgpt_register.py`
- Python stdlib `threading` / `concurrent.futures` - Shared locks and worker pools across both scripts
- Unpackaged imports `requests` and `urllib3` - Used by `codex/protocol_keygen.py` but not declared in `pyproject.toml`

## Configuration

**Environment:**
- Main configuration source is `config.json` beside `chatgpt_register.py`, with environment variables overriding file values
- Key runtime settings include `EMAIL_PROVIDER`, provider credentials, OAuth values, proxy settings, and upload credentials
- Runtime outputs default to `registered_accounts.txt`, `ak.txt`, `rk.txt`, and `codex_tokens/`

**Build:**
- `pyproject.toml` - Packaging metadata, dependency list, console script
- `uv.lock` - Locked dependency graph for reproducible installs
- No linter, formatter, type checker, or test config files found

## Platform Requirements

**Development:**
- macOS / Linux / Windows should work if Python 3.10+ and network access are available
- IMAP reachability is required for Mailcow mode
- Interactive TUI paths require a real TTY and installed optional dependencies

**Production:**
- No deployment target is defined; this is a locally run automation CLI
- Success depends on external service stability and anti-abuse behavior rather than an internal hosting stack

---

*Stack analysis: 2026-03-07*
*Update after major dependency changes*
