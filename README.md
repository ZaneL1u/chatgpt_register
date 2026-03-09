# 🤖 ChatGPT Register

批量注册 ChatGPT 账号的命令行工具。支持多种邮箱平台，自动拉取验证码，可选 OAuth 获取 token 并上传到外部平台。

> **声明**：本项目仅用于自动化测试、流程验证与技术研究。请自行确保使用行为符合目标平台条款和当地法规。

## 它能做什么

- **批量注册** — 线程池并发，可配置并发数和代理
- **多邮箱平台** — 支持 DuckMail、Mailcow（自建）、Mail.tm、Catchmail.io、Maildrop.cc
- **自动验证码** — Mailcow 走 IMAP，DuckMail / Mail.tm 走 API
- **OAuth Token** — 注册后自动走完 OAuth 流程，拿到 `access_token` + `refresh_token`
- **Token 上传** — 支持上传到 CPA 平台或 Sub2API
- **交互式向导** — 首次运行引导你填写配置，保存为 TOML profile，下次直接用
- **实时面板** — 基于 rich 的运行面板，显示进度、任务状态和日志

## 快速开始

**环境**：Python >= 3.10，推荐用 [uv](https://github.com/astral-sh/uv)

```bash
# 安装依赖
uv sync

# 首次运行，进入交互式向导
uv run chatgpt-register
```

向导会引导你依次配置：

```text
? 选择操作 › 新建配置
? 邮箱平台 › Mailcow
? Mailcow API URL › mail.example.com
? API Key › ****
? 注册账号数量 › 10
? 并发数 › 3
? 代理地址 (留空跳过) ›
? 上传目标 › Sub2API
? ...
? 保存为 profile? › yes
? Profile 名称 › my-config

✔ 配置已保存
开始注册...
```

配置保存后，下次可以直接用：

```bash
uv run chatgpt-register --profile my-config
```

Profile 默认存储在 `~/.chatgpt-register/profiles/`。

## CLI 参数

```bash
chatgpt-register [--profile NAME] [--profiles-dir PATH] [--non-interactive]
```

| 参数 | 说明 |
| --- | --- |
| `--profile` | 加载指定 profile 直接执行，跳过向导 |
| `--profiles-dir` | 自定义 profile 目录（默认 `~/.chatgpt-register/profiles/`） |
| `--non-interactive` | 非交互模式，必须配合 `--profile` 使用 |

**启动逻辑**：有 `--profile` 就直接跑；没有且终端可交互就启动向导；非交互环境下没给 `--profile` 会报错。

## 邮箱平台

| 平台 | 需要配置 | 验证码获取方式 |
| --- | --- | --- |
| **DuckMail** | API Base + Bearer Token | API 轮询 |
| **Mailcow** | API URL + API Key | IMAP（域名和 IMAP 地址自动推断） |
| **Mail.tm** | API Base | API 轮询 |
| **Catchmail.io** | API Base + 可选域名 | API 轮询 |
| **Maildrop.cc** | GraphQL API Base | GraphQL 查询 |

Mailcow 适合有自建邮箱服务的场景，注册完成后会自动清理临时邮箱。

Catchmail.io 和 Maildrop.cc 是完全免费、无需注册的临时邮箱服务：

- **Catchmail.io** — 提供 6 个域名（`catchmail.io`/`.cc`/`.com`/`.net`/`.org`/`.co`），向导中可勾选启用哪些域名，运行时随机轮换。REST API，无需 API Key。
- **Maildrop.cc** — 固定域名 `maildrop.cc`，GraphQL API，无需 API Key。

> **注意**：Catchmail.io 和 Maildrop.cc 的邮箱是公共共享的（无密码保护），适合快速测试。生产场景建议使用 Mailcow 或 Mail.tm。

## 上传目标

注册成功后，token 可以上传到：

- **CPA** — 通过 multipart POST 上传 token JSON 文件
- **Sub2API** — 通过 API 上传账号，支持分组绑定

两者可以同时启用。Sub2API 的分组绑定（`group_ids`）在向导中会自动拉取可选分组让你选择。

## 输出文件

| 文件 | 内容 |
| --- | --- |
| `registered_accounts.txt` | 注册结果：`邮箱----密码----邮箱密码----oauth状态` |
| `ak.txt` | access_token（每行一个） |
| `rk.txt` | refresh_token（每行一个） |
| `codex_tokens/<email>.json` | 单账号完整 token 数据 |
| `logs/register-*.log` | 运行日志（向导中可选开启） |

文件名和路径都可以在 profile 中自定义。

## Profile 配置

每个 profile 是一个 TOML 文件，包含完整的运行配置。示例：

```toml
[email]
provider = "mailcow"

[email.mailcow]
api_url = "mail.example.com"
api_key = "your-api-key"

[registration]
total_accounts = 10
workers = 3
proxy = ""
output_file = "registered_accounts.txt"
log_file = ""

[oauth]
enabled = true
required = true

[upload]
targets = ["sub2api"]

[upload.sub2api]
api_base = "sub2api.example.com"
admin_api_key = "your-admin-key"
group_ids = [1]
```

**设计原则**：运行时不再接受环境变量覆盖或交互式补问。所有参数在 profile 中固化，确保每次运行结果可复现。

## 项目结构

```text
chatgpt_register/
├── cli.py              # CLI 入口
├── wizard.py           # 交互式向导（questionary）
├── dashboard.py        # 实时面板（rich）
├── config/
│   ├── model.py        # Pydantic 配置模型
│   └── profile.py      # Profile 持久化管理
├── adapters/           # 邮箱适配器
│   ├── base.py         # 基类
│   ├── duckmail.py
│   ├── mailcow.py
│   ├── mailtm.py
│   ├── catchmail.py
│   └── maildrop.py
├── upload/             # Token 上传
│   ├── cpa.py
│   └── sub2api.py
└── core/
    ├── batch.py        # 并发编排
    ├── register.py     # 注册+OAuth 核心流程
    ├── sentinel.py     # Sentinel PoW 求解
    ├── http.py         # HTTP 工具
    └── tokens.py       # Token 保存
```

## 常见问题

**注册成功但 OAuth 失败？**

如果你只需要注册不需要 token，在 profile 里设置：

```toml
[oauth]
enabled = false
```

或者允许 OAuth 失败但不阻塞注册：

```toml
[oauth]
enabled = true
required = false
```

**收不到验证码？**

- Mailcow：检查 IMAP 连通性（默认端口 993/SSL），先单线程跑 1 个账号排查
- DuckMail / Mail.tm：确认 API Base 和凭证正确
- Catchmail.io / Maildrop.cc：确认网络可达，这两个服务无需凭证

**报错 `unsupported_email`？**

OpenAI 拒绝了当前邮箱域名，换一个邮箱平台试试。

**非交互模式报错？**

先跑一次 `uv run chatgpt-register` 创建 profile，然后用 `--profile` 参数指定。

**还有 `config.json`？**

旧版配置已废弃，CLI 不会读取它。请改用向导创建 TOML profile。

## 开发

```bash
# 安装依赖（含开发依赖）
uv sync

# 跑测试
uv run pytest tests/ -q

# 直接运行
uv run chatgpt-register
```

## 贡献

欢迎 PR。提交时请说明变更动机，附上验证步骤。

## 安全提醒

不要把 API Key、Bearer Token、代理凭据或账号数据提交到仓库。Profile 文件存储在用户主目录下（`~/.chatgpt-register/`），不在项目目录中。
