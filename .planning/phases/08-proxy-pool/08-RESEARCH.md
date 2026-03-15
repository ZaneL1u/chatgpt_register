# Phase 8: 多代理池调度 - Research

**Researched:** 2026-03-15
**Domain:** 多代理并发调度、配置迁移、向导交互
**Confidence:** HIGH

## Summary

Phase 8 需要实现多代理池调度功能：用户可配置多个代理地址（`proxies: list[str]`），并发 worker 启动时按负载均衡策略分配代理并全程绑定，向导支持多行输入和文件导入，旧 `proxy` 单字段自动迁移。

核心技术挑战集中在三个方面：(1) 线程安全的 `ProxyPool` 代理池管理，需要 `threading.Lock` 保护借出/归还逻辑；(2) 配置模型的双字段兼容（`proxy` + `proxies`），需要 Pydantic `model_validator` 实现内存级自动迁移；(3) 向导的多模式代理输入，需基于现有 `questionary` 框架扩展多行文本和文件导入能力。

**Primary recommendation:** 新建独立的 `proxy_pool.py` 模块实现 `ProxyPool` 类，通过 `threading.Lock` + 引用计数实现线程安全的负载均衡分配，在 `batch.py` 的 `_register_one()` 中从池获取代理替代直接读 `config.registration.proxy`。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 采用动态负载均衡：每个 worker 启动时获取当前负载最小的代理
- 不限制同一代理的并发使用数（代理数少于 worker 数时自动复用）
- worker 全程绑定同一代理，中途代理失败不切换，直接报错
- RuntimeDashboard 显示每个 worker 当前绑定的代理 IP，方便观察负载分布
- 统一多行文本输入：支持直接粘贴多行代理地址，空行结束
- 文件路径自动识别：输入内容如果是 `.txt` 文件路径则自动读取文件内容
- 输入后显示解析摘要确认：「解析到 3 个 SOCKS5 + 1 个 HTTP 代理」
- 单/多自动切换：单个代理直接走单行输入（与现有体验一致），多个代理使用多行输入界面
- 双字段兼容：配置模型同时保留 `proxy`（单个，向下兼容）和 `proxies`（列表，新功能）
- `proxies` 优先：当 `proxies` 非空时使用 `proxies`，否则回退到 `proxy` 单字段
- 内存转换不写回：加载旧 profile 时在内存中将 `proxy` 转换为 `proxies` 列表，不修改原始 TOML 文件
- 日志提示：迁移时打印一行提示「已将 proxy 单字段自动转换为 proxies 列表」
- 新字段命名为 `proxies`，类型 `list[str]`，默认空列表
- 双模式向导：提供「直接输入完整地址」和「分步填写」（先选协议、再填 host:port、可选认证）两种模式
- 智能解析：支持 `socks5://user:pass@host:port`、`http://host:port`、`host:port`（默认 http）等格式
- 格式错误处理：警告并跳过无效行，继续使用其余合法代理

### Claude's Discretion
- 代理可用性校验的具体实现方式（是否启动前 TCP 连通测试）
- ProxyPool 类的内部数据结构和线程安全实现
- 解析摘要的具体展示格式
- 分步填写模式的具体交互步骤

### Deferred Ideas (OUT OF SCOPE)
None — 讨论保持在 phase 范围内
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROXY-01 | 用户能在配置中指定多个代理地址（新增 `proxies: list[str]` 字段） | RegConfig 扩展 + Pydantic model_validator 双字段兼容 |
| PROXY-02 | `proxies` 字段支持 SOCKS5、SOCKS4、HTTP 混合格式 | proxy_parser 模块：URL 解析 + 协议识别 + 格式校验 |
| PROXY-03 | 系统以 round-robin 策略将代理分配给并发 worker | ProxyPool 类：threading.Lock + 引用计数负载均衡 |
| PROXY-04 | 同一 worker 在整个注册任务周期内绑定同一代理 | ProxyPool.acquire() 返回后 worker 全程持有，不调用 release 直到任务结束 |
| PROXY-05 | 旧 `proxy` 单字段 profile 能自动迁移到新 `proxies` 列表 | RegConfig model_validator：proxy 非空且 proxies 为空时自动填充 |
| PROXY-06 | 向导支持多代理输入（逐行输入 / 从文件导入 / 单代理向下兼容） | wizard.py 改造：questionary 多模式输入 + 文件路径检测 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | v2 (already in project) | 配置模型 + 校验 | 项目已有 BaseModel、field_validator、model_validator 模式 |
| threading | stdlib | 线程安全锁 | 项目已使用 threading.Lock 保护 print/file/log |
| questionary | (already in project) | 交互式向导 | 项目已有完整向导框架 |
| rich | (already in project) | Dashboard 展示 | 项目已有 RuntimeDashboard |
| urllib.parse | stdlib | URL 解析 | 解析代理地址的 scheme/host/port/auth |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tomli_w | (already in project) | TOML 写入 | ProfileManager.save() 序列化新字段 |
| re | stdlib | 正则校验 | 代理地址格式验证 |
| pathlib | stdlib | 文件路径处理 | 文件导入功能 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 自建 ProxyPool | 第三方代理池库 | 项目需求简单（负载均衡+绑定），第三方库过度复杂 |
| threading.Lock | asyncio.Lock | 项目使用 ThreadPoolExecutor 同步模型，不适合 asyncio |

## Architecture Patterns

### 推荐模块结构
```
chatgpt_register/
├── config/
│   └── model.py          # RegConfig 扩展 proxies 字段 + model_validator
├── core/
│   ├── proxy_pool.py     # 新增：ProxyPool 类
│   ├── proxy_parser.py   # 新增：代理地址解析和校验
│   └── batch.py          # 修改：注入 ProxyPool，_register_one 从池获取代理
├── wizard.py             # 修改：多代理输入模式
└── dashboard.py          # 修改：增加代理列
```

### Pattern 1: ProxyPool 负载均衡分配
**What:** 使用引用计数实现动态负载均衡，每个代理维护当前活跃 worker 数
**When to use:** worker 启动时调用 `acquire()` 获取负载最小的代理
**Example:**
```python
import threading

class ProxyPool:
    def __init__(self, proxies: list[str]):
        self._lock = threading.Lock()
        # 每个代理的活跃引用计数
        self._usage: dict[str, int] = {p: 0 for p in proxies}

    def acquire(self) -> str:
        """获取当前负载最小的代理，线程安全。"""
        with self._lock:
            proxy = min(self._usage, key=self._usage.get)
            self._usage[proxy] += 1
            return proxy

    def release(self, proxy: str) -> None:
        """释放代理（worker 任务结束后调用）。"""
        with self._lock:
            if proxy in self._usage:
                self._usage[proxy] = max(0, self._usage[proxy] - 1)

    @property
    def snapshot(self) -> dict[str, int]:
        """Dashboard 展示用：返回当前各代理负载快照。"""
        with self._lock:
            return dict(self._usage)
```

### Pattern 2: Pydantic 双字段兼容迁移
**What:** 使用 `model_validator(mode="after")` 实现 `proxy` -> `proxies` 内存级迁移
**When to use:** 加载旧 profile 时自动转换
**Example:**
```python
class RegConfig(BaseModel):
    proxy: str = ""
    proxies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def migrate_proxy_to_proxies(self) -> RegConfig:
        if self.proxy and not self.proxies:
            self.proxies = [self.proxy]
            # 日志提示在调用方打印，model 层不引入 print
        return self
```

### Pattern 3: 代理地址解析
**What:** 支持多种代理 URL 格式的智能解析和标准化
**When to use:** 向导输入和配置加载时
**Example:**
```python
import re
from urllib.parse import urlparse

SUPPORTED_SCHEMES = {"http", "https", "socks4", "socks5"}

def parse_proxy(raw: str) -> str | None:
    """解析并标准化代理地址，无效返回 None。"""
    raw = raw.strip()
    if not raw:
        return None
    # 无 scheme 时默认 http
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urlparse(raw)
    if parsed.scheme not in SUPPORTED_SCHEMES:
        return None
    if not parsed.hostname:
        return None
    return raw
```

### Anti-Patterns to Avoid
- **在 model 层打印日志：** Pydantic model 不应有副作用，迁移提示应由调用方（batch.py 或 CLI）打印
- **修改原始 TOML 文件：** 内存迁移不写回，避免用户 profile 被意外修改
- **全局 ProxyPool 单例：** 应通过参数注入到 `run_batch()`，避免测试困难
- **代理切换：** worker 获取代理后全程绑定，异常不触发重新分配

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL 解析 | 自写正则 | `urllib.parse.urlparse` | 处理 auth、port、特殊字符等边界情况 |
| TOML 序列化 | 手动字符串拼接 | `tomli_w.dump()` | 已有 ProfileManager 完整管道 |
| 线程同步 | busy-wait / 自旋锁 | `threading.Lock` | stdlib 提供的互斥锁足够高效 |

## Common Pitfalls

### Pitfall 1: 代理认证信息中的特殊字符
**What goes wrong:** `socks5://user:p@ss@host:1080` 中 `@` 导致解析错误
**Why it happens:** `urlparse` 按最后一个 `@` 分割 userinfo 和 host
**How to avoid:** 认证信息中的特殊字符需要 URL-encode；向导分步填写模式可避免用户手动处理
**Warning signs:** 代理连接失败但地址看起来正确

### Pitfall 2: ProxyPool 线程安全中的异常退出
**What goes wrong:** worker 异常退出时未调用 `release()`，导致计数泄漏
**Why it happens:** `_register_one()` 的 finally 块未包含 proxy release
**How to avoid:** 在 `_register_one()` 的 finally 块中始终调用 `pool.release(proxy)`
**Warning signs:** 长时间运行后某些代理的引用计数持续增长

### Pitfall 3: 空 proxies 列表
**What goes wrong:** 用户配置了 `proxies = []` 但未设 `proxy`，ProxyPool 初始化报错
**Why it happens:** 没有处理"无代理"的边缘情况
**How to avoid:** `proxies` 为空且 `proxy` 也为空时，跳过 ProxyPool 创建，走原有的无代理逻辑
**Warning signs:** 最简配置（无代理）运行失败

### Pitfall 4: questionary 多行输入的终止信号
**What goes wrong:** 用户不知道如何结束多行输入
**Why it happens:** `questionary` 没有原生多行输入支持
**How to avoid:** 使用循环 + 空行终止，提示文案明确说明「输入空行结束」；或改用 `questionary.text` 循环采集
**Warning signs:** 用户卡在输入界面无法继续

### Pitfall 5: TOML 序列化 list[str] 字段
**What goes wrong:** `proxies` 列表保存到 TOML 后格式不正确
**Why it happens:** `tomli_w` 默认行为可能将列表序列化为多行格式
**How to avoid:** `tomli_w.dump()` 已能正确处理 `list[str]`，无需特殊处理。ProfileManager 已有完整管道
**Warning signs:** 保存后重新加载失败

## Code Examples

### 代理池集成到 batch.py
```python
# batch.py — run_batch() 中创建 ProxyPool
from chatgpt_register.core.proxy_pool import ProxyPool

def run_batch(config: RegisterConfig):
    # ... 现有初始化代码 ...

    # 构建代理池
    effective_proxies = config.registration.proxies
    pool = ProxyPool(effective_proxies) if effective_proxies else None

    # ... ThreadPoolExecutor 中 ...
    future = executor.submit(
        _register_one, idx, total_accounts, config,
        output_file, _print_lock, _file_lock, dashboard,
        proxy_pool=pool,  # 新增参数
    )

def _register_one(idx, total, config, output_file, print_lock, file_lock,
                   dashboard=None, proxy_pool=None):
    proxy = None
    try:
        # 从池获取代理（如果有池）
        if proxy_pool is not None:
            proxy = proxy_pool.acquire()
        else:
            proxy = config.registration.proxy or None

        reg = ChatGPTRegister(
            config=config,
            proxy=proxy,
            # ... 其他参数 ...
        )
        # ... 注册逻辑 ...
    finally:
        if proxy_pool is not None and proxy is not None:
            proxy_pool.release(proxy)
```

### 向导多代理输入
```python
# wizard.py — _ask_registration_config 中
def _ask_proxies() -> list[str]:
    """多模式代理输入。"""
    mode = questionary.select(
        "代理配置方式",
        choices=[
            "单个代理 (直接输入)",
            "多个代理 (逐行输入)",
            "从文件导入 (.txt)",
            "跳过 (不使用代理)",
        ],
    ).ask()

    if mode is None or "跳过" in mode:
        return []

    if "单个" in mode:
        addr = questionary.text("代理地址").ask()
        parsed = parse_proxy(addr)
        return [parsed] if parsed else []

    if "文件" in mode:
        path = questionary.text("代理列表文件路径").ask()
        return _load_proxies_from_file(path)

    # 多行输入
    proxies = []
    print("逐行输入代理地址，空行结束：")
    while True:
        line = questionary.text("", default="").ask()
        if not line or not line.strip():
            break
        parsed = parse_proxy(line)
        if parsed:
            proxies.append(parsed)
        else:
            print(f"  ⚠ 跳过无效地址: {line}")
    return proxies
```

### Dashboard 代理列扩展
```python
# dashboard.py — register_worker 和 _build_workers_panel 中
def register_worker(self, worker_id: int, tag: str = "", proxy: str = ""):
    # 现有逻辑 + 新增 proxy 字段
    item["proxy"] = _truncate_proxy(proxy)  # 脱敏截断

def _truncate_proxy(proxy: str, max_len: int = 25) -> str:
    """脱敏截断代理地址用于显示。"""
    if not proxy:
        return "直连"
    # 隐藏认证信息
    from urllib.parse import urlparse
    parsed = urlparse(proxy)
    if parsed.username:
        return f"{parsed.scheme}://***@{parsed.hostname}:{parsed.port}"
    return proxy[:max_len] + ("..." if len(proxy) > max_len else "")
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | pyproject.toml (`[project.optional-dependencies]`) |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROXY-01 | `proxies: list[str]` 字段可配置 | unit | `pytest tests/test_config_model.py::test_proxies_field -x` | ❌ Wave 0 |
| PROXY-02 | 支持 SOCKS5/SOCKS4/HTTP 混合格式 | unit | `pytest tests/test_proxy_parser.py::test_mixed_formats -x` | ❌ Wave 0 |
| PROXY-03 | round-robin / 负载均衡分配 | unit | `pytest tests/test_proxy_pool.py::test_load_balance -x` | ❌ Wave 0 |
| PROXY-04 | worker 全程绑定同一代理 | unit | `pytest tests/test_proxy_pool.py::test_worker_binding -x` | ❌ Wave 0 |
| PROXY-05 | 旧 proxy 字段自动迁移 | unit | `pytest tests/test_config_model.py::test_proxy_migration -x` | ❌ Wave 0 |
| PROXY-06 | 向导多代理输入 | unit | `pytest tests/test_wizard_proxy.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_proxy_parser.py` — 代理地址解析和校验测试（PROXY-02）
- [ ] `tests/test_proxy_pool.py` — ProxyPool 线程安全和负载均衡测试（PROXY-03, PROXY-04）
- [ ] `tests/test_config_model.py::test_proxies_field` — proxies 字段测试（PROXY-01）
- [ ] `tests/test_config_model.py::test_proxy_migration` — 旧字段迁移测试（PROXY-05）
- [ ] `tests/test_wizard_proxy.py` — 向导多代理输入测试（PROXY-06）

## Open Questions

1. **代理可用性校验是否在启动前执行？**
   - What we know: CONTEXT.md 标记为 Claude's Discretion
   - Recommendation: 暂不实现 TCP 连通测试，仅做格式校验。代理连通性由实际注册过程中的错误自然暴露，避免增加启动延迟

2. **questionary 多行输入的最佳实现方式**
   - What we know: questionary 没有原生多行输入 widget
   - Recommendation: 使用循环调用 `questionary.text()` + 空行终止模式，每行即时校验并反馈

## Sources

### Primary (HIGH confidence)
- 项目源码直接审查：`config/model.py`、`core/batch.py`、`wizard.py`、`dashboard.py`、`core/register.py`、`config/profile.py`
- Python stdlib 文档：`threading.Lock`、`urllib.parse`

### Secondary (MEDIUM confidence)
- Pydantic v2 model_validator 模式 — 项目已有成功实践（EmailConfig.check_provider_config）
- questionary 交互模式 — 项目已有完整向导实现

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 全部使用项目已有依赖，无新引入
- Architecture: HIGH - 遵循项目已有模式（Lock + Pydantic + questionary）
- Pitfalls: HIGH - 基于代码审查识别的具体风险点

**Research date:** 2026-03-15
**Valid until:** 2026-04-15（稳定技术栈，30 天有效）
