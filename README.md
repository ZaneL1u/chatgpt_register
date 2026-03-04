# ChatGPT 批量自动注册工具

一个支持并发注册的 Python 脚本，支持多种邮箱来源：

- `duckmail`：DuckMail API 临时邮箱
- `mailcow`：自建 Mailcow（API 创建邮箱 + IMAP 收验证码）
- `mailtm`：Mail.tm 公共 API 临时邮箱

## Fork 说明

这份 Fork 在原版基础上，新增并完善了 `mailcow` 注册链路：

- 注册前通过 Mailcow API 自动创建邮箱
- 注册时通过 IMAP 自动拉取 OTP 验证码
- 注册后自动删除临时邮箱，减少邮箱配额占用
- 新增邮箱适配器层，可切换 `mailtm`

## 适用人群

- 小白：照着文档一步一步跑通 1 个账号
- 熟手：用环境变量和并发参数批量跑
- 运维/站长：接入自建 Mailcow，减少第三方依赖

## 你会得到什么

- 自动完成注册流程（含邮箱验证码）
- 可选执行 OAuth 并保存 token
- 可选上传 token JSON 到 CPA 面板
- 多线程并发，提高批量效率

## 目录

- [1. 环境准备](#1-环境准备)
- [2. 安装与启动](#2-安装与启动)
- [3. 小白路线A用-DuckMail-跑通](#3-小白路线a用-duckmail-跑通)
- [4. 小白路线B用-Mailcow-跑通](#4-小白路线b用-mailcow-跑通)
- [5. 运行时会问你什么](#5-运行时会问你什么)
- [6. 配置项详解](#6-配置项详解)
- [7. 环境变量覆盖](#7-环境变量覆盖)
- [8. 输出文件说明](#8-输出文件说明)
- [9. 常见报错与排查](#9-常见报错与排查)
- [10. 进阶用法大佬速查](#10-进阶用法大佬速查)
- [11. 安全建议](#11-安全建议)
- [12. 相关链接](#12-相关链接)

## 1. 环境准备

### 系统与软件

- Python `3.10+`
- `uv`（Python 包与虚拟环境管理）
- 可访问目标站点的网络环境（必要时配代理）

### 安装依赖

```bash
uv sync
```

## 2. 安装与启动

### 入口说明（统一口径）

- 默认给用户的运行命令只有一个：`uv run chatgpt-register`
- 该命令读取仓库根目录的 `config.json`（即与 `chatgpt_register.py` 同级）
- `codex/protocol_keygen.py` 属于子目录下的独立工具，不是本 README 的常规使用入口

### 第一步：复制配置文件

Linux/macOS:

```bash
cp config.example.json config.json
```

Windows:

```bat
copy config.example.json config.json
```

### 第二步：编辑 `config.json`

至少先把你选的邮箱提供者配置好（DuckMail / Mailcow / Mail.tm）。

### 第三步：运行脚本

```bash
uv run chatgpt-register
```

查看命令行帮助：

```bash
uv run chatgpt-register --help
```

脚本会交互询问：

- Token 上传目标（支持 TUI：`↑/↓` 选择，`Enter` 确认）
- 代理地址
- 注册数量
- 并发数

说明：TUI 选择依赖 `questionary`，未安装时脚本会直接报错退出（不再回退为手动输入序号）。

## 3. 小白路线A：用 DuckMail 跑通

> 推荐先用这一条做首跑验证。先跑 1 个账号、并发 1，确认链路正常后再放量。

### 步骤 1：在 DuckMail 获取 API Key（LinuxDo 登录）

1. 打开 `https://domain.duckmail.sbs`
2. 点击 `使用 LinuxDo 登录`（页面文案可能微调，但含义相同）
3. 在 LinuxDo 授权页完成登录与授权
4. 回到 DuckMail 管理页，进入 `API Key` 页面
5. 新建并复制你的 Key（通常是 `dk_` 前缀）

### 步骤 2：填写 `config.json`

```json
{
  "email_provider": "duckmail",
  "duckmail_api_base": "https://api.duckmail.sbs",
  "duckmail_bearer": "dk_xxx"
}
```

说明：

- 这个 Fork 的 DuckMail 流程要求 `duckmail_bearer` 非空
- 若你不填，会在启动和执行时提示 `DUCKMAIL_BEARER 未设置`

### 步骤 3：先做 API 连通性自检（推荐）

```bash
curl -s https://api.duckmail.sbs/domains \
  -H "Authorization: Bearer dk_xxx"
```

看到 JSON（常见含 `hydra:member`）即为可用。

### 步骤 4：正式跑脚本

```bash
uv run chatgpt-register
```

第一次建议输入：

- 代理：按你的网络实际填写，不确定就先回车
- 注册数量：`1`
- 并发数：`1`

### 步骤 5：确认结果

至少会看到以下之一：

- 成功：终端出现 `[OK]`，并写入 `registered_accounts.txt`
- 失败：终端出现 `[FAIL]`，根据报错去看 [9. 常见报错与排查](#9-常见报错与排查)

## 4. 小白路线B：用 Mailcow 跑通

> 适合已有 Mailcow 站点的用户。建议先确保 API 与 IMAP 都可用。

### 前置条件

- 你有可访问的 Mailcow 地址，例如 `https://mail.example.com`
- 你有 Mailcow API Key
- 你有可用于创建邮箱的域名，例如 `example.com`
- IMAP 可连通（默认 `993`，SSL）

### 步骤 1：填写 `config.json`

```json
{
  "email_provider": "mailcow",
  "mailcow_api_url": "https://mail.example.com",
  "mailcow_api_key": "YOUR_MAILCOW_API_KEY",
  "mailcow_domain": "example.com",
  "mailcow_imap_host": "mail.example.com",
  "mailcow_imap_port": 993
}
```

### 步骤 2：建议先做 API 自检

先验证 API 地址可达，且 Key 有权限创建邮箱。

```bash
curl -I https://mail.example.com
```

### 步骤 3：运行脚本

```bash
uv run chatgpt-register
```

建议首跑参数：

- 注册数量：`1`
- 并发数：`1`

### 步骤 4：确认清理逻辑

Mailcow 模式下，脚本在任务结束后会尝试删除临时邮箱。你会在日志看到：

- `已清理临时邮箱`：清理成功
- `清理邮箱失败`：清理失败，可手动删除

## 5. 运行时会问你什么

脚本交互顺序如下：

1. Token 上传目标（`none/cpa/sub2api/both`，默认读配置）
2. 若包含 `sub2api`：拉取 `openai` 分组并让你选择一个分组
3. 代理设置
4. 注册账号数量（默认读取 `config.json` 的 `total_accounts`）
5. 并发数（默认 `3`）

也支持非交互参数（适合脚本化/CI），例如：

```bash
uv run chatgpt-register \
  --non-interactive \
  --upload-targets sub2api \
  --sub2api-api-base https://sub2api.example.com \
  --sub2api-admin-api-key admin_xxx \
  --sub2api-group-id 6 \
  --total-accounts 5 \
  --workers 3
```

代理输入示例：

- `http://127.0.0.1:7890`
- `socks5://127.0.0.1:7890`
- 直接回车表示不使用代理

## 6. 配置项详解

默认配置见 `config.example.json`。下面是核心字段：

| 配置项 | 默认值 | 何时必填 | 作用 |
|---|---:|---|---|
| `total_accounts` | `3` | 否 | 默认注册数量（交互时可改） |
| `email_provider` | `mailtm` | 是 | 邮箱来源：`duckmail` / `mailcow` / `mailtm` |
| `duckmail_api_base` | `https://api.duckmail.sbs` | DuckMail 必填 | DuckMail API 基础地址 |
| `duckmail_bearer` | `""` | DuckMail 必填 | DuckMail API Token |
| `mailcow_api_url` | `""` | Mailcow 必填 | Mailcow API 地址 |
| `mailcow_api_key` | `""` | Mailcow 必填 | Mailcow API Key |
| `mailcow_domain` | `""` | Mailcow 必填 | 创建邮箱所用域名 |
| `mailcow_imap_host` | `""` | Mailcow 建议填 | IMAP 主机，不填时尝试从 `mailcow_api_url` 推断 |
| `mailcow_imap_port` | `993` | Mailcow 可选 | IMAP 端口 |
| `mailtm_api_base` | `https://api.mail.tm` | Mail.tm 可选 | Mail.tm API 基础地址 |
| `proxy` | `""` | 否 | 默认代理（交互时可改） |
| `output_file` | `registered_accounts.txt` | 否 | 注册结果输出文件 |
| `enable_oauth` | `true` | 否 | 是否执行 OAuth 获取 token |
| `oauth_required` | `true` | 否 | OAuth 失败是否判定整个注册失败 |
| `oauth_issuer` | `https://auth.openai.com` | OAuth 开启时建议保留默认 | OAuth 发行方地址 |
| `oauth_client_id` | `app_EMoamEEZ73f0CkXaXp7hrann` | OAuth 开启时建议保留默认 | OAuth Client ID |
| `oauth_redirect_uri` | `http://localhost:1455/auth/callback` | OAuth 开启时建议保留默认 | OAuth 回调地址 |
| `ak_file` | `ak.txt` | 否 | Access Token 输出文件 |
| `rk_file` | `rk.txt` | 否 | Refresh Token 输出文件 |
| `token_json_dir` | `codex_tokens` | 否 | 单账号 token JSON 输出目录 |
| `upload_targets` | `cpa` | 否 | 上传目标：`none` / `cpa` / `sub2api` / `both`（也支持 `cpa,sub2api`） |
| `upload_api_url` | `""` | 仅上传时必填 | CPA 上传 API 地址 |
| `upload_api_token` | `""` | 仅上传时必填 | CPA 上传 Bearer Token |
| `sub2api_api_base` | `""` | 上传到 Sub2API 时必填 | Sub2API 基础地址（如 `https://sub2api.example.com`） |
| `sub2api_admin_api_key` | `""` | Sub2API 推荐填写其一 | Sub2API Admin API Key（请求头 `x-api-key`） |
| `sub2api_bearer_token` | `""` | Sub2API 备选填写其一 | Sub2API Bearer Token（请求头 `Authorization`） |
| `sub2api_group_ids` | `[]` | 否 | 创建 Sub2API 账号时绑定的分组 ID 列表 |
| `sub2api_account_concurrency` | `1` | 否 | 创建 Sub2API 账号时的并发值 |
| `sub2api_account_priority` | `1` | 否 | 创建 Sub2API 账号时的优先级 |

## 7. 环境变量覆盖

环境变量优先级高于 `config.json`。支持：

- `EMAIL_PROVIDER`
- `DUCKMAIL_API_BASE`
- `DUCKMAIL_BEARER`
- `MAILCOW_API_URL`
- `MAILCOW_API_KEY`
- `MAILCOW_DOMAIN`
- `MAILCOW_IMAP_HOST`
- `MAILCOW_IMAP_PORT`
- `MAILTM_API_BASE`
- `PROXY`
- `TOTAL_ACCOUNTS`
- `ENABLE_OAUTH`
- `OAUTH_REQUIRED`
- `OAUTH_ISSUER`
- `OAUTH_CLIENT_ID`
- `OAUTH_REDIRECT_URI`
- `AK_FILE`
- `RK_FILE`
- `TOKEN_JSON_DIR`
- `UPLOAD_TARGETS`
- `UPLOAD_API_URL`
- `UPLOAD_API_TOKEN`
- `SUB2API_API_BASE`
- `SUB2API_ADMIN_API_KEY`
- `SUB2API_BEARER_TOKEN`
- `SUB2API_GROUP_IDS`（逗号分隔，例如 `1,2,3`）
- `SUB2API_ACCOUNT_CONCURRENCY`
- `SUB2API_ACCOUNT_PRIORITY`

示例（DuckMail）：

```bash
export EMAIL_PROVIDER=duckmail
export DUCKMAIL_API_BASE=https://api.duckmail.sbs
export DUCKMAIL_BEARER=dk_xxx
export TOTAL_ACCOUNTS=5
uv run chatgpt-register
```

示例（Mailcow）：

```bash
export EMAIL_PROVIDER=mailcow
export MAILCOW_API_URL=https://mail.example.com
export MAILCOW_API_KEY=xxxx
export MAILCOW_DOMAIN=example.com
export MAILCOW_IMAP_HOST=mail.example.com
export MAILCOW_IMAP_PORT=993
uv run chatgpt-register
```

示例（Mail.tm）：

```bash
export EMAIL_PROVIDER=mailtm
export MAILTM_API_BASE=https://api.mail.tm
export TOTAL_ACCOUNTS=3
uv run chatgpt-register
```

## 8. 输出文件说明

- `registered_accounts.txt`
  - 格式：`邮箱----ChatGPT密码----邮箱密码----oauth=ok/fail`
- `ak.txt`
  - 每行一个 `access_token`
- `rk.txt`
  - 每行一个 `refresh_token`
- `codex_tokens/*.json`
  - 每个账号一个 JSON 文件，含 access/refresh 等字段

## 9. 常见报错与排查

### 1) `❌ 错误: email_provider=duckmail 但未设置 DUCKMAIL_BEARER`

原因：DuckMail 模式没填 `duckmail_bearer`。  
处理：补全 `config.json` 或导出 `DUCKMAIL_BEARER`。

### 2) `❌ 错误: email_provider=mailcow 但缺少必要配置`

原因：缺少 `mailcow_api_url / mailcow_api_key / mailcow_domain` 中的一项或多项。  
处理：补全三项后重试。

### 3) `curl: (28) Connection timed out`

原因：网络超时，常见于代理不可用、并发过高、链路波动。  
处理：

- 并发先降到 `1-2`
- 检查代理可用性
- 先测试：

```bash
curl -I https://chatgpt.com --max-time 10
```

### 4) `Create account 失败 ... unsupported_email`

原因：OpenAI 拒绝了该邮箱域名（常见于部分临时邮箱域）。  
处理：

- 切换到 `mailtm` / `duckmail` / `mailcow`
- 降并发到 `1` 先做单账号验证

### 5) Mailcow 收不到 OTP

处理顺序：

1. 确认 `mailcow_imap_host`、`mailcow_imap_port` 可连通
2. 确认 Mailcow API 创建邮箱成功
3. 确认 IMAP 登录未被策略拦截
4. 将并发降到 `1` 先做单账号验证

### 6) OAuth 获取失败

如果你只关心注册成功，不强制 token，可设置：

```json
{
  "enable_oauth": true,
  "oauth_required": false
}
```

这样 OAuth 失败不会让整条注册任务直接判定失败。

## 10. 进阶用法（大佬速查）

### 最小可用压测策略

1. 先用 `1` 账号、`1` 并发跑通
2. 再升到 `3-5` 并发观察失败率
3. 失败率明显升高就回退并发

### 无状态部署建议

- 用环境变量注入敏感配置，不把密钥写入仓库
- 将输出目录挂载到持久卷，避免容器重启丢数据
- 对 `registered_accounts.txt` 与 token 文件做外部归档

### Token 自动上传（CPA / Sub2API / 双传）

通过 `upload_targets` 控制上传目标：

- `none`：不上传
- `cpa`：只传 CPA
- `sub2api`：只传 Sub2API
- `both` 或 `cpa,sub2api`：两个都传

对应配置要求：

- 传 CPA：`upload_api_url` + `upload_api_token`
- 传 Sub2API：`sub2api_api_base` + (`sub2api_admin_api_key` 或 `sub2api_bearer_token`)

Sub2API 上传方式为调用其 Admin API 创建 `platform=openai`、`type=oauth` 账号。
运行时会先拉取 `openai` 分组并让你选一个；若没有 `openai` 分组，脚本会提示先去 Sub2API 后台新建分组再重试。

## 11. 相关链接

- DuckMail 域名管理：`https://domain.duckmail.sbs`
- DuckMail API：`https://api.duckmail.sbs`
- Sub2API 仓库：`https://github.com/Wei-Shaw/sub2api`
- CPA 文档：`https://help.router-for.me/cn/`
- CPA 面板仓库：`https://github.com/dongshuyan/CPA-Dashboard`
