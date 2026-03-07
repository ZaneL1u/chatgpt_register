# 架构

**分析日期：** 2026-03-07

## 模式概览

**整体模式：** 单体 Python CLI 自动化工具，采用邮箱提供者适配器 + 线程池并发模型

**关键特征：**
- 主入口集中在单文件 `chatgpt_register.py`
- 核心流程是高网络耦合的直接 HTTP 编排
- 临时邮箱后端通过适配器模式接入
- 没有数据库，输出完全基于文件
- 存在一个与主流程概念重叠的独立工具 `codex/protocol_keygen.py`
- GSD / Codex 工作流约束通过 `AGENTS.md`、`CLAUDE.md`、`.planning/config.json`、`.codex/config.toml` 叠加生效

## 分层

**CLI / 交互层：**
- 目的：解析参数、执行交互选择、展示进度与结果
- 包含：`main()`、`_build_cli_parser()`、`_resolve_proxy_from_inputs()`、`_prompt_upload_targets()`、`RuntimeDashboard`
- 依赖：全局配置与批处理执行层
- 被谁使用：终端用户通过 `chatgpt-register` 调用

**配置层：**
- 目的：合并 `config.json`、环境变量、CLI 参数，生成运行时配置
- 包含：`_load_config()`、`_apply_cli_overrides()`、邮箱 / 上传配置校验函数
- 依赖：本地文件系统与环境变量
- 被谁使用：所有后续注册、OAuth、上传逻辑

**执行层：**
- 目的：协调并发注册任务并汇总结果
- 包含：`run_batch()`、`_register_one()`，以及 `codex/protocol_keygen.py` 中对应的批处理入口
- 依赖：worker 函数、锁、文件输出、远程 HTTP 服务
- 被谁使用：CLI 入口

**集成层：**
- 目的：对接邮箱提供者、OpenAI 接口、上传目标
- 包含：`EmailAdapter` 及其实现、`ChatGPTRegister`、sentinel token 生成逻辑、上传辅助函数
- 依赖：`curl-cffi`、`imaplib`、`requests`、远程服务
- 被谁使用：执行层

## 数据流

**主注册流程：**
1. 用户通过 `chatgpt-register` 或 `python chatgpt_register.py` 启动程序
2. `main()` 解析 CLI 参数，并与 `config.json` / 环境变量合并
3. `run_batch()` 按账号数创建线程池，调度 `_register_one()`
4. `_register_one()` 创建 `ChatGPTRegister` 实例，并通过 `_build_email_adapter()` 选择邮箱适配器
5. 适配器创建邮箱并在后续轮询 OTP 邮件
6. `ChatGPTRegister` 依次执行首页、CSRF、注册、发送 OTP、校验 OTP、创建账号等 HTTP 步骤
7. 可选执行 OAuth 登录，解码 token，写入本地文件，并按配置上传到 CPA / Sub2API
8. 批处理层统计成功 / 失败并输出到普通日志或实时面板

**状态管理：**
- 跨次运行基本无状态
- 运行期状态保存在进程内存、线程局部 session 与少量全局配置变量中
- 持久化状态只体现在输出文件与 `.planning/` 文档

## 关键抽象

**EmailAdapter：**
- 目的：统一不同临时邮箱服务的创建、拉信与内容提取行为
- 例子：`DuckMailAdapter`、`MailcowAdapter`、`MailTmAdapter`
- 模式：策略 / 适配器模式

**ChatGPTRegister：**
- 目的：封装主流程中的 OpenAI 注册与 OAuth 行为
- 例子：session 初始化、sentinel token 构造、重定向跟踪、OTP 提交
- 模式：绑定单个 worker 生命周期的有状态服务对象

**RuntimeDashboard：**
- 目的：以 `rich` 构建并发执行面板
- 例子：摘要区域、worker 状态表、日志窗口
- 模式：带锁的内存态 UI 聚合器

## 入口点

**主 CLI 入口：**
- 位置：`chatgpt_register.py`
- 触发方式：`chatgpt-register` console script 或直接运行 Python 文件
- 职责：校验配置、处理交互、启动并发注册

**协议工具入口：**
- 位置：`codex/protocol_keygen.py`
- 触发方式：直接执行脚本
- 职责：运行另一套纯 HTTP 注册 / OAuth 流程，并保存生成结果

## 错误处理

**总体策略：** 在集成边界抛异常，在 worker 或 CLI 边界集中捕获并输出可读错误

**常见模式：**
- 启动前通过辅助函数校验邮箱与上传配置
- worker 尽量返回 `(ok, email, err)` 一类结果元组，避免线程异常直接冒泡
- 外部调用周围大量使用宽泛的 `except Exception`，以便在脚本场景下继续运行或输出错误

## 横切关注点

**日志：**
- 以终端输出为主，没有独立 logger 抽象
- 重点记录步骤推进、状态码、上传结果、OAuth 流程状态

**验证：**
- 配置与响应主要依赖手写校验，没有 schema 系统
- 项目级语言约束依赖仓库文件约定，而不是程序内硬编码

**认证与 secret：**
- secret 来自本地配置、环境变量或 CLI 参数
- token 和账号元数据会被写回磁盘
- 没有加密存储、脱敏日志或 secret manager 抽象

---

*架构分析：2026-03-07*
*主要模式变化后更新*
