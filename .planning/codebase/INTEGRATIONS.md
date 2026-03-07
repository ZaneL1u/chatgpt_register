# 外部集成

**分析日期：** 2026-03-07

## API 与外部服务

**目标认证服务：**
- OpenAI / ChatGPT 认证端点：负责注册、登录续接、OTP 验证与 OAuth token 交换
  - 集成方式：`chatgpt_register.py` 与 `codex/protocol_keygen.py` 中的自定义 HTTP 流程
  - 鉴权方式：Cookie、PKCE、sentinel challenge、OAuth client 参数
  - 关键端点：`/oauth/authorize`、`/oauth/token`、账户续接 / 注册 / OTP 相关接口

**临时邮箱提供者：**
- DuckMail：创建邮箱并拉取邮件
  - 客户端：`chatgpt_register.py` 中的 `curl-cffi` Session
  - 鉴权：`DUCKMAIL_BEARER`
  - 关键端点：`/accounts`、`/token`、`/messages`
- Mail.tm：创建邮箱并拉取邮件
  - 客户端：`chatgpt_register.py` 中的 `curl-cffi` Session
  - 鉴权：邮箱账号换取的 provider token
  - 关键端点：`/domains`、`/accounts`、`/token`、`/messages`
- Mailcow：自建邮箱生命周期管理
  - 集成方式：REST 创建 / 删除邮箱，IMAP 读取 OTP
  - 鉴权：`X-API-Key` 与邮箱密码
  - 关键端点：`/api/v1/add/mailbox`、`/api/v1/delete/mailbox`

**上传目标：**
- CPA 管理平台：可选上传 token JSON
  - 集成方式：`curl-cffi` 发送 multipart POST
  - 鉴权：`upload_api_token`
  - 触发点：生成单账号 token JSON 之后
- Sub2API：可选使用 OAuth token 创建账号
  - 集成方式：JSON REST API
  - 鉴权：`x-api-key` 或 Bearer Token
  - 关键端点：`/api/v1/admin/groups`、`/api/v1/admin/accounts`

## 数据存储

**数据库：**
- 无：仓库内没有内部数据库、ORM 或迁移系统

**文件存储：**
- 本地文件系统：所有输出都写在仓库根目录附近
  - 典型文件：`registered_accounts.txt`、`ak.txt`、`rk.txt`、`codex_tokens/*.json`
  - 权限模型：依赖本地操作系统文件权限

**缓存：**
- 无独立缓存层
- 运行期状态只保存在进程内存中

## 认证与身份

**认证提供方：**
- OpenAI auth：账户注册、邮箱 OTP、OAuth token 签发都依赖该服务
  - 实现方式：自定义 HTTP 请求序列与 session cookie 管理
  - Token 存储：纯文本文件与本地 JSON 文件
  - Session 管理：每个 worker 维护独立内存态 session

**OAuth 集成：**
- OpenAI OAuth Client：使用 `oauth_client_id` 与 `oauth_redirect_uri`
  - 配置位置：`config.json` / `config.example.json`
  - 用途：完成 Codex / ChatGPT token 获取流程

## 监控与可观测性

**错误追踪：**
- 无外部错误追踪平台接入

**分析：**
- 无埋点分析平台

**日志：**
- 仅 stdout / stderr
  - 主方式：`print()`
  - 可选增强：`rich` 实时面板

## CI / CD 与部署

**托管：**
- 无服务托管配置
- 这是本地脚本项目，不是部署型应用

**CI：**
- 未发现 GitHub Actions、其他 CI 配置或发布流水线

## 环境配置

**开发环境：**
- 所需 secret 取决于邮箱提供者与上传目标
- secret 来源：`config.json`、环境变量、CLI 参数
- Mock / Stub：当前没有

**预发布环境：**
- 未定义 staging 约定

**生产 / 实际执行：**
- `.gitignore` 已忽略 `config.json`、`codex/config.json`、`codex_tokens/` 等敏感输出
- 没有接入集中式 secret manager

## 回调与回传

**进入系统的回调：**
- OAuth 重定向回调：默认使用 `http://localhost:1455/auth/callback`
  - 校验方式：从回调 URL 中提取 `code` 参数
  - 用途：OAuth 授权完成后的 token 交换

**发往外部的调用：**
- CPA 上传：token JSON 写盘后触发
  - 重试：仅有请求级异常处理，没有统一重试策略
- Sub2API 账号创建：token 生成后触发
  - 重试：仅有请求级异常处理，没有统一重试策略

---

*外部集成审计：2026-03-07*
*新增或移除外部服务后更新*
