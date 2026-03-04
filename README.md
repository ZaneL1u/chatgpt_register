# chatgpt-register

基于 Python 的并发注册脚本，支持多邮箱提供者（`duckmail` / `mailcow` / `mailtm`），可选执行 OAuth 并将 token 落盘或上传到外部平台。

## 声明

- 本项目仅用于自动化测试、流程验证与研究场景。
- 请确保你的使用行为符合目标平台条款、当地法律与团队合规要求。
- 仓库不提供任何规避风控或滥用服务的支持。

## 功能概览

- 并发执行注册任务（线程池）。
- 邮箱适配器架构，支持 DuckMail / Mailcow / Mail.tm。
- 自动拉取邮箱 OTP（Mailcow 走 IMAP，临时邮箱走 API）。
- 可选 OAuth 流程，输出 `access_token` / `refresh_token` / 单账号 JSON。
- 可选上传到 CPA 或 Sub2API。

## 能力边界

- 这是一个脚本型工具，不保证服务端接口长期稳定。
- 受目标站点策略、邮箱域信誉、网络环境影响，成功率存在波动。
- `questionary` 仅用于交互式 TUI 选择（非交互模式无需手动菜单）。

## 快速开始

### 1) 环境要求

- Python `>= 3.10`
- `uv`（推荐）

### 2) 安装依赖

```bash
uv sync
```

### 3) 初始化配置

```bash
cp config.example.json config.json
```

至少设置以下内容：

- `email_provider`
- 对应邮箱提供者的必填字段
- 如需上传 token，再补充上传配置

### 4) 运行

```bash
uv run chatgpt-register
```

查看 CLI 参数：

```bash
uv run chatgpt-register --help
```

## 邮箱提供者配置

### DuckMail

必填：

- `email_provider=duckmail`
- `duckmail_bearer`

可选：

- `duckmail_api_base`（默认 `https://api.duckmail.sbs`）

### Mailcow

必填：

- `email_provider=mailcow`
- `mailcow_api_url`
- `mailcow_api_key`
- `mailcow_domain`

可选：

- `mailcow_imap_host`（不填时尝试从 `mailcow_api_url` 推断）
- `mailcow_imap_port`（默认 `993`）

说明：Mailcow 模式会在任务结束后尝试删除临时邮箱。

### Mail.tm

必填：

- `email_provider=mailtm`

可选：

- `mailtm_api_base`（默认 `https://api.mail.tm`）

## OAuth 与上传

### OAuth

- `enable_oauth=true` 时执行 OAuth。
- `oauth_required=true` 时，OAuth 失败会判定该账号任务失败。
- 输出文件：
  - `ak_file`（access token）
  - `rk_file`（refresh token）
  - `token_json_dir/*.json`（单账号 token 数据）

### 上传目标

`upload_targets` 支持：

- `none`
- `cpa`
- `sub2api`
- `both`（或 `cpa,sub2api`）

当目标包含 `cpa` 时需配置：

- `upload_api_url`
- `upload_api_token`

当目标包含 `sub2api` 时需配置：

- `sub2api_api_base`
- `sub2api_admin_api_key` 或 `sub2api_bearer_token`

Sub2API 需要绑定 `openai` 分组：

- 交互模式：运行时选择分组
- 非交互模式：传 `--sub2api-group-id`，或传 `--sub2api-auto-select-first-group`

## 非交互模式示例

```bash
uv run chatgpt-register \
  --non-interactive \
  --upload-targets sub2api \
  --sub2api-api-base https://sub2api.example.com \
  --sub2api-admin-api-key admin_xxx \
  --sub2api-group-id 6 \
  --proxy http://127.0.0.1:7890 \
  --total-accounts 5 \
  --workers 3
```

## CLI 参数

| 参数 | 说明 |
| --- | --- |
| `--non-interactive` | 非交互运行，不进行输入询问 |
| `--upload-targets` | `none/cpa/sub2api/both`（支持 `cpa,sub2api`） |
| `--proxy` | 代理地址；传空字符串可强制不使用代理 |
| `--total-accounts` | 注册数量（`>0`） |
| `--workers` | 并发数（`>0`） |
| `--sub2api-api-base` | Sub2API 地址 |
| `--sub2api-admin-api-key` | Sub2API Admin API Key（`x-api-key`） |
| `--sub2api-bearer-token` | Sub2API Bearer Token（`Authorization`） |
| `--sub2api-group-id` | Sub2API 分组 ID（openai 平台） |
| `--sub2api-auto-select-first-group` | 非交互且未指定 group-id 时，自动选第一个 openai 分组 |

## 配置优先级

`CLI 参数 > 环境变量 > config.json`。

常用环境变量：

- `EMAIL_PROVIDER`
- `DUCKMAIL_BEARER`
- `MAILCOW_API_URL`
- `MAILCOW_API_KEY`
- `MAILCOW_DOMAIN`
- `MAILTM_API_BASE`
- `PROXY`
- `TOTAL_ACCOUNTS`
- `ENABLE_OAUTH`
- `OAUTH_REQUIRED`
- `UPLOAD_TARGETS`
- `UPLOAD_API_URL`
- `UPLOAD_API_TOKEN`
- `SUB2API_API_BASE`
- `SUB2API_ADMIN_API_KEY`
- `SUB2API_BEARER_TOKEN`
- `SUB2API_GROUP_IDS`

## 输出文件

- `registered_accounts.txt`  
  `email----chatgpt_password----email_password----oauth=ok/fail`
- `ak.txt`（每行一个 `access_token`）
- `rk.txt`（每行一个 `refresh_token`）
- `codex_tokens/<email>.json`

## 故障排查

### `email_provider=duckmail 但未设置 DUCKMAIL_BEARER`

补齐 `duckmail_bearer` 或环境变量 `DUCKMAIL_BEARER`。

### `email_provider=mailcow 但缺少必要配置`

补齐 `mailcow_api_url`、`mailcow_api_key`、`mailcow_domain`。

### `unsupported_email`

目标站点拒绝了当前邮箱域名。建议更换邮箱提供者或先单线程验证。

### 收不到 OTP（尤其 Mailcow）

- 检查 IMAP 连通性（host/port/SSL）。
- 确认邮箱创建成功且能登录。
- 降低并发并先跑 `1` 账号验证链路。

### OAuth 失败但你只关心注册

设置：

```json
{
  "enable_oauth": true,
  "oauth_required": false
}
```

## 目录说明

- `chatgpt_register.py`：主程序入口
- `config.example.json`：配置示例
- `codex/protocol_keygen.py`：独立工具（非主流程）

## 贡献

欢迎提交 PR。建议包含：

- 变更动机与影响范围
- 配置/兼容性说明
- 最小复现与验证步骤

## 安全

不要将以下内容提交到仓库：

- 任意 API Key / Bearer Token
- 可复用的代理凭据
- 生产环境账号数据

如发现安全问题，请通过私下渠道联系维护者。
