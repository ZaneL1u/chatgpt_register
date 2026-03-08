# chatgpt-register

基于 Python 的批量注册工具，支持多邮箱提供者（`duckmail` / `mailcow` / `mailtm`），可选执行 OAuth，并将 token 落盘或上传到外部平台。

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
- 交互式问答向导与 TOML profile 持久化。

## 能力边界

- 这是一个脚本型工具，不保证服务端接口长期稳定。
- 受目标站点策略、邮箱域信誉、网络环境影响，成功率存在波动。
- 主 CLI 已完全切换到 `交互式向导 + TOML profile`；`config.json`、环境变量覆盖和运行时补问都已废弃。

## 快速开始

### 1) 环境要求

- Python `>= 3.10`
- `uv`（推荐）

### 2) 安装依赖

```bash
uv sync
```

### 3) 首次创建 profile

```bash
uv run chatgpt-register
```

首次进入后会启动交互式向导。按步骤填写：

- 邮箱平台与对应凭证
- 注册数量、并发、代理
- 上传目标（CPA / Sub2API）
- 确认后保存为 TOML profile

默认 profile 目录：`~/.chatgpt-register/profiles/`

### 4) 运行已保存 profile

```bash
uv run chatgpt-register --profile your-profile-name
```

自动化/CI 场景建议显式加上：

```bash
uv run chatgpt-register --non-interactive --profile your-profile-name
```

如果 profile 不在默认目录，可指定：

```bash
uv run chatgpt-register --profile your-profile-name --profiles-dir /path/to/profiles
```

## CLI 参数

| 参数 | 说明 |
| --- | --- |
| `--profile` | 直接加载指定 TOML profile 并执行 |
| `--profiles-dir` | 指定 profile 存储目录（默认 `~/.chatgpt-register/profiles/`） |
| `--non-interactive` | 禁止交互；未传 `--profile` 时直接失败 |

### 启动路由

- 传入 `--profile`：直接加载 profile 并执行，不进入向导。
- 未传 `--profile` 且当前终端可交互：启动向导，可选择已有 profile、创建新 profile 或基于已有 profile 派生。
- 非交互终端或显式 `--non-interactive`：必须提供 `--profile`。

## Profile 说明

每个 profile 都是一个 TOML 文件，运行期不再接受额外业务参数覆盖。也就是说：

- 不再从 `config.json` 读取配置
- 不再读取环境变量来覆盖 profile
- 不再通过 `input()` 补齐代理、数量、并发或上传凭证

如果当前目录仍有 `config.json`，CLI 只会输出迁移提示，不会自动加载。

## 邮箱与上传配置

### 邮箱提供者

- `duckmail`：需要 bearer token
- `mailcow`：需要 API URL 和 API Key（域名、IMAP 信息自动推断）
- `mailtm`：使用 API Base 即可

这些信息都在向导中录入，并最终保存在 TOML profile 中。

### OAuth 输出

运行后会按 profile 中的注册配置输出：

- `registered_accounts.txt`
- `ak.txt`
- `rk.txt`
- `codex_tokens/<email>.json`

文件名和目录同样由 profile 的 `registration` 配置决定。

### Sub2API

Sub2API 的 `api_base`、凭证和 `group_ids` 必须在保存 profile 时就已经完整固化。

运行阶段只会做校验，不会再：

- 询问 Sub2API 地址
- 询问 Admin API Key / Bearer Token
- 运行时拉取分组后让你再选一次

如果 profile 中缺少 Sub2API 分组绑定，CLI 会快速失败，并提示你回到向导修复该 profile。

## 故障排查

### 非交互模式报错：必须提供 `--profile`

这是预期行为。请先运行：

```bash
uv run chatgpt-register
```

完成一次交互式创建并保存 profile，随后再使用：

```bash
uv run chatgpt-register --non-interactive --profile your-profile-name
```

### 当前目录还有 `config.json`

这是旧路径残留。CLI 只会提示迁移，不会再读取它。请改用 TOML profile。

### Sub2API 缺少分组绑定

用向导打开该 profile，重新选择 Sub2API 的 openai 分组并保存，然后再执行 `--profile`。

### `unsupported_email`

目标站点拒绝了当前邮箱域名。建议更换邮箱提供者或先单线程验证。

### 收不到 OTP（尤其 Mailcow）

- 检查 IMAP 连通性（host/port/SSL）。
- 确认邮箱创建成功且能登录。
- 降低并发并先跑 `1` 个账号验证链路。

### OAuth 失败但你只关心注册

请在 profile TOML 中设置 `oauth.required = false`，保存后再运行。

## 目录说明

- `chatgpt_register/cli.py`：主 CLI 入口
- `chatgpt_register/wizard.py`：交互式配置向导
- `chatgpt_register/config/profile.py`：TOML profile 管理
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
