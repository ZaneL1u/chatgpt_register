# 架构分析：v1.1 反风控增强

**领域:** ChatGPT 批量注册 CLI 工具 — 反检测增强
**研究日期:** 2026-03-14
**整体置信度:** HIGH（基于完整代码阅读，非外部推测）

## 现有架构概览

### 系统概览

```
┌─────────────────────────────────────────────────────────────┐
│                        入口层                                │
│  cli.py → wizard.py (questionary TUI → RegisterConfig)       │
├─────────────────────────────────────────────────────────────┤
│                        编排层                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  core/batch.py — run_batch()                        │    │
│  │  ThreadPoolExecutor(N workers)                      │    │
│  │  _register_one(idx, config) per worker              │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                        执行层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ core/        │  │ adapters/    │  │ upload/      │       │
│  │ register.py  │  │ duckmail.py  │  │ cpa.py       │       │
│  │ http.py      │  │ mailtm.py    │  │ sub2api.py   │       │
│  │ sentinel.py  │  │ catchmail.py │  │              │       │
│  │ tokens.py    │  │ maildrop.py  │  │              │       │
│  │ utils.py     │  │ mailcow.py   │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                        配置层                                │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ config/model.py  │  │ config/profile.py│                 │
│  │ RegisterConfig   │  │ ProfileManager   │                 │
│  │ (Pydantic v2)    │  │ (TOML 持久化)    │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                   ~/.chatgpt-register/profiles/              │
└─────────────────────────────────────────────────────────────┘
```

### 组件职责

| 组件 | 职责 | 实现方式 |
| ------ | ------ | ---------- |
| `cli.py` | 解析 CLI 参数，决定交互/非交互启动 | argparse，入口唯一 |
| `wizard.py` | 引导用户配置，生成 RegisterConfig | questionary 问答 |
| `core/batch.py` | 并发编排，run_batch() 是唯一调度点 | ThreadPoolExecutor |
| `core/register.py` | 单次注册完整流程（注册+OTP+OAuth） | curl_cffi Sessions |
| `core/http.py` | HTTP 指纹：Chrome 版本、延迟、trace headers | curl_cffi impersonate |
| `core/sentinel.py` | PoW 挑战求解 | 纯 CPU 计算 |
| `adapters/*.py` | 与各临时邮箱 API 交互，创建/读取邮箱 | HTTP + polling |
| `upload/*.py` | 将注册结果上传到 CPA/Sub2API | HTTP POST |
| `config/model.py` | 配置数据模型，唯一真相来源 | Pydantic v2 BaseModel |
| `config/profile.py` | Profile TOML 读写，多套配置管理 | tomllib/tomli_w |
| `dashboard.py` | 实时运行状态面板 | Rich Live |

### 现有包结构

```
chatgpt_register/
├── cli.py                   # 入口，argparse
├── wizard.py                # TUI 向导，生成 RegisterConfig
├── dashboard.py             # Rich 实时面板
├── config/
│   ├── model.py             # RegisterConfig Pydantic 模型
│   └── profile.py           # ProfileManager，TOML 持久化
├── core/
│   ├── batch.py             # run_batch()，ThreadPoolExecutor
│   ├── register.py          # ChatGPTRegister，注册流程
│   ├── http.py              # Chrome 指纹、延迟、trace headers
│   ├── sentinel.py          # PoW 挑战
│   ├── tokens.py            # token 保存逻辑
│   └── utils.py             # 密码/姓名/生日纯函数
├── adapters/
│   ├── base.py              # EmailAdapter 基类
│   ├── __init__.py          # build_email_adapter 工厂
│   ├── duckmail.py
│   ├── mailtm.py
│   ├── catchmail.py
│   ├── maildrop.py
│   └── mailcow.py
└── upload/
    ├── __init__.py
    ├── common.py
    ├── cpa.py
    └── sub2api.py
```

## 四大特性集成方案

### 特性 1：邮箱名拟人化

**问题定位：** 邮箱 local-part 生成散落在各适配器中，均为纯随机字符串。

- `DuckMailAdapter.create_temp_email()` 第 33-34 行：`"".join(random.choice(chars) for _ in range(...))`
- 其他适配器类似，各自独立生成乱码 local-part

**集成方案：**

```
新增文件：
  core/humanize.py
    ├── generate_humanized_local(style="firstname_lastname") → str
    │   策略：firstname.lastname + 2-4 位数字，如 "emma.davis2847"
    │   数据源：复用 utils.py 已有的 first/last name 列表并大幅扩充
    └── FIRST_NAMES / LAST_NAMES 常量池（各 100+ 条目）

修改文件：
  config/model.py
    └── RegConfig 新增字段：humanize_email: bool = True
  adapters/duckmail.py, mailtm.py, catchmail.py, maildrop.py, mailcow.py
    └── create_temp_email() 中调用 generate_humanized_local() 替代随机字符串
  wizard.py
    └── _ask_registration_config() 新增是否开启拟人化邮箱的询问
```

**架构决策：** 拟人化逻辑集中在 `core/humanize.py`，不分散到每个适配器。适配器只负责「用给定的 local-part 创建邮箱」，local-part 的生成策略由上层决定。未来扩展拟人化策略（如中文拼音风格）时只改一个文件。

**对 `_register_one` 的影响：** 无。`_register_one` 调用 `reg.create_temp_email()` 不变，变化封装在适配器内部。

### 特性 2：批次输出归档

**问题定位：** 当前所有输出文件路径硬编码在 `RegConfig` 默认值中，所有批次写入同一文件：
- `output_file = "registered_accounts.txt"`（追加模式）
- `ak_file = "ak.txt"` / `rk_file = "rk.txt"`（追加模式）
- `token_json_dir = "codex_tokens"`（固定目录）

多次运行后文件混在一起，无法区分批次。

**集成方案：**

```
新增文件：
  core/output.py
    ├── create_batch_output_dir(base: str = "output") → Path
    │   生成路径：output/20260314-2035/  (年月日-时分)
    ├── resolve_output_paths(batch_dir: Path, config: RegConfig) → ResolvedPaths
    │   将 config 中的相对路径解析到 batch_dir 下
    └── ResolvedPaths (dataclass)
        ├── output_file: Path
        ├── ak_file: Path
        ├── rk_file: Path
        ├── token_json_dir: Path
        └── log_file: Path

修改文件：
  config/model.py
    └── RegConfig 新增字段：batch_output_dir: str = "output"
                           organize_by_batch: bool = True
  core/batch.py
    └── run_batch() 开头调用 create_batch_output_dir()，
        将 output_file / ak_file 等路径重定向到批次目录，
        批次结束后打印实际输出目录路径
  core/tokens.py
    └── save_codex_tokens() 中的 token_json_dir 改为接收已解析的绝对路径
  wizard.py
    └── _ask_registration_config() 新增输出目录配置项
```

**架构决策：** `run_batch()` 在启动 ThreadPoolExecutor 之前一次性计算好所有输出路径，然后透传给 `_register_one`。不在 worker 内部创建目录，避免竞态。路径解析逻辑集中在 `core/output.py`。

**对 `_register_one` 的影响：** 接收已解析的 `output_file` 路径（当前已是参数），无需改签名，只需 `run_batch` 传入新路径。

### 特性 3：多代理调度

**问题定位：** 当前 `RegConfig.proxy` 是单一 `str`，所有 worker 共用同一代理。

```python
# ChatGPTRegister.__init__ 第 65-67 行：
self.proxy = proxy if proxy is not None else (config.registration.proxy or None)
if self.proxy:
    self.session.proxies = {"http": self.proxy, "https": self.proxy}
```

**集成方案：**

```
新增文件：
  core/proxy.py
    ├── ProxyPool
    │   ├── __init__(proxies: list[str])
    │   ├── acquire(worker_id: int) → str | None
    │   │   策略：round-robin，同一 worker 始终用同一代理
    │   │   实现：proxies[worker_id % len(proxies)]
    │   └── proxies: list[str]（去重后的代理列表）
    └── parse_proxy_list(raw: str) → list[str]
        支持格式：逗号分隔、换行分隔、文件路径（@proxies.txt）

修改文件：
  config/model.py
    └── RegConfig:
        proxy: str = ""  →  保留（向下兼容，单代理场景）
        proxies: list[str] = Field(default_factory=list)  ← 新增
        @model_validator: 若 proxy 非空且 proxies 为空，自动将 proxy 加入 proxies
  core/batch.py
    └── run_batch():
        1. 构建 ProxyPool(config.registration.proxies)
        2. _register_one 传入 proxy_override 参数
        3. 每个 worker 调用 proxy_pool.acquire(idx) 获取分配的代理
        4. Dashboard 显示当前 worker 使用的代理标识
  core/register.py
    └── ChatGPTRegister.__init__():
        proxy 参数已存在，无需改签名。
        run_batch 传入 proxy_pool.acquire(idx) 即可
  wizard.py
    └── _ask_registration_config():
        "代理地址" 改为支持多行输入或文件路径
```

**架构决策：**
1. **Round-robin 而非随机分配**：确保同一 worker 的整个注册流程（注册 + OTP + OAuth）使用同一代理，避免 IP 切换触发风控。
2. **ProxyPool 无锁**：因为 `acquire(worker_id)` 是纯计算（取模），不需要锁。
3. **向下兼容**：`proxy` 字段保留，单代理用户无需改配置。

**对 `_register_one` 的影响：** 新增 `proxy` 参数从 `proxy_pool.acquire(idx)` 获取，替代直接读 `config.registration.proxy`。改动局限在 `run_batch` 调用 `_register_one` 的参数传递。

### 特性 4：反机器人风险排查与加固

**问题定位：** 现有代码已做了相当多反检测工作，但仍有改进空间。

**已有的反检测措施（代码中确认）：**
- `curl_cffi` 的 `impersonate` 模式模拟真实 Chrome TLS 指纹（http.py）
- 随机 Chrome 版本 + 对应 sec-ch-ua（http.py `CHROME_PROFILES`）
- 随机延迟 `random_delay()`（register.py 多处调用）
- 真实 traceparent / datadog headers（http.py `make_trace_headers`）
- Sentinel PoW 挑战求解（sentinel.py）
- 随机 device_id（uuid4）
- 随机 Accept-Language 组合

**仍存在的风险点：**

| 风险 | 位置 | 现状 | 建议 |
| ------ | ------ | ------ | ------ |
| 请求间隔过于均匀 | register.py `random_delay()` | 均匀分布 U(0.3, 0.8) | 改为偏态分布（对数正态），模拟人类不规则节奏 |
| Chrome profile 池太小 | http.py `CHROME_PROFILES` | 仅 4 个版本 | 扩充至 8-12 个常见版本 |
| 平台指纹固定 Windows | register.py 第 79-82 行 | 固定 `"Windows"`, `"x86"` | 加入 macOS 和 Linux 指纹概率混合 |
| 密码模式可识别 | utils.py `generate_password()` | 固定长度 14，固定特殊字符集 | 随机长度 12-18，更丰富的特殊字符 |
| 并发启动无 stagger | batch.py `ThreadPoolExecutor` | 所有 worker 同时启动 | 加入随机启动延迟，避免同一秒发出 N 个首请求 |
| Accept-Language 候选太少 | register.py 第 71-75 行 | 仅 4 种 | 扩充到 10+ 种常见组合 |

**集成方案：** 不新增独立模块，在现有文件中修改。

```
修改文件：
  core/http.py
    ├── CHROME_PROFILES 扩充（8-12 个版本）
    ├── random_delay() 改为偏态分布
    ├── 新增 random_platform() → (platform, arch, bitness) 三元组
    └── 新增 ACCEPT_LANGUAGE_POOL 常量（10+ 种）
  core/register.py
    └── ChatGPTRegister.__init__() 使用 random_platform() 设置 headers
  core/batch.py
    └── run_batch() 在 submit 循环中加入 stagger 延迟：
        for idx in range(1, total+1):
            if idx > 1:
                time.sleep(random.uniform(0.5, 2.0))  # stagger
            executor.submit(...)
  core/utils.py
    └── generate_password() 改为随机长度 + 更丰富字符集
```

## 组件边界总结

| 组件 | 职责 | 交互对象 |
| ------ | ------ | ---------- |
| `core/humanize.py`（新增） | 拟人邮箱 local-part 生成 | adapters/*.py |
| `core/output.py`（新增） | 批次目录创建与路径解析 | core/batch.py, core/tokens.py |
| `core/proxy.py`（新增） | 多代理池管理与调度 | core/batch.py |
| `core/http.py`（修改） | 扩充指纹池、改进延迟分布 | core/register.py |
| `core/batch.py`（修改） | 集成代理池、批次目录、stagger | 所有新增组件 |
| `config/model.py`（修改） | 新增配置字段 | 所有消费配置的模块 |
| `wizard.py`（修改） | 新增配置问答项 | config/model.py |
| `adapters/*.py`（修改） | 调用 humanize 生成 local-part | core/humanize.py |

## 数据流

### 变更前

```
RegisterConfig.registration.proxy（单个 str）
  → ChatGPTRegister(proxy=config.registration.proxy)
    → session.proxies = {"http": proxy, "https": proxy}

RegisterConfig.registration.output_file（固定路径）
  → _register_one(..., output_file)
    → open(output_file, "a")  # 所有批次追加到同一文件

适配器 create_temp_email()
  → random.choice(chars) * N  # 乱码 local-part
```

### 变更后

```
RegisterConfig.registration.proxies（list[str]）
  → ProxyPool(proxies)
    → proxy_pool.acquire(worker_id)  # round-robin，同 worker 同代理
      → ChatGPTRegister(proxy=assigned_proxy)

RegisterConfig.registration.batch_output_dir
  → create_batch_output_dir() → output/20260314-2035/
    → resolve_output_paths(batch_dir, config) → ResolvedPaths
      → _register_one(..., output_file=batch_dir/registered_accounts.txt)

RegisterConfig.registration.humanize_email = True
  → generate_humanized_local()  # emma.davis2847
    → 适配器 create_temp_email(local_part=...)
```

### 完整注册流程（变更后）

```
RegisterConfig
  → run_batch()
      ├── ProxyPool(config.proxies)                 # 代理池初始化
      ├── create_batch_output_dir()                 # 批次目录创建（一次性）
      ├── resolve_output_paths() → ResolvedPaths    # 路径解析（一次性）
      └── stagger loop → ThreadPoolExecutor
            └── _register_one(idx, config, proxy, resolved_paths)
                  ├── generate_humanized_local()    # 拟人邮箱前缀
                  ├── adapter.create_temp_email()   # 创建邮箱
                  ├── ChatGPTRegister(proxy=proxy)  # 分配代理
                  ├── run_register()                # 注册+OTP
                  ├── perform_codex_oauth_login_http()
                  └── save_tokens(resolved_paths)   # 写到批次目录
```

## 架构模式

### 模式 1：配置驱动一切

**什么：** 所有新行为通过 `RegisterConfig` 字段控制，不引入环境变量或 CLI 参数。

**适用条件：** 任何新的可配置行为。

**权衡：** 每次新增配置项都需要同时更新 model.py + wizard.py，有少量开销，但保证了统一入口。

**示例：**
```python
# 正确：新字段加在 RegConfig 中
class RegConfig(BaseModel):
    humanize_email: bool = True
    proxies: list[str] = Field(default_factory=list)
    batch_output_dir: str = "output"
    organize_by_batch: bool = True

# 错误：引入环境变量
HUMANIZE = os.environ.get("HUMANIZE_EMAIL", "true")
```

### 模式 2：适配器只做 IO，策略在上层

**什么：** 适配器（adapters/）负责与邮箱 API 交互，不负责生成邮箱地址格式策略。

**适用条件：** 跨适配器的通用策略，如 local-part 生成。

**权衡：** 需要适配器接受 local_part 参数，接口略有变化，但消除了重复逻辑。

**示例：**
```python
# 正确：适配器接收 local_part 参数
class DuckMailAdapter:
    def create_temp_email(self, local_part: str | None = None):
        if local_part is None:
            local_part = generate_humanized_local()
        ...

# 错误：每个适配器自己实现拟人化
class DuckMailAdapter:
    def _generate_human_name(self):  # 重复逻辑
        ...
```

### 模式 3：run_batch 是唯一编排点

**什么：** 所有编排逻辑（代理分配、输出目录创建、stagger 延迟）集中在 `run_batch()`。

**适用条件：** 任何影响并发行为或全局状态的逻辑。

**权衡：** run_batch 职责变重，但 worker 和注册类保持无状态，测试更容易。

## 反模式

### 反模式 1：Worker 内部创建目录

**错误做法：** 在 `_register_one` 中调用 `mkdir`。

**为什么错误：** 多个 worker 同时创建同一目录产生竞态，且 `exist_ok=True` 虽然不报错但语义不清晰。

**正确做法：** `run_batch()` 在启动 worker 之前一次性创建好所有目录。

### 反模式 2：代理状态共享

**错误做法：** 用 `threading.Lock` 保护的共享代理计数器。

**为什么错误：** round-robin 分配是纯函数（`worker_id % len(proxies)`），不需要可变状态，不需要锁。

**正确做法：** `ProxyPool.acquire(worker_id)` 纯计算，无状态，无锁。

### 反模式 3：在 Pydantic 模型中加业务逻辑

**错误做法：** 在 `RegisterConfig` 的 validator 中执行代理解析或目录创建。

**为什么错误：** 配置模型应只做数据校验，不做副作用操作。代理解析和目录创建属于运行时逻辑。

**正确做法：** validator 只做格式校验（如 URL 格式），运行时逻辑放在 `run_batch()` 开头。

## 集成点

### 新增模块与现有模块的依赖关系

| 边界 | 通信方式 | 注意事项 |
| ------ | ---------- | ---------- |
| `core/humanize.py` ↔ `adapters/*.py` | 直接函数调用 | 适配器需新增 local_part 可选参数 |
| `core/output.py` ↔ `core/batch.py` | 函数调用，返回 ResolvedPaths | batch.py 在 ThreadPoolExecutor 启动前调用 |
| `core/output.py` ↔ `core/tokens.py` | ResolvedPaths 中的绝对路径 | tokens.py 接口需改为接收 Path 而非 str |
| `core/proxy.py` ↔ `core/batch.py` | ProxyPool 对象，acquire(idx) | batch.py 创建 ProxyPool，传给 _register_one |
| `config/model.py` ↔ 所有消费者 | Pydantic 模型字段 | 新字段均有默认值，向下兼容 |
| `wizard.py` ↔ `config/model.py` | 读写模型字段 | 所有新字段需在向导中有对应问答项 |

### 向下兼容性

| 变更 | 兼容策略 |
| ------ | ---------- |
| `proxy` → `proxies` 迁移 | `model_validator` 自动将单代理 `proxy` 迁移到 `proxies` 列表 |
| 输出路径变化 | `organize_by_batch: bool = True`，可关闭以保持旧行为 |
| 邮箱拟人化 | `humanize_email: bool = True`，可关闭以保持旧行为 |
| 现有 TOML profile | 新字段有默认值，旧 profile 加载时自动填充默认值 |

## 建议构建顺序

依赖关系分析：

```
1. config/model.py 字段扩展 ← 所有特性的基础
2. core/humanize.py ← 独立，无依赖
3. core/output.py ← 依赖 config/model.py 新字段
4. core/proxy.py ← 依赖 config/model.py 新字段
5. core/http.py 加固 ← 独立，纯扩充
6. adapters/*.py 集成 humanize ← 依赖 humanize.py
7. core/batch.py 集成 output + proxy + stagger ← 依赖 output.py + proxy.py
8. wizard.py 新增配置项 ← 依赖 config/model.py 新字段
9. core/register.py 平台指纹扩展 ← 依赖 http.py 新函数
```

**推荐分阶段构建：**

| 阶段 | 内容 | 原因 |
| ------ | ------ | ------ |
| Phase 1 | config/model.py 字段 + core/humanize.py + adapters 集成 | 最独立、最低风险，可立即验证 |
| Phase 2 | core/output.py + batch.py 批次目录集成 | 依赖 Phase 1 的配置字段 |
| Phase 3 | core/proxy.py + batch.py 代理池集成 | 依赖 Phase 1 的配置字段，与 Phase 2 可并行 |
| Phase 4 | core/http.py + register.py 反检测加固 + stagger | 独立于前三项，但建议最后做以便集成测试 |
| Phase 5 | wizard.py 向导更新 | 所有配置字段就绪后统一更新向导 |

**阶段排序理由：**
- Phase 1 先行因为邮箱拟人化是最高价值且最低风险的改动
- Phase 2 和 Phase 3 可并行，互不依赖
- Phase 4 放在后面因为涉及随机分布调参，需要实际运行验证效果
- Phase 5 最后因为它是所有新配置字段的 UI 暴露层，等字段稳定后再做

## 可扩展性考量

| 场景 | 当前设计 | 扩展方式 |
| ------ | ---------- | ---------- |
| 新增拟人化策略 | `generate_humanized_local(style=...)` | 在 humanize.py 添加新 style，如 `style="pinyin"` |
| 代理健康检查 | ProxyPool 无状态分配 | 未来可加 `mark_failed(proxy)` 方法跳过故障代理 |
| 输出格式扩展 | 纯文本 + JSON | ResolvedPaths 可加 csv_file 等字段 |
| 代理来源扩展 | 配置文件 + 内联 | parse_proxy_list 支持 `@file` 和 `http://api` 前缀 |
| 更多邮箱适配器 | build_email_adapter 工厂 | 新增适配器实现 EmailAdapter 基类，无需改调用方 |

## 来源

- 所有分析基于对项目完整代码的逐文件阅读（HIGH 置信度）
- 架构建议基于现有代码风格和 PROJECT.md 中记录的设计决策
- 无需外部文档验证，因为这是对已有内部代码的架构集成分析

---
*反风控增强 v1.1 架构集成分析*
*研究日期: 2026-03-14*
