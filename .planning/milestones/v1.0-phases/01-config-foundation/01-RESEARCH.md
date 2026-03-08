# Phase 1: 配置层基础 - 研究

**研究日期:** 2026-03-07
**领域:** Pydantic v2 数据模型 + TOML 持久化
**置信度:** HIGH

<user_constraints>
## 用户约束 (来自 CONTEXT.md)

### 锁定决策
- 采用嵌套子模型结构：RegisterConfig 包含 EmailConfig、RegConfig（注册参数）、OAuthConfig、UploadConfig 等子模型
- TOML section 自然对应子模型层级：`[email]`、`[registration]`、`[oauth]`、`[upload]`
- 与未来 TUI 分屏向导的步骤对齐（每个子模型对应一屏）
- EmailConfig 包含 `provider: Literal["duckmail", "mailcow", "mailtm"]` 字段
- 三个平台的专属配置作为 Optional 子模型：`duckmail: DuckMailConfig | None`、`mailcow: MailcowConfig | None`、`mailtm: MailTmConfig | None`
- 通过 `@model_validator(mode="after")` 校验 provider 与对应子模型的一致性（选了 duckmail 则 duckmail 配置必填）
- TOML 中只写实际使用的平台 section，未使用的平台不需要出现
- UploadConfig 包含 `targets: list[Literal["cpa", "sub2api"]]`，允许空列表（不上传）
- CPA 和 Sub2API 各自为 Optional 子模型，validator 校验 targets 与子模型的一致性
- 校验失败时提供中文可读错误消息，不使用 Pydantic 默认的英文技术格式
- 模型结构应与 Phase 3 的 TUI 分步向导自然对齐——每个子模型对应向导的一个 Screen
- 现有 config.json 的字段命名可以在 Pydantic model 中使用更规范的名称，通过 `Field(alias=...)` 保持 TOML 可读性

### Claude 自主裁量
- Profile TOML 文件的命名规则和目录组织方式
- 全局变量收拢的具体迁移策略（一步切换 vs 过渡期）
- TOML 文件中的注释模板和 section 排列顺序
- ProfileManager 的具体 API 设计（方法签名、错误处理策略）

### 延迟事项 (不在范围内)
None — 讨论保持在阶段范围内
</user_constraints>

<phase_requirements>
## 阶段需求

| ID | 描述 | 研究支撑 |
|----|------|----------|
| CONF-01 | 用户配置以 TOML 格式保存为 profile 文件到 `~/.chatgpt-register/profiles/` | tomli-w 写入 TOML、tomllib 读取 TOML、ProfileManager 文件 I/O 模式 |
| CONF-02 | 支持通过参数指定 profile 存储路径 | ProfileManager 构造函数接受 `base_dir: Path` 参数，默认 `~/.chatgpt-register/profiles/` |
| CONF-03 | Pydantic 模型校验所有配置项，即时反馈错误 | Pydantic v2 `@model_validator(mode="after")`、自定义中文 `ValidationError` 消息 |
| ARCH-02 | 收拢 20+ 全局变量为配置 dataclass/Pydantic model，`run_batch()` 接受配置参数 | RegisterConfig 嵌套子模型覆盖 chatgpt_register.py:414-443 全部变量 |
</phase_requirements>

## 概要

本阶段的核心任务是将散落在 `chatgpt_register.py` 第 414-443 行的 20+ 个模块级全局变量收拢为一个结构化的 Pydantic v2 数据模型 `RegisterConfig`，并通过 `ProfileManager` 实现 TOML 文件的持久化。项目运行在 Python 3.14 上，已有 `tomllib` 标准库可读取 TOML，只需额外引入 `tomli-w` 用于写入。

Pydantic v2（当前稳定版 2.12.5）提供了完整的验证和序列化能力。通过 `model_validate()` 从 TOML 解析后的 dict 创建模型实例，通过 `model_dump(exclude_none=True)` 导出为 dict 再由 `tomli-w` 写入 TOML。`@model_validator(mode="after")` 可实现 provider 与对应子模型的联动校验。

现有 `config.example.json` 包含完整的字段清单（约 30 个配置键），已有清晰的分类：邮箱平台（3 种）、代理、OAuth、上传目标（CPA/Sub2API）。这些字段自然映射为嵌套子模型。

**核心建议:** 使用 Pydantic v2.12+ `BaseModel` 嵌套子模型 + `tomllib`（读）+ `tomli-w`（写），ProfileManager 作为纯粹的文件 I/O 管理器。

## 技术栈

### 核心

| 库 | 版本 | 用途 | 为何选择 |
|----|------|------|----------|
| pydantic | >=2.12,<3 | 数据模型定义、校验、序列化 | Python 生态标准数据验证库，Rust 核心性能优异 |
| tomllib | stdlib (Python 3.11+) | 读取 TOML 文件 | 标准库，零依赖，Python 3.14 已内置 |
| tomli-w | >=1.2 | 写入 TOML 文件 | tomllib 的官方写入对应库，轻量快速 |

### 辅助

| 库 | 版本 | 用途 | 使用场景 |
|----|------|------|----------|
| pydantic[email] | 与核心同版本 | EmailStr 类型验证 | 如果需要验证邮箱地址格式（本项目暂不需要） |

### 备选方案对比

| 当前选择 | 备选 | 权衡 |
|----------|------|------|
| tomli-w | tomlkit | tomlkit 支持保留注释和格式（round-trip），但解析慢 25-60x，且返回自定义类型而非标准 dict。本项目是新建 TOML 文件不需要 round-trip，tomli-w 更合适 |
| pydantic BaseModel | dataclasses + 手动校验 | Pydantic 提供开箱即用的嵌套模型校验、自定义错误消息、序列化，手动实现工作量大且易出错 |
| pydantic BaseModel | pydantic-settings BaseSettings | BaseSettings 自动读取环境变量，但本阶段聚焦 TOML 持久化，环境变量优先级将在后续阶段处理 |

**安装命令:**
```bash
uv add "pydantic>=2.12,<3" "tomli-w>=1.2"
```

## 架构模式

### 推荐项目结构

本阶段新增文件放在项目根目录（与现有 `chatgpt_register.py` 同级），Phase 2 再做包拆分：

```
chatgpt_register/           # 项目根目录
├── chatgpt_register.py     # 现有主文件（本阶段不改动主逻辑）
├── config_model.py          # NEW: RegisterConfig + 所有子模型
├── profile_manager.py       # NEW: ProfileManager TOML 持久化
├── config.example.json      # 现有，保留参考
└── tests/
    ├── __init__.py
    ├── conftest.py           # NEW: 共享 fixtures
    ├── test_config_model.py  # NEW: 模型校验测试
    └── test_profile_manager.py # NEW: ProfileManager 测试
```

### 模式 1: 嵌套子模型 + Discriminated Union

**说明:** 用 `@model_validator(mode="after")` 实现 provider 与子模型的联动校验。

**使用场景:** EmailConfig 中 provider 字段决定哪个平台子模型必填。

**示例:**
```python
# Source: Pydantic v2 官方文档 - Validators
from typing import Literal
from pydantic import BaseModel, model_validator

class DuckMailConfig(BaseModel):
    api_base: str = "https://api.duckmail.sbs"
    bearer: str

class MailcowConfig(BaseModel):
    api_url: str
    api_key: str
    domain: str
    imap_host: str
    imap_port: int = 993

class MailTmConfig(BaseModel):
    api_base: str = "https://api.mail.tm"

class EmailConfig(BaseModel):
    provider: Literal["duckmail", "mailcow", "mailtm"]
    duckmail: DuckMailConfig | None = None
    mailcow: MailcowConfig | None = None
    mailtm: MailTmConfig | None = None

    @model_validator(mode="after")
    def check_provider_config(self) -> "EmailConfig":
        mapping = {
            "duckmail": self.duckmail,
            "mailcow": self.mailcow,
            "mailtm": self.mailtm,
        }
        cfg = mapping.get(self.provider)
        if cfg is None:
            raise ValueError(
                f"选择了 {self.provider} 邮箱平台，"
                f"但未提供 [{self.provider}] 配置节"
            )
        return self
```

### 模式 2: TOML 读写 + model_dump(exclude_none=True)

**说明:** 写入 TOML 时排除 None 字段，保证 TOML 文件中只出现用户实际配置的平台 section。

**使用场景:** ProfileManager 的 save/load 方法。

**示例:**
```python
# Source: tomllib stdlib docs + tomli-w PyPI docs
import tomllib
import tomli_w
from pathlib import Path

def save_profile(config: RegisterConfig, path: Path) -> None:
    data = config.model_dump(exclude_none=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)

def load_profile(path: Path) -> RegisterConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return RegisterConfig.model_validate(data)
```

### 模式 3: 自定义中文错误消息

**说明:** 覆盖 Pydantic 默认错误输出，提供中文可读消息。

**使用场景:** 校验失败时的用户反馈。

**示例:**
```python
from pydantic import ValidationError

def format_validation_errors(e: ValidationError) -> str:
    """将 Pydantic ValidationError 格式化为中文可读消息"""
    messages = []
    for error in e.errors():
        loc = " -> ".join(str(l) for l in error["loc"])
        msg = error["msg"]
        messages.append(f"  配置项 [{loc}]: {msg}")
    return "配置校验失败:\n" + "\n".join(messages)
```

### 反模式

- **在 model_validator 中直接抛出英文 ValueError:** 用户看到的应该是中文消息。在 validator 中的 `raise ValueError(...)` 消息应使用中文。
- **用 dict 代替嵌套子模型:** 失去类型安全和自动校验，未来 TUI 无法直接映射到 Screen。
- **在 RegisterConfig 中硬编码文件路径:** 持久化逻辑属于 ProfileManager，模型只负责数据结构和校验。
- **一次性替换所有全局变量引用:** Phase 1 只定义模型和 ProfileManager，全局变量的消费者（`run_batch()` 等）在 Phase 2 迁移。

## 不要手动实现

| 问题 | 不要自己写 | 使用替代 | 原因 |
|------|-----------|----------|------|
| 配置校验 | 手写 if/else 校验链 | Pydantic `@model_validator` + `@field_validator` | 嵌套模型校验、类型转换、错误聚合都由 Pydantic 处理 |
| TOML 序列化 | 手动拼接 TOML 字符串 | `tomli-w` | TOML 格式有复杂的转义和类型映射规则 |
| TOML 反序列化 | 手写解析器 | `tomllib` (stdlib) | 标准库实现，完全符合 TOML v1.0 规范 |
| 路径展开 | 手动处理 `~` 和相对路径 | `Path.expanduser()` + `Path.resolve()` | 跨平台行为已由标准库处理 |

**核心洞察:** Pydantic v2 的嵌套模型 + model_validator 已经覆盖了所有联动校验需求，不需要任何自定义校验框架。

## 常见陷阱

### 陷阱 1: tomli-w 不支持所有 Python 类型

**问题:** `tomli-w.dump()` 只接受 TOML 兼容类型（str, int, float, bool, list, dict, datetime）。如果 `model_dump()` 返回 `Path` 对象或 `Enum` 值，写入会失败。
**原因:** Pydantic `model_dump()` 默认以 Python 模式序列化，保留原始类型。
**解决:** 使用 `model_dump(mode="json")` 确保所有值为 JSON 兼容的基础类型（str, int, float, bool, list, dict, None），这些类型同时兼容 TOML（除了 None，通过 `exclude_none=True` 排除）。
**预警信号:** `TypeError: Object of type X is not TOML serializable`

### 陷阱 2: TOML 不支持 None/null

**问题:** TOML 格式没有 null 概念。如果 `model_dump()` 输出包含 `None` 值，`tomli-w` 会报错。
**原因:** Optional 字段在 Pydantic 中默认为 `None`。
**解决:** 始终使用 `model_dump(mode="json", exclude_none=True)` 写入 TOML。读取时缺失的键会由 Pydantic 默认值填充。
**预警信号:** `TypeError: NoneType is not TOML serializable`

### 陷阱 3: model_validator 中的 ValidationError 消息被包装

**问题:** 在 `@model_validator(mode="after")` 中 `raise ValueError("中文消息")` 后，Pydantic 会将其包装为 `ValidationError`，错误信息变成嵌套结构。
**原因:** Pydantic 的错误聚合机制会在外层再包一层。
**解决:** 使用 `e.errors()` 遍历获取原始 `msg` 字段，而不是直接 `str(e)`。自定义格式化函数（见代码示例）。
**预警信号:** 用户看到原始 JSON 格式的错误信息

### 陷阱 4: TOML section 顺序与 model_dump 字典顺序

**问题:** `model_dump()` 输出的字典顺序决定 TOML 文件中 section 的排列顺序。如果子模型定义顺序不当，TOML 文件可读性差（比如把嵌套 table 放在简单键之前）。
**原因:** TOML 规范要求简单键在嵌套 table 之前。`tomli-w` 不会自动重排。
**解决:** 在 RegisterConfig 中按"简单字段在前、嵌套子模型在后"的顺序定义字段。或者在序列化时手动排序字典。
**预警信号:** 生成的 TOML 文件中 `[section]` 标记出现在同级简单键之前

### 陷阱 5: Literal 类型与 TOML 字符串大小写

**问题:** TOML 文件中用户可能写 `provider = "DuckMail"` 而 Literal 要求 `"duckmail"`。
**原因:** Pydantic Literal 默认严格匹配大小写。
**解决:** 使用 `@field_validator("provider", mode="before")` 在校验前转小写。
**预警信号:** 用户填写的 TOML 配置因大小写不匹配被拒绝

## 代码示例

以下示例基于官方文档验证：

### RegisterConfig 完整骨架

```python
# Source: 基于 config.example.json 字段映射 + Pydantic v2 文档模式
from __future__ import annotations
from typing import Literal
from pathlib import Path
from pydantic import BaseModel, Field, model_validator, field_validator

class DuckMailConfig(BaseModel):
    api_base: str = "https://api.duckmail.sbs"
    bearer: str

class MailcowConfig(BaseModel):
    api_url: str
    api_key: str
    domain: str
    imap_host: str
    imap_port: int = 993

class MailTmConfig(BaseModel):
    api_base: str = "https://api.mail.tm"

class EmailConfig(BaseModel):
    provider: Literal["duckmail", "mailcow", "mailtm"]
    duckmail: DuckMailConfig | None = None
    mailcow: MailcowConfig | None = None
    mailtm: MailTmConfig | None = None

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def check_provider_config(self) -> EmailConfig:
        mapping = {
            "duckmail": self.duckmail,
            "mailcow": self.mailcow,
            "mailtm": self.mailtm,
        }
        if mapping.get(self.provider) is None:
            raise ValueError(
                f"选择了 {self.provider} 邮箱平台，"
                f"但未提供 [{self.provider}] 配置节"
            )
        return self

class OAuthConfig(BaseModel):
    enabled: bool = True
    required: bool = True
    issuer: str = "https://auth.openai.com"
    client_id: str = "app_EMoamEEZ73f0CkXaXp7hrann"
    redirect_uri: str = "http://localhost:1455/auth/callback"

class CpaConfig(BaseModel):
    api_url: str
    api_token: str

class Sub2ApiConfig(BaseModel):
    api_base: str
    admin_api_key: str
    bearer_token: str
    group_ids: list[int] = []
    account_concurrency: int = 1
    account_priority: int = 1

class UploadConfig(BaseModel):
    targets: list[Literal["cpa", "sub2api"]] = []
    cpa: CpaConfig | None = None
    sub2api: Sub2ApiConfig | None = None

    @model_validator(mode="after")
    def check_target_configs(self) -> UploadConfig:
        if "cpa" in self.targets and self.cpa is None:
            raise ValueError("上传目标包含 cpa，但未提供 [upload.cpa] 配置节")
        if "sub2api" in self.targets and self.sub2api is None:
            raise ValueError("上传目标包含 sub2api，但未提供 [upload.sub2api] 配置节")
        return self

class RegConfig(BaseModel):
    """注册参数"""
    total_accounts: int = Field(default=5, ge=1, description="注册账号数量")
    proxy: str = ""
    output_file: str = "registered_accounts.txt"
    ak_file: str = "ak.txt"
    rk_file: str = "rk.txt"
    token_json_dir: str = "codex_tokens"

class RegisterConfig(BaseModel):
    """顶层配置，TOML 文件的根结构"""
    email: EmailConfig
    registration: RegConfig = RegConfig()
    oauth: OAuthConfig = OAuthConfig()
    upload: UploadConfig = UploadConfig()
```

### ProfileManager 骨架

```python
# Source: 设计模式 — 基于 tomllib/tomli-w 官方 API
from __future__ import annotations
import tomllib
import tomli_w
from pathlib import Path

_DEFAULT_BASE = Path.home() / ".chatgpt-register" / "profiles"

class ProfileManager:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = (base_dir or _DEFAULT_BASE).expanduser().resolve()

    def save(self, name: str, config: RegisterConfig) -> Path:
        """保存配置为 TOML profile 文件"""
        path = self.base_dir / f"{name}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = config.model_dump(mode="json", exclude_none=True)
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
        return path

    def load(self, name: str) -> RegisterConfig:
        """从 TOML profile 文件加载配置"""
        path = self.base_dir / f"{name}.toml"
        if not path.exists():
            raise FileNotFoundError(f"Profile 不存在: {path}")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return RegisterConfig.model_validate(data)

    def list_profiles(self) -> list[str]:
        """列举所有已保存的 profile 名称"""
        if not self.base_dir.exists():
            return []
        return sorted(p.stem for p in self.base_dir.glob("*.toml"))

    def exists(self, name: str) -> bool:
        return (self.base_dir / f"{name}.toml").exists()

    def delete(self, name: str) -> None:
        path = self.base_dir / f"{name}.toml"
        if path.exists():
            path.unlink()
```

### TOML 输出示例

上述模型 `model_dump(mode="json", exclude_none=True)` 后经 `tomli-w` 写入的效果：

```toml
[email]
provider = "duckmail"

[email.duckmail]
api_base = "https://api.duckmail.sbs"
bearer = "my-token"

[registration]
total_accounts = 10
proxy = "socks5://127.0.0.1:1080"
output_file = "registered_accounts.txt"
ak_file = "ak.txt"
rk_file = "rk.txt"
token_json_dir = "codex_tokens"

[oauth]
enabled = true
required = true
issuer = "https://auth.openai.com"
client_id = "app_EMoamEEZ73f0CkXaXp7hrann"
redirect_uri = "http://localhost:1455/auth/callback"

[upload]
targets = ["cpa"]

[upload.cpa]
api_url = "https://cpa.example.com/api"
api_token = "my-cpa-token"
```

## 技术现状

| 旧方案 | 当前方案 | 变更时间 | 影响 |
|--------|----------|----------|------|
| Pydantic v1 (`validator`, `Config` 内部类) | Pydantic v2 (`model_validator`, `model_config`) | 2023-06 | v2 API 完全不同，不要参考 v1 示例 |
| `toml` 第三方库 | `tomllib` (stdlib) + `tomli-w` | Python 3.11 (2022-10) | `toml` 库已不再维护，标准库才是正确选择 |
| dataclass + 手动校验 | Pydantic BaseModel | 持续演进 | Pydantic 已成为 Python 配置校验的事实标准 |

**已过时/弃用:**
- `toml` 库 (PyPI)：已停止维护，请使用 `tomllib` + `tomli-w`
- Pydantic v1 API（`@validator`、`class Config`）：v2 完全替换，迁移指南见官方文档

## 开放问题

1. **Profile 命名规则**
   - 已知信息：文件存储为 `{name}.toml`，需要确保文件名安全
   - 不明确处：是否需要限制命名（仅允许 `[a-z0-9_-]`）？是否需要默认 profile 名？
   - 建议：限制为 `[a-z0-9][a-z0-9_-]*`，最大长度 64 字符。提供 `default` 作为默认名。

2. **全局变量过渡策略**
   - 已知信息：Phase 1 只创建模型，Phase 2 才做消费者迁移
   - 不明确处：Phase 1 是否需要提供一个 `from_legacy_dict(config_dict)` 类方法来兼容旧的 `_load_config()` 返回值？
   - 建议：在 Phase 1 中实现 `RegisterConfig.from_legacy_dict()` 类方法，Phase 2 可以渐进式迁移而不需要一次性改完。

3. **TOML section 排列顺序**
   - 已知信息：`tomli-w` 保持字典键序
   - 不明确处：用户是否在意 TOML 文件中的 section 排列？
   - 建议：按 `email` -> `registration` -> `oauth` -> `upload` 顺序排列，与向导步骤一致。在 `model_dump` 后无需额外排序，因为 Pydantic 默认按字段定义顺序输出。

## 验证架构

### 测试框架

| 属性 | 值 |
|------|-----|
| 框架 | pytest (需新增安装) |
| 配置文件 | none — Wave 0 需创建 |
| 快速运行命令 | `python -m pytest tests/ -x -q` |
| 完整套件命令 | `python -m pytest tests/ -v` |

### 阶段需求 -> 测试映射

| Req ID | 行为 | 测试类型 | 自动化命令 | 文件存在？ |
|--------|------|----------|-----------|-----------|
| CONF-01 | RegisterConfig 实例保存为 TOML 文件，内容可读可解析 | unit | `python -m pytest tests/test_profile_manager.py::test_save_and_load -x` | 需创建 |
| CONF-02 | ProfileManager 接受自定义 base_dir 参数 | unit | `python -m pytest tests/test_profile_manager.py::test_custom_base_dir -x` | 需创建 |
| CONF-03 | 校验失败时返回清晰中文错误（provider 不匹配、必填项缺失等） | unit | `python -m pytest tests/test_config_model.py::test_validation_errors -x` | 需创建 |
| ARCH-02 | RegisterConfig 覆盖所有 20+ 全局变量字段 | unit | `python -m pytest tests/test_config_model.py::test_field_coverage -x` | 需创建 |

### 采样频率
- **每次任务提交:** `python -m pytest tests/ -x -q`
- **每个 wave 合并:** `python -m pytest tests/ -v`
- **阶段门控:** 完整套件全绿方可通过 `/gsd:verify-work`

### Wave 0 缺口
- [ ] `tests/__init__.py` — 空文件，标记为 Python 包
- [ ] `tests/conftest.py` — 共享 fixtures（示例 RegisterConfig 实例、临时目录）
- [ ] `tests/test_config_model.py` — 覆盖 CONF-03, ARCH-02
- [ ] `tests/test_profile_manager.py` — 覆盖 CONF-01, CONF-02
- [ ] 框架安装: `uv add --dev pytest` — 当前未检测到 pytest

## 来源

### 主要来源 (HIGH 置信度)
- [Pydantic v2 官方文档 - Models](https://docs.pydantic.dev/latest/concepts/models/) — 模型定义、model_config
- [Pydantic v2 官方文档 - Validators](https://docs.pydantic.dev/latest/concepts/validators/) — model_validator、field_validator API
- [Pydantic v2 官方文档 - Serialization](https://docs.pydantic.dev/latest/concepts/serialization/) — model_dump 参数
- [Python 标准库 - tomllib](https://docs.python.org/3/library/tomllib.html) — TOML 读取 API
- [tomli-w PyPI](https://pypi.org/project/tomli-w/) — 版本 1.2.0，TOML 写入 API
- [Pydantic PyPI](https://pypi.org/project/pydantic/) — 当前稳定版 2.12.5

### 次要来源 (MEDIUM 置信度)
- [DEV.to TOML 库对比](https://dev.to/pypyr/comparison-of-python-toml-parser-libraries-595e) — tomli-w vs tomlkit 性能对比
- [Real Python - Python and TOML](https://realpython.com/python-toml/) — TOML 读写最佳实践

### 三级来源 (LOW 置信度)
- 无

## 元数据

**置信度分项:**
- 技术栈: HIGH — Pydantic v2 和 tomllib/tomli-w 均为成熟稳定的库，有官方文档验证
- 架构: HIGH — 嵌套子模型模式是 Pydantic 官方推荐的配置管理方式
- 陷阱: HIGH — 所有陷阱均来自官方文档中明确说明的 API 行为

**研究日期:** 2026-03-07
**有效期至:** 2026-04-07（Pydantic 和 TOML 生态稳定，30 天内不会有重大变化）
