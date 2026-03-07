# External Integrations

**Analysis Date:** 2026-03-07

## APIs & External Services

**Primary target service:**
- OpenAI / ChatGPT auth endpoints - Registration and OAuth token exchange
  - Integration method: Direct HTTP flows in `chatgpt_register.py` and `codex/protocol_keygen.py`
  - Auth: Cookies, PKCE values, sentinel challenge responses, and OAuth client credentials
  - Endpoints used: `/oauth/authorize`, `/oauth/token`, account continuation / registration / OTP endpoints on `https://auth.openai.com`

**Temporary email providers:**
- DuckMail - Temporary mailbox creation and message polling
  - SDK/Client: `curl-cffi` session in `chatgpt_register.py`
  - Auth: Bearer token from `DUCKMAIL_BEARER`
  - Endpoints used: `/accounts`, `/token`, `/messages`
- Mail.tm - Temporary mailbox creation and message polling
  - SDK/Client: `curl-cffi` session in `chatgpt_register.py`
  - Auth: Provider-issued mailbox token
  - Endpoints used: `/domains`, `/accounts`, `/token`, `/messages`
- Mailcow - Self-hosted mailbox lifecycle
  - Integration method: REST mailbox management plus IMAP inbox polling
  - Auth: `X-API-Key` for API and mailbox password for IMAP
  - Endpoints used: `/api/v1/add/mailbox`, `/api/v1/delete/mailbox`

**Upload targets:**
- CPA management platform - Optional token JSON upload from `chatgpt_register.py`
  - Integration method: Multipart HTTP POST using `curl-cffi`
  - Auth: Bearer token from `upload_api_token`
  - Payload: Generated token JSON file
- Sub2API - Optional account creation from OAuth token data
  - Integration method: JSON REST API via `curl-cffi`
  - Auth: `x-api-key` or bearer token
  - Endpoints used: `/api/v1/admin/groups`, `/api/v1/admin/accounts`

## Data Storage

**Databases:**
- None - No internal database or ORM exists in this repository

**File Storage:**
- Local filesystem - Outputs and token artifacts are written to files beside the script
  - Files: `registered_accounts.txt`, `ak.txt`, `rk.txt`, `codex_tokens/*.json`
  - Auth: OS-level filesystem permissions only

**Caching:**
- None - State is held in memory during execution only

## Authentication & Identity

**Auth Provider:**
- OpenAI auth service - Handles account registration, login continuation, OTP validation, and OAuth token issuance
  - Implementation: Custom HTTP request sequencing with cookies, PKCE, and sentinel token generation
  - Token storage: Plaintext files and JSON files on disk
  - Session management: In-memory HTTP session cookies per worker

**OAuth Integrations:**
- OpenAI OAuth client - Uses configured `oauth_client_id` and redirect URI
  - Credentials: `oauth_client_id`, `oauth_redirect_uri`, and runtime session state
  - Scopes: Implicitly tied to ChatGPT / Codex token issuance workflow in code

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracker integration found

**Analytics:**
- None

**Logs:**
- stdout / stderr only
  - Integration: Plain `print()` calls or Rich live dashboard panels in `chatgpt_register.py`

## CI/CD & Deployment

**Hosting:**
- None - No service deployment manifests or runtime hosting config found

**CI Pipeline:**
- None - No GitHub Actions, CI configs, or release pipeline files found

## Environment Configuration

**Development:**
- Required secrets vary by chosen mail provider and upload target
- Secrets location: `config.json`, environment variables, or CLI flags
- Mock / stub services: None implemented

**Staging:**
- No separate staging environment conventions defined in repo docs or code

**Production:**
- Secrets are expected to stay local and gitignored via `.gitignore`
- No centralized secret manager integration exists

## Webhooks & Callbacks

**Incoming:**
- OAuth redirect callback - `http://localhost:1455/auth/callback` is used as the redirect URI in config defaults
  - Verification: Code extracts `code` query param from redirect URLs
  - Events: OAuth authorization completion only

**Outgoing:**
- CPA upload call - Triggered after token JSON is written
  - Retry logic: None beyond request-level exception handling
- Sub2API account creation - Triggered after token generation when enabled
  - Retry logic: None beyond request-level exception handling

---

*Integration audit: 2026-03-07*
*Update when adding/removing external services*
