# Quick Task 1: 添加 Catchmail.io 和 Maildrop.cc 邮箱服务支持

## 任务描述

在现有邮箱适配器架构上新增 Catchmail.io 和 Maildrop.cc 两个免费临时邮箱服务。向导中可选这两个新服务；Catchmail.io 额外支持勾选可用域名（默认全选，可去掉部分）。

## 任务分解

### Task 1: 新增配置模型和适配器

**files**: `config/model.py`, `adapters/catchmail.py`(新建), `adapters/maildrop.py`(新建), `adapters/__init__.py`
**action**:

1. `config/model.py`:
   - 新增 `CatchmailConfig(BaseModel)`: `api_base="https://api.catchmail.io"`, `domains: list[str]`（默认 6 个域名全选）
   - 新增 `MaildropConfig(BaseModel)`: `api_base="https://api.maildrop.cc/graphql"`
   - `EmailConfig.provider` Literal 加入 `"catchmail"`, `"maildrop"`
   - `EmailConfig` 加字段 `catchmail`, `maildrop`，更新 `check_provider_config` mapping

2. `adapters/catchmail.py`（新建）:
   - `CatchmailAdapter(EmailAdapter)`, provider = `"catchmail"`
   - `create_temp_email()`: 从 config.domains 随机选域名，生成随机用户名，拼接地址。Catchmail 无需注册，直接返回 `(email, "", f"catchmail:{email}")`
   - `fetch_messages()`: GET `/api/v1/mailbox?address={email}` 解析 messages 数组
   - `extract_message_content()`: GET `/api/v1/message/{id}?mailbox={email}` 取 body.text 或 body.html

3. `adapters/maildrop.py`（新建）:
   - `MaildropAdapter(EmailAdapter)`, provider = `"maildrop"`
   - `create_temp_email()`: 生成随机用户名，拼 `@maildrop.cc`。返回 `(email, "", f"maildrop:{email}")`
   - `fetch_messages()`: POST GraphQL `{ inbox(mailbox: "xxx") { id headerfrom subject date } }`
   - `extract_message_content()`: POST GraphQL `{ message(mailbox: "xxx", id: "yyy") { ... data html } }`

4. `adapters/__init__.py`:
   - `build_email_adapter()` 加 `catchmail` 和 `maildrop` 分支

**verify**: `python -c "from chatgpt_register.config.model import CatchmailConfig, MaildropConfig; print('ok')"`
**done**: 两个新适配器可导入，工厂函数可创建

### Task 2: 更新向导和工具函数

**files**: `wizard.py`, `core/utils.py`
**action**:

1. `core/utils.py` — `provider_display_name()` mapping 加:
   - `"catchmail": "Catchmail.io"`
   - `"maildrop": "Maildrop.cc"`

2. `wizard.py` — `_ask_email_config()`:
   - choices 加 `"Catchmail.io"`, `"Maildrop.cc"`
   - provider_key 映射: `"catchmail.io"` → `"catchmail"`, `"maildrop.cc"` → `"maildrop"`（需修改映射逻辑）
   - Catchmail.io 分支: 询问 API Base（默认），然后用 `questionary.checkbox` 让用户勾选域名（默认全选 6 个），可去掉部分
   - Maildrop.cc 分支: 仅询问 API Base（默认值即可）

**verify**: `python -c "from chatgpt_register.wizard import _ask_email_config; print('ok')"`
**done**: 向导支持选择 5 个邮箱平台，Catchmail.io 有域名勾选

### Task 3: 验证整体集成

**files**: 无新文件
**action**: 运行 `python -c` 验证完整链路可导入、配置模型校验通过
**verify**: 构建 RegisterConfig 对象，provider=catchmail 和 maildrop 均能通过校验
**done**: 端到端可用
