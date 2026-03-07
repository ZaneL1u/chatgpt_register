# Testing Patterns

**Analysis Date:** 2026-03-07

## Test Framework

**Runner:**
- None configured
- No `pytest`, `unittest` test suite, or CI workflow was found

**Assertion Library:**
- None in repository state

**Run Commands:**
```bash
# No committed automated test command exists today
uv run chatgpt-register --help      # Basic CLI smoke check
python codex/protocol_keygen.py     # Manual script execution only, requires local config and dependencies
```

## Test File Organization

**Location:**
- No committed test files or `tests/` directory exist

**Naming:**
- No test naming convention is established yet

**Structure:**
```text
Current repository state:
chatgpt_register.py
codex/protocol_keygen.py
README.md
config.example.json
```

## Test Structure

**Suite Organization:**
- No established `describe` / class / function test layout exists

**Patterns:**
- Verification is currently manual and operator-driven
- README examples and live execution act as de facto smoke testing
- Interactive and network-coupled behavior make the current code harder to test in isolation

## Mocking

**Framework:**
- None configured

**Patterns:**
- No mock fixtures, fake providers, or HTTP stubs are present
- External services are called directly from production code

**What to Mock:**
- OpenAI auth endpoints and OAuth token exchange
- DuckMail / Mail.tm / Mailcow API and IMAP interactions
- CPA and Sub2API upload endpoints
- Time, random values, and filesystem writes for deterministic tests

**What NOT to Mock:**
- Pure parsing helpers such as upload-target parsing and OTP extraction can be tested directly
- Config merge behavior can be tested with temporary files and environment variables

## Fixtures and Factories

**Test Data:**
- None committed
- The codebase would benefit from fixture payloads for provider responses and OAuth redirects

**Location:**
- Recommended future locations: `tests/fixtures/` for API payloads and `tests/factories/` for config / token builders

## Coverage

**Requirements:**
- No target or enforcement exists

**Configuration:**
- No coverage tool configuration found

**View Coverage:**
```bash
# Not available until a test runner is added
```

## Test Types

**Unit Tests:**
- Missing for config parsing, provider selection, OTP extraction, and JWT decode helpers
- These are the lowest-cost starting points

**Integration Tests:**
- Missing for email provider adapters, upload integrations, and batch worker orchestration
- Would require HTTP mocking and IMAP fakes to be reliable

**E2E Tests:**
- None
- Full live registration flows are risky and environment-dependent, so they should stay manual or run in tightly controlled sandboxes

## Common Patterns

**Async / Concurrency Testing:**
- No established pattern exists
- Threaded code in `run_batch()` and shared file writes need dedicated race-safety tests if modified

**Error Testing:**
- No established pattern exists
- High-value future tests should cover missing provider config, failed remote responses, and partial OAuth failure behavior

**Snapshot Testing:**
- Not used

---

*Testing analysis: 2026-03-07*
*Update when test patterns change*
