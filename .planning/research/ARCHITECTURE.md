# 架构研究：TUI 配置系统集成

**领域:** Python CLI 工具的 TUI 配置向导集成
**研究日期:** 2026-03-07
**置信度:** HIGH

## 系统总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        入口层 (Entry)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  CLI 解析器  │  │  TUI 向导    │  │  Profile 快速选择    │   │
│  │  (argparse)  │  │  (Textual)   │  │  (Textual)           │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                     │               │
├─────────┴─────────────────┴─────────────────────┴───────────────┤
│                      配置层 (Config)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              ProfileManager (TOML 读写)                  │    │
│  │     load / save / list / delete / validate               │    │
│  └────────────────────────┬────────────────────────────────┘    │
│                           │                                     │
├───────────────────────────┴─────────────────────────────────────┤
│                      执行层 (Execution)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐     │
│  │ run_batch() │  │ Dashboard   │  │  上传 (CPA/Sub2API) │     │
│  │ ThreadPool  │  │ (Rich Live) │  │                     │     │
│  └──────┬──────┘  └─────────────┘  └─────────────────────┘     │
│         │                                                       │
├─────────┴───────────────────────────────────────────────────────┤
│                      集成层 (Integration)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ DuckMail │  │ Mailcow  │  │ Mail.tm  │  │ ChatGPTReg   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      存储层 (Storage)                            │
│  ┌──────────────────────┐  ┌──────────────┐                     │
│  │ ~/.chatgpt-register/ │  │ 输出文件     │                     │
│  │   profiles/*.toml    │  │ ak.txt 等    │                     │
│  └──────────────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

### 组件职责

| 组件 | 职责 | 与谁通信 |
|------|------|----------|
| CLI 解析器 | 解析命令行参数，支持 `--profile` / `--non-interactive` 等快捷入口 | ProfileManager、执行层 |
| TUI 向导 (Textual App) | 交互式引导用户完成全部配置选项，生成配置字典 | ProfileManager |
| Profile 快速选择 (Textual Screen) | 列出已有 profile，选择后直接进入执行 | ProfileManager、执行层 |
| ProfileManager | TOML profile 的 CRUD、校验、路径管理 | 文件系统 (存储层) |
| run_batch() | 并发调度注册任务 | 集成层、Dashboard |
| RuntimeDashboard | 实时展示注册进度 (Rich Live) | run_batch() |
| EmailAdapter 家族 | 创建临时邮箱、拉取 OTP | 外部邮箱服务 |
| ChatGPTRegister | 执行 OpenAI 注册 HTTP 流程 | OpenAI API |

## 推荐项目结构

```
chatgpt_register/
├── chatgpt_register/          # 包化目录（从单文件迁移）
│   ├── __init__.py            # 版本号、公共导出
│   ├── __main__.py            # python -m chatgpt_register 入口
│   ├── cli.py                 # argparse 定义 + main()
│   ├── config/
│   │   ├── __init__.py
│   │   ├── profile.py         # ProfileManager: TOML 读写、校验
│   │   ├── schema.py          # 配置字段定义与默认值（dataclass）
│   │   └── migration.py       # config.json → TOML 迁移工具
│   ├── tui/
│   │   ├── __init__.py
│   │   ├── app.py             # Textual App 主类
│   │   ├── screens/
│   │   │   ├── welcome.py     # 欢迎 / profile 选择界面
│   │   │   ├── wizard.py      # 配置向导主界面
│   │   │   └── confirm.py     # 配置确认摘要界面
│   │   ├── widgets/
│   │   │   ├── provider.py    # 邮箱提供者选择组件
│   │   │   ├── upload.py      # 上传目标选择组件
│   │   │   └── execution.py   # 并发数/账号数设置组件
│   │   └── styles/
│   │       └── app.tcss       # Textual CSS 样式表
│   ├── core/
│   │   ├── __init__.py
│   │   ├── register.py        # ChatGPTRegister 类
│   │   ├── batch.py           # run_batch()、_register_one()
│   │   └── dashboard.py       # RuntimeDashboard
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py            # EmailAdapter 基类
│   │   ├── duckmail.py        # DuckMailAdapter
│   │   ├── mailcow.py         # MailcowAdapter
│   │   └── mailtm.py          # MailTmAdapter
│   └── upload/
│       ├── __init__.py
│       ├── cpa.py             # CPA 上传逻辑
│       └── sub2api.py         # Sub2API 上传逻辑
├── pyproject.toml
└── uv.lock
```

### 结构设计理由

- **`config/`:** 配置逻辑独立成模块，ProfileManager 是核心——TUI、CLI 都通过它读写配置，避免配置散落在全局变量中
- **`tui/`:** Textual 相关代码完全隔离。使用 Textual 的 Screen 机制组织多步向导，widgets 可复用、可独立测试
- **`core/`:** 注册执行逻辑与 UI 完全解耦。`run_batch()` 接收一个配置字典即可运行，不关心配置来源
- **`adapters/`:** 邮箱适配器保持已有的策略模式，每个适配器一个文件，便于新增
- **`upload/`:** 上传目标独立，CPA 和 Sub2API 各自封装

## 架构模式

### 模式 1: TUI-as-Config-Generator（TUI 仅生成配置）

**是什么:** TUI 不直接执行注册，只负责收集用户输入并生成一个配置字典/Profile。配置生成后，TUI 退出，CLI 拿到配置后启动同步执行流程。

**何时使用:** 当已有执行逻辑是同步+线程池模型，与 Textual 的 asyncio 事件循环存在根本冲突时。这正是本项目的情况。

**权衡:**
- 优势: 不需要重写 `run_batch()` 和所有 worker 逻辑；TUI 与执行完全解耦；测试简单
- 代价: 执行期间无法用 TUI 展示进度（但已有 Rich RuntimeDashboard 可继续使用）

**示例:**

```python
# cli.py
def main():
    args = parse_args()

    if args.profile:
        # 快捷路径：直接加载已有 profile
        config = ProfileManager().load(args.profile)
    elif args.non_interactive:
        # 纯 CLI 模式：从参数 + 环境变量构建
        config = build_config_from_args(args)
    else:
        # 交互模式：启动 TUI 向导
        app = ConfigWizardApp()
        app.run()
        config = app.result_config  # TUI 退出后拿到配置
        if config is None:
            return 1  # 用户取消

    # 校验后执行
    validate_config(config)
    run_batch(**config)
```

### 模式 2: Textual Screen 多步向导

**是什么:** 用 Textual 的 `Screen` 类组织多步配置流程。每个配置步骤是一个独立 Screen，通过 `push_screen` / `pop_screen` 导航。最终 Screen 返回完整配置。

**何时使用:** 配置项较多，需要分步引导，且需要支持"上一步"回退。

**权衡:**
- 优势: 用户体验好，步骤清晰，代码模块化
- 代价: 需要管理 Screen 间的状态传递

**示例:**

```python
from textual.app import App
from textual.screen import Screen

class WizardStep1(Screen):
    """选择邮箱提供者"""
    def compose(self):
        yield Select(
            options=[("DuckMail", "duckmail"), ("Mailcow", "mailcow"), ("Mail.tm", "mailtm")],
            id="provider"
        )
        yield Button("下一步", id="next")

    def on_button_pressed(self, event):
        provider = self.query_one("#provider").value
        self.app.wizard_state["email_provider"] = provider
        self.app.push_screen(WizardStep2())

class ConfigWizardApp(App):
    def __init__(self):
        super().__init__()
        self.wizard_state = {}
        self.result_config = None

    def on_mount(self):
        self.push_screen(WizardStep1())
```

### 模式 3: ProfileManager 数据类 + TOML 序列化

**是什么:** 用 `dataclass` 定义配置 schema，ProfileManager 负责 TOML 序列化/反序列化、路径管理、列表展示。

**何时使用:** 需要类型安全的配置结构和多 profile 管理。

**权衡:**
- 优势: 类型提示、IDE 补全、默认值集中管理、校验逻辑内聚
- 代价: 需要维护 dataclass 与 TOML 的映射

**示例:**

```python
import tomllib
from dataclasses import dataclass, asdict, field
from pathlib import Path

@dataclass
class RegisterConfig:
    email_provider: str = "mailtm"
    total_accounts: int = 3
    max_workers: int = 3
    proxy: str = ""
    enable_oauth: bool = True
    # ... 其他字段

class ProfileManager:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path.home() / ".chatgpt-register" / "profiles"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> list[str]:
        return [p.stem for p in self.base_dir.glob("*.toml")]

    def load(self, name: str) -> RegisterConfig:
        path = self.base_dir / f"{name}.toml"
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return RegisterConfig(**data)

    def save(self, name: str, config: RegisterConfig) -> Path:
        import tomli_w  # 写入需要第三方库
        path = self.base_dir / f"{name}.toml"
        with open(path, "wb") as f:
            tomli_w.dump(asdict(config), f)
        return path
```

## 数据流

### 主数据流：TUI 向导模式

```
用户启动 chatgpt-register (无 --profile 参数)
    │
    ▼
┌───────────────────────────┐
│  检查已有 profiles        │
│  ProfileManager.list()    │
└───────────┬───────────────┘
            │
    ┌───────┴───────┐
    │ 有 profiles?  │
    └───┬───────┬───┘
     是 │       │ 否
        ▼       ▼
┌────────────┐  ┌────────────────┐
│ 欢迎界面   │  │ 直接进入       │
│ 选择已有 / │  │ 配置向导       │
│ 新建       │  │                │
└─────┬──────┘  └───────┬────────┘
      │                 │
      ▼                 ▼
┌──────────────────────────────────┐
│       Textual 配置向导           │
│  Step1: 邮箱提供者 + 凭证       │
│  Step2: 上传目标 + API 配置     │
│  Step3: 执行参数 (数量/并发)    │
│  Step4: 确认摘要                 │
└───────────────┬──────────────────┘
                │
                ▼
┌──────────────────────────────────┐
│  保存为 TOML Profile?            │
│  ProfileManager.save()           │
└───────────────┬──────────────────┘
                │
                ▼  (Textual App 退出)
┌──────────────────────────────────┐
│  config dict 传递给 run_batch()  │
│  同步执行，RuntimeDashboard 展示 │
└──────────────────────────────────┘
```

### 主数据流：CLI 快捷模式

```
用户启动 chatgpt-register --profile production
    │
    ▼
ProfileManager.load("production")
    │
    ▼
校验配置 → run_batch(**config)
```

### 关键数据流说明

1. **TUI → 配置字典:** Textual App 在运行过程中将用户选择存入 `wizard_state` 字典。App 退出后（`run()` 返回），调用方从 `app.result_config` 取出字典。这是 TUI 与执行层的唯一接口。
2. **配置字典 → 全局变量:** 当前代码使用模块级全局变量（`EMAIL_PROVIDER`、`DUCKMAIL_BEARER` 等约 30 个）。重构时应将这些全局变量封装为 `RegisterConfig` dataclass 实例，作为参数传入 `run_batch()`。
3. **run_batch → _register_one:** 通过 `ThreadPoolExecutor.submit()` 调度，每个 worker 接收配置参数和索引号。

## 反模式

### 反模式 1: 在 Textual 事件循环里跑同步注册逻辑

**常见做法:** 在 Textual App 中用 `@work(thread=True)` 包装 `run_batch()`，试图在 TUI 里同时展示配置和执行进度。

**为什么有问题:** `run_batch()` 内部已使用 `ThreadPoolExecutor`，在 Textual worker 线程中再创建线程池会导致嵌套线程管理混乱。更重要的是，`run_batch()` 大量使用全局 `print()` 和 `RuntimeDashboard`（基于 Rich Live），与 Textual 接管终端的模式直接冲突——两个框架会争夺终端控制权。

**正确做法:** TUI 只负责配置收集，生成配置后退出 Textual App，然后在普通终端环境下运行 `run_batch()`。已有的 `RuntimeDashboard`（Rich Live）在非 Textual 环境下正常工作。

### 反模式 2: Profile 字段散落在多处定义

**常见做法:** 在 TOML schema、CLI argparse、TUI widget、验证函数中各自硬编码字段名和默认值。

**为什么有问题:** 新增或修改配置字段需要同步改 4+ 处代码，极易遗漏导致行为不一致。

**正确做法:** 用一个 `RegisterConfig` dataclass 作为 Single Source of Truth。CLI 解析器、TUI 向导、ProfileManager 都从这个 dataclass 获取字段定义和默认值。

### 反模式 3: TUI 与业务逻辑紧耦合

**常见做法:** 在 Textual Screen 的事件处理器中直接调用邮箱验证、API 测试等网络操作。

**为什么有问题:** TUI 变得难以测试，网络错误会破坏交互体验，且违反单一职责。

**正确做法:** TUI 只收集用户输入。如果需要在 TUI 中做连通性检查（如验证 API key 是否有效），用 Textual 的 `@work(thread=True)` 在后台线程执行，通过 `call_from_thread` 更新 UI 状态。但这属于增强功能，初始版本不需要。

## Textual 与同步 CLI 集成的关键技术细节

### Textual App 生命周期

Textual `App.run()` 会：
1. 接管终端（进入 application mode）
2. 启动 asyncio 事件循环
3. 用户交互期间完全控制终端输出
4. `App.exit()` 后恢复终端并返回

**关键点:** `App.run()` 是阻塞调用。它返回后，终端恢复正常，可以继续使用 Rich Live 或普通 print。这意味着"先 TUI 后执行"的模式天然可行。

### Textual `App.run()` 的返回值

`App.exit(result)` 可以传递返回值，`App.run()` 的返回值就是 `exit()` 传入的值。这是 TUI 向外传递配置字典的最简洁方式：

```python
# TUI 内部
self.exit(result=self.wizard_state)

# 调用方
config = ConfigWizardApp().run()
if config is not None:
    run_batch(**config)
```

置信度: HIGH（来自 Textual 官方文档 `App.exit()` API）

### TOML 读写库选择

- **读取:** Python 3.11+ 内置 `tomllib`，3.10 用 `tomli`（纯 Python 后备）
- **写入:** 需要 `tomli_w`（轻量、无依赖）
- 项目要求 Python 3.10+，所以需要兼容处理读取库：

```python
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
```

置信度: HIGH（Python 标准库文档）

## 集成点

### 外部服务

| 服务 | 集成模式 | 注意事项 |
|------|----------|----------|
| OpenAI 注册接口 | curl_cffi HTTP 请求 | 与 TUI 无关，纯执行层 |
| DuckMail API | REST API + Bearer | API key 存入 Profile |
| Mailcow | REST API + IMAP | 多个凭证字段需在 TUI 中分步输入 |
| Mail.tm | REST API | 最简单，几乎无需配置 |
| CPA 上传 | HTTP POST | URL + Token 存入 Profile |
| Sub2API | HTTP POST + group 选择 | group 选择可在 TUI 中完成或延迟到执行时 |

### 内部边界

| 边界 | 通信方式 | 注意事项 |
|------|----------|----------|
| TUI → 配置层 | 函数调用 (`ProfileManager.save/load`) | TUI 运行期间调用，同进程 |
| 配置层 → 执行层 | 配置字典参数传递 | TUI 退出后发生 |
| CLI → 配置层 | 函数调用 | `--profile` 参数触发 `load()` |
| 执行层 → 集成层 | 直接函数调用，ThreadPoolExecutor 内 | 保持现有模式不变 |

## 构建顺序建议

基于组件依赖关系，推荐以下构建顺序：

| 顺序 | 组件 | 依赖前置 | 理由 |
|------|------|----------|------|
| 1 | `RegisterConfig` dataclass + schema | 无 | 所有其他组件的基石，定义字段就是定义接口 |
| 2 | `ProfileManager` (TOML 读写) | schema | TUI 和 CLI 都需要它，且可独立测试 |
| 3 | 单文件拆包 (adapters/, core/, upload/) | schema | 消除全局变量依赖，让 `run_batch()` 接受 config 参数 |
| 4 | TUI 向导 (Textual screens) | schema, ProfileManager | 此时有明确的数据接口可对接 |
| 5 | CLI 入口重写 (集成 TUI + Profile) | 以上全部 | 最后一步，把所有组件串起来 |
| 6 | config.json 迁移工具 | ProfileManager | 可选，帮助老用户迁移 |

**顺序理由:**
- schema 必须先行，否则后续每个组件都在猜测字段定义
- ProfileManager 先于 TUI，因为 TUI 需要知道"保存到哪"和"加载什么"
- 单文件拆包必须在 TUI 之前，否则 TUI 生成的配置没法传给 `run_batch()`（当前 `run_batch()` 依赖全局变量）
- CLI 入口最后重写，因为它是所有组件的集成点

## 来源

- [Textual 官方文档 - App Basics](https://textual.textualize.io/guide/app/) - HIGH 置信度
- [Textual 官方文档 - Workers](https://textual.textualize.io/guide/workers/) - HIGH 置信度
- [Textual GitHub Discussion #1828 - 同步代码集成](https://github.com/Textualize/textual/discussions/1828) - MEDIUM 置信度
- [Real Python - Python Textual 教程](https://realpython.com/python-textual/) - MEDIUM 置信度
- [Textual API - App.exit()](https://textual.textualize.io/api/app/) - HIGH 置信度
- Python 3.11 `tomllib` 标准库文档 - HIGH 置信度

---
*架构研究: TUI 配置系统集成*
*研究日期: 2026-03-07*
