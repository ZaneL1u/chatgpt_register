# Coding Conventions

**Analysis Date:** 2026-03-07

## Naming Patterns

**Files:**
- Python modules use snake_case filenames such as `chatgpt_register.py` and `protocol_keygen.py`
- Markdown docs use conventional names like `README.md` and `SKILL.md`
- Generated artifacts use descriptive plaintext names such as `registered_accounts.txt`, `ak.txt`, and `rk.txt`

**Functions:**
- Helper functions generally use snake_case
- Internal helper functions often use a leading underscore, for example `_load_config()` and `_prepare_sub2api_group_binding()`
- No separate naming rule for async code because the codebase is synchronous and thread-based

**Variables:**
- Local variables use snake_case
- Module-level config and constants use UPPER_SNAKE_CASE after config hydration, for example `EMAIL_PROVIDER` and `UPLOAD_API_URL`
- Temporary HTTP payload objects and response aliases use short lowercase names such as `resp`, `res`, and `data`

**Types:**
- Type hints are present selectively, not comprehensively
- Classes use PascalCase: `RuntimeDashboard`, `EmailAdapter`, `ChatGPTRegister`, `ProtocolRegistrar`
- There are no custom dataclasses, enums, or typed config models

## Code Style

**Formatting:**
- No formatter config was found
- Existing code uses 4-space indentation and double-quoted strings frequently, but style is not fully uniform
- Large monolithic functions and long files are accepted in the current codebase
- Inline Chinese comments and user-facing Chinese strings are common in the main script

**Linting:**
- No lint configuration or lint command was found
- Style consistency appears to be maintained manually

## Import Organization

**Order:**
1. Python standard library imports
2. Third-party imports
3. Optional third-party imports guarded by `try/except`

**Grouping:**
- Imports are grouped in broad blocks rather than strictly alphabetized by tooling
- Optional Rich import block uses `try/except` to set `RICH_AVAILABLE`

**Path Aliases:**
- None; imports are direct module imports only

## Error Handling

**Patterns:**
- External API and IO boundaries use `try/except Exception` heavily
- Errors are usually converted into human-readable terminal output rather than custom exception types
- Many helper functions return empty lists / `None` on failure instead of raising, especially around mailbox polling

**Error Types:**
- Raise on hard configuration or remote API failures
- Return sentinel values for recoverable polling failures or optional integrations
- Log with enough context for an operator to see provider, step, or status code

## Logging

**Framework:**
- `print()` is the default logging mechanism
- Rich live panels are optional when `rich` is installed and a TTY is available

**Patterns:**
- Progress logs use bracketed tags like `[OAuth]`, `[CPA]`, `[Sub2API]`, and worker identifiers
- Logging is embedded directly in control flow rather than abstracted behind a logger interface
- Shared `_print_lock` is used where concurrent worker output could interleave

## Comments

**When to Comment:**
- Comments explain protocol steps, provider behavior, known edge cases, and operator guidance
- Section-divider comments are used extensively in `codex/protocol_keygen.py`
- Comments are more common around reverse-engineered or fragile HTTP behavior

**Docstrings:**
- Many functions and classes have short Chinese docstrings
- Public / top-level helpers are more likely to be documented than small internal helpers

**TODO Comments:**
- No consistent TODO convention or issue-linking format was observed

## Function Design

**Size:**
- The codebase tolerates very large functions and very large modules
- Feature extraction happens only when repeated behavior is obvious, such as email adapter classes

**Parameters:**
- Primitive-heavy function signatures are common
- Optional behavior is often controlled through boolean flags or module-level globals

**Return Values:**
- Mixed style: tuples for worker results, dicts for decoded payloads, booleans for status helpers
- Guard clauses and early returns are common in config validation and remote-call wrappers

## Module Design

**Exports:**
- Single-file executable modules expose one main entry point plus many internal helpers
- There is no package-level public API layer

**Barrel Files:**
- None; the repository does not use package export modules
- New shared code will likely need manual extraction into new modules if the codebase grows

---

*Convention analysis: 2026-03-07*
*Update when patterns change*
