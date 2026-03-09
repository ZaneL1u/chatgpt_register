---
type: quick-task
plan: 1
subsystem: email-adapters
tags: [catchmail, maildrop, email-adapter, wizard]
key-files:
  created:
    - chatgpt_register/adapters/catchmail.py
    - chatgpt_register/adapters/maildrop.py
  modified:
    - chatgpt_register/config/model.py
    - chatgpt_register/adapters/__init__.py
    - chatgpt_register/wizard.py
    - chatgpt_register/core/utils.py
decisions:
  - Catchmail.io 和 Maildrop.cc 均无需注册/API Key，mail_token 采用 "provider:email" 格式传递邮箱地址
  - Maildrop 使用 GraphQL API，Catchmail 使用 REST API
  - 向导 provider_key 映射改为显式映射表，避免 lower().replace() 对含点号名称的错误转换
metrics:
  duration: 174s
  completed: "2026-03-10T03:12:56+08:00"
---

# Quick Task 1: 添加 Catchmail.io 和 Maildrop.cc 邮箱服务支持

**概要:** 新增两个免费临时邮箱适配器（Catchmail.io REST API + Maildrop.cc GraphQL API），含配置模型、工厂函数、向导集成和域名多选

## 完成任务

| 任务 | 名称               | 提交    | 关键文件                                      |
| ---- | ------------------ | ------- | --------------------------------------------- |
| 1    | 新增配置模型和适配器 | 9fb19ed | config/model.py, adapters/catchmail.py, adapters/maildrop.py, adapters/__init__.py |
| 2    | 更新向导和工具函数   | 1a37e6a | wizard.py, core/utils.py                      |
| 3    | 验证整体集成         | (无变更) | 端到端验证通过                                 |

## 实现细节

### CatchmailAdapter（REST API）
- `create_temp_email()`: 从可配置域名列表随机选域名 + 随机用户名，无需注册
- `fetch_messages()`: GET `/api/v1/mailbox?address={email}` 解析 messages 数组
- `extract_message_content()`: GET `/api/v1/message/{id}?mailbox={email}` 取 body.text/body.html
- 支持 6 个域名：catchmail.io / .cc / .com / .net / .org / .co

### MaildropAdapter（GraphQL API）
- `create_temp_email()`: 随机用户名 + 固定 @maildrop.cc，无需注册
- `fetch_messages()`: GraphQL `inbox(mailbox:)` 查询
- `extract_message_content()`: GraphQL `message(mailbox:, id:)` 查询，返回 html 或 data 字段

### 配置模型
- `CatchmailConfig`: api_base + domains（默认 6 个全选）
- `MaildropConfig`: api_base（默认 GraphQL 端点）
- `EmailConfig.provider` Literal 扩展为 5 项

### 向导更新
- 选项列表新增 Catchmail.io 和 Maildrop.cc
- Catchmail.io 分支：API Base + checkbox 域名多选
- Maildrop.cc 分支：仅 API Base
- provider_key 使用显式映射表替代字符串操作

## 偏离计划

无 — 完全按计划执行。

## 验证结果

- CatchmailConfig / MaildropConfig 可正常导入和实例化
- RegisterConfig 对两个新 provider 的校验通过（含默认值、自定义值、缺失配置报错）
- 工厂函数 build_email_adapter 可识别新 provider
- provider_display_name 正确返回显示名称
