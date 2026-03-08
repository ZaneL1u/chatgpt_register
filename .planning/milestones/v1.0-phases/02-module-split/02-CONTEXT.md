# Phase 2: 模块拆分 - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## 阶段边界

将 3217 行的 `chatgpt_register.py` 单文件拆分为清晰的多模块 Python 包结构。`run_batch()` 通过 `RegisterConfig` 实例作为参数驱动，而非全局变量。Phase 1 产出的 `config_model.py` 和 `profile_manager.py` 一并整合进新包。TUI 向导（Phase 3）和 CLI 集成（Phase 4）不在本阶段范围内。

</domain>

<decisions>
## 实现决策

### 包结构设计
- 按架构层拆分，使用同名 `chatgpt_register/` 包目录（原单文件变为包）
- 子包划分：`config/`、`core/`、`adapters/`、`upload/`
- 顶层放置 `cli.py`（argparse + main）和 `dashboard.py`（RuntimeDashboard）

### 拆分粒度
- 邮箱适配器各自独立文件：`adapters/base.py`（抽象基类）、`adapters/duckmail.py`、`adapters/mailcow.py`、`adapters/mailtm.py`
- ChatGPTRegister 类、OAuth 登录流程、sentinel token 生成合并为 `core/register.py`（逻辑耦合紧密）
- 批处理编排独立为 `core/batch.py`（run_batch）
- 上传目标各自独立文件：`upload/cpa.py`、`upload/sub2api.py`

### 入口点与兼容性
- pyproject.toml 的 console_scripts 直接切换到 `chatgpt_register.cli:main`
- 不保留旧文件兼容层，旧的 `chatgpt_register.py`、根目录 `config_model.py`、`profile_manager.py` 全部删除
- 不需要 `__main__.py`，不支持 `python -m chatgpt_register` 运行方式

### 全局变量迁移策略
- 采用参数传递方式：`run_batch(config: RegisterConfig)` 接收配置对象，内部函数通过参数传递 config 或其子属性
- 彻底消除模块级可变全局状态
- 拆分与全局变量迁移一步完成，不分阶段

### Claude's Discretion
- 测试目录组织方式（镜像结构或扁平）
- Phase 1 产物整合到 config/ 子包的具体文件命名（如 model.py vs config_model.py）
- 各模块的 `__init__.py` 导出策略
- 辅助函数（如代理解析、配置校验）的具体归属模块

</decisions>

<specifics>
## 具体想法

无特定要求——按照讨论的架构层拆分方案执行即可。

</specifics>

<code_context>
## 现有代码洞察

### 可复用资产
- `config_model.py`：RegisterConfig Pydantic 模型，已完成所有配置字段定义和校验
- `profile_manager.py`：ProfileManager TOML 持久化，支持创建/读取/保存/列举/删除
- `tests/test_config_model.py` + `tests/test_profile_manager.py`：Phase 1 已有测试覆盖

### 已建立的模式
- 邮箱适配器：`EmailAdapter` 抽象基类 + `DuckMailAdapter`/`MailcowAdapter`/`MailTmAdapter` 实现（策略模式）
- 核心注册：`ChatGPTRegister` 有状态服务对象，绑定单个 worker 生命周期
- 并发模型：线程池 + 共享锁，worker 返回结果元组 `(ok, email, err)`
- 错误处理：集成边界抛异常，worker 边界捕获并输出
- 日志：`print()` 为主，`rich` 实时面板可选增强

### 集成点
- `pyproject.toml`：console_scripts 入口需要更新
- `config.example.json`：示例配置文件保留不动
- `codex/protocol_keygen.py`：独立工具，不参与拆分
- `chatgpt_register.egg-info/`：需要重新生成

</code_context>

<deferred>
## 延迟想法

无——讨论保持在阶段范围内。

</deferred>

---

*Phase: 02-module-split*
*Context gathered: 2026-03-08*
