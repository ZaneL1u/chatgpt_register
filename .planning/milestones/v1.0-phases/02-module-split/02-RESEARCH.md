# Phase 2: 模块拆分 - 研究

**研究日期:** 2026-03-08
**领域:** Python 包结构重组 + 全局变量消除
**置信度:** HIGH

<user_constraints>
## 用户约束 (来自 CONTEXT.md)

### 锁定决策
- 按架构层拆分，使用同名 `chatgpt_register/` 包目录
- 子包划分：`config/`、`core/`、`adapters/`、`upload/`
- 顶层放置 `cli.py`（argparse + main）和 `dashboard.py`（RuntimeDashboard）
- 邮箱适配器各自独立文件：`adapters/base.py`、`adapters/duckmail.py`、`adapters/mailcow.py`、`adapters/mailtm.py`
- ChatGPTRegister 类、OAuth 登录流程、sentinel token 生成合并为 `core/register.py`
- 批处理编排独立为 `core/batch.py`（run_batch）
- 上传目标各自独立文件：`upload/cpa.py`、`upload/sub2api.py`
- pyproject.toml 入口切换到 `chatgpt_register.cli:main`
- 不保留旧文件兼容层，旧 `chatgpt_register.py`、根目录 `config_model.py`、`profile_manager.py` 全部删除
- 不需要 `__main__.py`
- `run_batch(config: RegisterConfig)` 接收配置对象，内部函数通过参数传递 config 或其子属性
- 彻底消除模块级可变全局状态
- 拆分与全局变量迁移一步完成

### Claude 自主裁量
- 测试目录组织方式
- Phase 1 产物整合到 config/ 子包的具体文件命名
- 各模块的 `__init__.py` 导出策略
- 辅助函数的具体归属模块
</user_constraints>

<phase_requirements>
## 阶段需求

| ID | 描述 | 研究支撑 |
|----|------|----------|
| ARCH-01 | 拆分 `chatgpt_register.py` 为多模块包结构 | 目标包结构设计、依赖关系分析、全局变量消除策略 |
</phase_requirements>

## 概要

本阶段核心任务是将 3217 行的 `chatgpt_register.py` 单文件拆分为清晰的 Python 包结构。同时需要将 Phase 1 产出的根目录 `config_model.py` 和 `profile_manager.py` 整合进包内。拆分过程中需要同步消除 30 个模块级全局变量（第 414-443 行），改为通过 `RegisterConfig` 参数传递。

**核心挑战:**
1. 全局变量被约 40 个函数/方法直接引用，需要逐一改为参数传递
2. `_register_one()` 和 `run_batch()` 是全局变量的主要消费者，需要重构签名
3. 上传函数（`_upload_token_json_to_cpa`、`_upload_token_to_sub2api` 等）大量依赖全局变量
4. `_build_email_adapter()` 工厂函数使用全局 `EMAIL_PROVIDER`
5. `_load_config()` 和 `_CONFIG` 在模块导入时执行，需要延迟到运行时

## 源文件分析

### 当前文件行号区段

| 行号范围 | 内容 | 目标模块 |
|----------|------|----------|
| 1-31 | imports | 各模块自行导入 |
| 32-49 | rich 导入 + 全局常量 | `dashboard.py` |
| 51-80 | 辅助打印函数 | `core/utils.py` |
| 82-262 | `RuntimeDashboard` 类 | `dashboard.py` |
| 264-288 | `_route_print_to_dashboard` | `dashboard.py` |
| 290-320 | `_as_int`, `_parse_int_list` | `core/utils.py` |
| 323-443 | `_load_config` + 30 个全局变量 | 删除（由 RegisterConfig 替代）|
| 446-597 | 上传目标解析、TUI 选择、配置校验 | `upload/common.py` + `cli.py` |
| 599-606 | `_random_chrome_version` | `core/http.py` |
| 609-628 | `_random_delay`, `_make_trace_headers`, `_generate_pkce` | `core/http.py` |
| 631-810 | `SentinelTokenGenerator` + sentinel 函数 | `core/sentinel.py` |
| 812-890 | JWT 解码、token 保存 | `core/tokens.py` |
| 892-1245 | 上传函数（CPA + Sub2API） | `upload/cpa.py` + `upload/sub2api.py` + `upload/common.py` |
| 1246-1260 | `_generate_password` | `core/utils.py` |
| 1261-1628 | 邮箱操作（旧式独立函数，已被适配器封装） | 删除或整合到适配器 |
| 1630-1864 | 邮箱适配器类 | `adapters/base.py` + 各适配器文件 |
| 1867-2826 | `ChatGPTRegister` 类 | `core/register.py` |
| 2830-3003 | `_register_one` + `run_batch` | `core/batch.py` |
| 3005-3217 | CLI（argparse + main） | `cli.py` |

### 全局变量依赖图

被引用最多的全局变量（grep 统计）：

| 变量 | 引用次数 | 主要消费者 |
|------|----------|-----------|
| `EMAIL_PROVIDER` | ~8 | `_build_email_adapter`, `_register_one`, `main`, 配置校验函数 |
| `DUCKMAIL_BEARER` / `DUCKMAIL_API_BASE` | ~4 | `DuckMailAdapter` |
| `MAILCOW_*` (6个) | ~12 | `MailcowAdapter`, mailcow 独立函数 |
| `MAILTM_API_BASE` | ~2 | `MailTmAdapter` |
| `ENABLE_OAUTH` / `OAUTH_*` | ~6 | `_register_one`, `ChatGPTRegister` |
| `SUB2API_*` (6个) | ~15 | 上传函数、`_prepare_sub2api_group_binding` |
| `UPLOAD_*` | ~5 | 上传函数 |
| `DEFAULT_PROXY` | ~3 | `_new_upload_session`, CLI |
| `AK_FILE` / `RK_FILE` / `TOKEN_JSON_DIR` | ~3 | `_save_codex_tokens` |
| `UPLOAD_TARGET_SET` | ~4 | `_upload_token_data`, CLI |
| `_print_lock` / `_file_lock` | ~20 | 全局使用 |

### 线程同步原语

```python
_print_lock = threading.Lock()  # 保护 print 输出
_file_lock = threading.Lock()   # 保护文件写入
```

这两个锁在并发场景下被多个函数使用，需要保留为模块级常量但放在合适的位置。建议：
- `_print_lock` → `core/batch.py`（批处理编排模块）
- `_file_lock` → `core/batch.py`（批处理编排模块）

## 目标包结构

```
chatgpt_register/           # Python 包（替代原单文件）
├── __init__.py              # 版本号 + 公共导出
├── cli.py                   # argparse CLI 入口 + main()
├── dashboard.py             # RuntimeDashboard + print 路由
├── config/
│   ├── __init__.py          # re-export RegisterConfig, ProfileManager
│   ├── model.py             # 原 config_model.py 内容
│   └── profile.py           # 原 profile_manager.py 内容
├── core/
│   ├── __init__.py
│   ├── register.py          # ChatGPTRegister 类
│   ├── batch.py             # run_batch() + _register_one()
│   ├── sentinel.py          # SentinelTokenGenerator + sentinel 函数
│   ├── tokens.py            # JWT 解码 + token 保存
│   ├── http.py              # Chrome 版本模拟 + HTTP 辅助
│   └── utils.py             # 密码生成、随机姓名/生日、打印辅助
├── adapters/
│   ├── __init__.py          # re-export _build_email_adapter
│   ├── base.py              # EmailAdapter 抽象基类
│   ├── duckmail.py          # DuckMailAdapter
│   ├── mailcow.py           # MailcowAdapter + IMAP 操作
│   └── mailtm.py            # MailTmAdapter
└── upload/
    ├── __init__.py          # re-export upload_token_data
    ├── common.py            # 上传目标解析 + 共享会话创建
    ├── cpa.py               # CPA 上传
    └── sub2api.py           # Sub2API 上传 + 分组管理
```

## 全局变量消除策略

### 策略：参数注入 + RegisterConfig 透传

1. **`run_batch(config: RegisterConfig)`** — 顶层入口接收完整配置
2. **`_register_one(idx, total, config: RegisterConfig)`** — worker 接收配置
3. **`ChatGPTRegister.__init__(config: RegisterConfig, ...)`** — 注册器从配置中提取所需字段
4. **适配器工厂** — `_build_email_adapter(register, config: RegisterConfig)` 从 config.email 读取 provider
5. **适配器实例** — 构造时接收对应的子配置（如 `DuckMailAdapter(register, config.email.duckmail)`）
6. **上传函数** — 接收 `config.upload` 子配置
7. **token 保存** — 接收 `config.registration` 子配置（获取 ak_file、rk_file、token_json_dir）

### 旧式独立函数处理

第 1261-1628 行有大量旧式独立邮箱函数（`create_temp_email()`、`_fetch_emails_duckmail()` 等）。这些函数已被适配器类封装但仍保留在源文件中。拆分时：
- 适配器类已完整封装了这些功能
- 旧式独立函数中有部分被适配器内部调用（如 `_mailcow_create_mailbox`）
- 需要将被调用的旧函数整合到对应适配器模块中
- 未被调用的冗余函数直接丢弃

### `_load_config()` 处理

`_load_config()` 从 `config.json` 加载旧格式配置。在 Phase 2 中：
- 此函数由 CLI 层的新代码替代
- CLI 通过 `RegisterConfig` 构造配置（来自 TOML profile 或 CLI 参数）
- 旧的 config.json 加载逻辑不再需要，直接删除

## 测试策略

### 现有测试
- `tests/test_config_model.py` — 13 个测试覆盖 RegisterConfig 校验
- `tests/test_profile_manager.py` — 11 个测试覆盖 ProfileManager CRUD

### 拆分后测试迁移
- 现有测试 import 路径需要更新：`from config_model import ...` → `from chatgpt_register.config.model import ...`
- conftest.py 的 fixtures 保持不变（数据结构未变）
- 新增集成测试：验证 `run_batch(config)` 接受 RegisterConfig 参数

### 测试执行命令
```bash
python -m pytest tests/ -x -q
```

## 风险与缓解

### 风险 1: 循环导入
**场景:** `core/register.py` 导入 `adapters/`，`adapters/` 导入 `core/register.py`（因 EmailAdapter 持有 register 引用）
**缓解:** 适配器通过 `TYPE_CHECKING` 导入 register 类型，运行时只持有实例引用

### 风险 2: pyproject.toml 入口点变更
**场景:** `scripts = { chatgpt-register = "chatgpt_register:main" }` 指向旧单文件
**缓解:** 更新为 `chatgpt_register.cli:main`，同时更新 `[tool.setuptools]` 配置

### 风险 3: 相对路径依赖
**场景:** `_save_codex_tokens` 使用 `os.path.dirname(os.path.abspath(__file__))` 定位输出目录
**缓解:** 改为使用当前工作目录（`Path.cwd()`），与用户期望一致

### 风险 4: 线程安全
**场景:** 全局锁 `_print_lock` 和 `_file_lock` 需要在多个模块间共享
**缓解:** 将锁定义在 `core/batch.py` 中并导出，或作为运行上下文的一部分传递

## 陷阱

### 陷阱 1: `config.json` 导入时执行
**问题:** 原文件第 414 行 `_CONFIG = _load_config()` 在模块导入时立即执行，会尝试读取 config.json
**解决:** 拆分后不再有模块级执行，配置由 CLI 显式构造

### 陷阱 2: `builtins.print` 猴子补丁
**问题:** `_route_print_to_dashboard` 修改全局 `builtins.print`，如果 dashboard 和业务逻辑在不同模块，效果仍然全局
**解决:** 这正是期望行为——contextmanager 在 `run_batch` 内使用，只在批处理期间生效

### 陷阱 3: `questionary` 延迟导入
**问题:** `_tui_select` 函数内部延迟导入 `questionary`，拆分后需要保持此模式
**解决:** 保持在 `cli.py` 中的延迟导入方式

## 验证架构

### 测试框架

| 属性 | 值 |
|------|-----|
| 框架 | pytest |
| 快速运行命令 | `python -m pytest tests/ -x -q` |
| 完整套件命令 | `python -m pytest tests/ -v` |

### 阶段需求 -> 测试映射

| Req ID | 行为 | 测试类型 | 自动化命令 |
|--------|------|----------|-----------|
| ARCH-01 | 包结构可导入，无循环依赖 | integration | `python -c "from chatgpt_register.core.batch import run_batch"` |
| ARCH-01 | run_batch 接受 RegisterConfig | unit | `python -m pytest tests/test_batch.py -x` |
| ARCH-01 | 旧文件已删除 | shell | `test ! -f chatgpt_register.py` |
| ARCH-01 | 现有测试全部通过 | regression | `python -m pytest tests/ -x -q` |

### 采样频率
- **每次任务提交:** `python -m pytest tests/ -x -q`
- **阶段门控:** 完整套件全绿 + 导入链验证

## 来源

### 主要来源 (HIGH 置信度)
- 项目源码 `chatgpt_register.py`（3217 行，直接分析）
- Phase 1 产物 `config_model.py` + `profile_manager.py`
- 用户讨论决策 `02-CONTEXT.md`

### 次要来源 (MEDIUM 置信度)
- Python Packaging User Guide — src layout vs flat layout
- setuptools 文档 — packages 自动发现配置

## 元数据

**置信度分项:**
- 包结构: HIGH — 基于用户锁定决策 + 源码实际分析
- 全局变量消除: HIGH — 完整梳理了所有变量引用链
- 测试策略: HIGH — 基于现有测试基础
- 风险: MEDIUM — 循环导入和线程安全需要实际验证

**研究日期:** 2026-03-08
**有效期至:** 2026-04-08
