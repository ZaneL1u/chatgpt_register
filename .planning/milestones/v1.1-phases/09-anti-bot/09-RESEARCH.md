# Phase 9: 反机器人加固 - Research

**Researched:** 2026-03-15
**Domain:** 反机器人检测、浏览器指纹统一、请求时序正态化
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 将 `random_delay()` 从 `random.uniform()` 均匀分布改为 `random.gauss()` 正态分布
- 按场景分三档延迟参数：
  - **普通步骤**（页面跳转、表单提交）：均值 0.5s，标准差 0.15s，下限 clamp 到 0.2s
  - **高延迟场景**（OTP 等待后的操作、重试）：均值 1.5s，标准差 0.4s，下限 clamp 到 0.5s
  - **微延迟**（连续 API 调用之间）：均值 0.3s，标准差 0.1s，下限 clamp 到 0.1s
- 在 `random_delay()` 函数签名中引入 `scenario` 参数或直接传 `(mean, std)` 参数对
- register.py 中约 12 处 `random_delay` 调用需逐一标注所属场景
- `CHROME_PROFILES` 从 4 个扩充到 10 个左右
- 版本范围覆盖近 6-8 个月的 Chrome 稳定版，不低于 Chrome 125
- 每个 profile 需包含准确的 `sec_ch_ua`、`build`、`patch_range`、`impersonate` 值
- `impersonate` 值需与 curl_cffi 实际支持的版本对齐
- 新建 `BrowserProfile` dataclass，包含 `impersonate`、`chrome_major`、`chrome_full`、`user_agent`、`sec_ch_ua` 五个字段
- `random_chrome_version()` 返回 `BrowserProfile` 实例而非裸元组
- `SentinelTokenGenerator` 不再有硬编码默认 UA，构造时必须传入 `user_agent`
- `sentinel.py` 的 `fetch_sentinel_challenge` 和 `build_sentinel_token` 统一从调用方获取浏览器信息
- `run_batch()` 中 worker 逐个提交，每提交一个后随机等待 2-8 秒（正态分布，均值 5s，标准差 1.5s，clamp 到 2-8s）
- 第一个 worker 立即启动，不等待

### Claude's Discretion
- 正态分布参数的具体数值微调
- `BrowserProfile` 放在 `http.py` 还是单独文件
- Chrome 版本数据的具体版本号选择（只要满足 8-12 个、覆盖近半年即可）
- worker 错开延迟的日志格式

### Deferred Ideas (OUT OF SCOPE)
- 无 — 讨论保持在阶段范围内
</user_constraints>

## Summary

Phase 9 是纯内部重构加固，不涉及新功能，不需要外部依赖。所有变更集中在 4 个文件：`core/http.py`（BrowserProfile dataclass + CHROME_PROFILES 扩充 + random_delay 签名改造）、`core/sentinel.py`（移除硬编码 UA 默认值）、`core/register.py`（14 处 random_delay 调用改为场景化参数 + BrowserProfile 解构适配）、`core/batch.py`（worker 错开启动）。

curl_cffi 0.14.0 支持的 Chrome impersonate 值经过实际验证：chrome99, chrome100, chrome101, chrome104, chrome107, chrome110, chrome116, chrome119, chrome120, chrome123, chrome124, chrome131, chrome133a, chrome136, chrome142。按 "不低于 Chrome 125" 的约束，可用值为 chrome131, chrome133a, chrome136, chrome142。由于只有 4 个直接可用的 impersonate 值，需要使用最接近的 impersonate 值来覆盖中间版本（如 Chrome 127 使用 chrome124 的 TLS 指纹 — 但这违反了 >=125 的约束）。实际方案：使用 chrome131, chrome133a, chrome136, chrome142 这 4 个 impersonate 值，通过不同 build/patch 组合创建 10 个 profile 条目，每个 impersonate 值对应 2-3 个不同的 patch 版本。

**Primary recommendation:** 将 BrowserProfile dataclass 放在 `http.py`（与 CHROME_PROFILES 同文件），避免新增文件；每个 impersonate 值创建 2-3 个不同 patch 的 profile 条目以达到 10 个总量。

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| curl_cffi | 0.14.0 | HTTP 请求 + TLS 指纹模拟 | 项目已有，impersonate 参数控制 TLS 指纹 |
| dataclasses (stdlib) | Python 3.10+ | BrowserProfile 数据结构 | 零依赖，项目已广泛使用 dataclass 模式 |
| random (stdlib) | Python 3.10+ | 正态分布 + 随机选择 | random.gauss() 内置，无需额外依赖 |
| time (stdlib) | Python 3.10+ | 延迟控制 | time.sleep() 已在使用 |

### Supporting
无新增依赖。

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dataclass | NamedTuple | NamedTuple 不可变，适合此场景；但 dataclass 更灵活且项目风格一致 |
| random.gauss | numpy.random.normal | 过重依赖，random.gauss 完全满足需求 |

## Architecture Patterns

### 现有代码结构（不变）
```
chatgpt_register/core/
├── http.py          # CHROME_PROFILES + BrowserProfile + random_delay + random_chrome_version
├── sentinel.py      # SentinelTokenGenerator + fetch/build 函数
├── register.py      # ChatGPTRegister（消费 BrowserProfile）
└── batch.py         # run_batch（worker 错开启动）
```

### Pattern 1: BrowserProfile Dataclass
**What:** 统一浏览器指纹数据结构
**When to use:** 所有需要浏览器标识的地方

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BrowserProfile:
    impersonate: str       # curl_cffi impersonate 值，如 "chrome136"
    chrome_major: int      # 主版本号，如 136
    chrome_full: str       # 完整版本，如 "136.0.7103.92"
    user_agent: str        # 完整 UA 字符串
    sec_ch_ua: str         # sec-ch-ua header 值
```

`frozen=True` 确保创建后不可修改，避免意外篡改。

### Pattern 2: 场景化延迟
**What:** random_delay 改为接受 mean/std 参数或 scenario 枚举
**When to use:** 所有请求间延迟

推荐方案 — 直接传 `(mean, std)` 参数对（简单、灵活、无需枚举类）：

```python
def random_delay(mean: float = 0.5, std: float = 0.15, min_bound: float = 0.2) -> None:
    """正态分布延迟，clamp 到 min_bound 下限。"""
    delay = max(min_bound, random.gauss(mean, std))
    time.sleep(delay)
```

调用时按场景传参：
- `random_delay(0.5, 0.15, 0.2)` — 普通步骤
- `random_delay(1.5, 0.4, 0.5)` — 高延迟场景
- `random_delay(0.3, 0.1, 0.1)` — 微延迟

### Pattern 3: Worker 错开启动
**What:** 逐个提交 worker，中间加正态分布延迟
**When to use:** run_batch 中替换 ThreadPoolExecutor 的批量提交

```python
# 替换现有一次性提交所有任务的逻辑
futures = {}
for idx in range(1, total_accounts + 1):
    future = executor.submit(_register_one, ...)
    futures[future] = idx
    if idx < total_accounts:
        # 错开延迟：正态分布，均值 5s，标准差 1.5s，clamp 到 2-8s
        stagger = max(2.0, min(8.0, random.gauss(5.0, 1.5)))
        time.sleep(stagger)
```

注意：第一个 worker 立即启动（循环内 stagger 在 submit 之后），最后一个不需要等待。

### Anti-Patterns to Avoid
- **在 sentinel.py 内部维护默认 UA:** 当前 `SentinelTokenGenerator.__init__` 的 `user_agent` 默认值 `Chrome/145.0.0.0` 与 CHROME_PROFILES 不一致 — 必须移除默认值
- **sentinel.py fetch/build 函数内部的默认 sec_ch_ua:** 当前有 `sec_ch_ua or '"Not:A-Brand"...'` 回退 — 必须要求调用方显式传入
- **使用均匀分布模拟人类行为:** `random.uniform()` 产生的等概率分布与人类操作节奏不符

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 正态分布随机数 | 自定义分布采样 | `random.gauss(mean, std)` | stdlib 实现，数值稳定 |
| TLS 指纹模拟 | 自定义 TLS 握手 | curl_cffi impersonate | 已有完善实现 |

## Common Pitfalls

### Pitfall 1: impersonate 值与版本号不匹配
**What goes wrong:** Chrome profile 的 major 版本号与 impersonate 值不一致，导致 TLS 指纹和 HTTP headers 矛盾
**Why it happens:** Chrome 版本多，容易混淆哪个 impersonate 对应哪个版本
**How to avoid:** 严格使用 curl_cffi 支持的 impersonate 值（chrome131, chrome133a, chrome136, chrome142），每个 profile 的 major 必须与 impersonate 中的数字一致
**Warning signs:** 注册失败率突然升高

### Pitfall 2: gauss() 返回负值
**What goes wrong:** `random.gauss(0.3, 0.1)` 有小概率返回负数，导致 `time.sleep()` 抛出 ValueError
**Why it happens:** 正态分布理论上无界
**How to avoid:** 始终 `max(min_bound, random.gauss(mean, std))` clamp
**Warning signs:** 偶发的 `ValueError: sleep length must be non-negative`

### Pitfall 3: worker 错开与 ThreadPoolExecutor 语义冲突
**What goes wrong:** ThreadPoolExecutor 的 max_workers 限制了并行线程数，但提交顺序和实际启动时间由线程池控制
**Why it happens:** executor.submit() 只是排队，不保证立即启动
**How to avoid:** 在主线程中 sleep 错开，确保 submit 间隔够大；如果 total_accounts > max_workers，后续任务自动排队等待空闲线程
**Warning signs:** 日志中多个 worker 启动时间相同

### Pitfall 4: sec_ch_ua 格式变化
**What goes wrong:** 不同 Chrome 版本的 sec_ch_ua 中 brand 排列顺序和 "Not_A Brand" 的格式不同
**Why it happens:** Google 故意在每个版本改变 GREASE brand 的格式来检测伪造
**How to avoid:** 每个版本的 sec_ch_ua 必须从真实 Chrome 浏览器中提取，不要猜测格式
**Warning signs:** 403 或 challenge 升级

### Pitfall 5: BrowserProfile 解构兼容性
**What goes wrong:** 将 `random_chrome_version()` 返回值从元组改为 dataclass 后，所有解构赋值 `a, b, c, d, e = random_chrome_version()` 都需要改
**Why it happens:** dataclass 默认不支持 iterable unpacking
**How to avoid:** 要么让所有调用方改用属性访问 `profile.impersonate`，要么给 BrowserProfile 加 `__iter__` 方法保持向后兼容。推荐前者（更清晰）。
**Warning signs:** `TypeError: cannot unpack non-iterable BrowserProfile object`

## Code Examples

### BrowserProfile 定义与 CHROME_PROFILES 扩充
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BrowserProfile:
    impersonate: str
    chrome_major: int
    chrome_full: str
    user_agent: str
    sec_ch_ua: str

CHROME_PROFILES = [
    # chrome131 系列（2 个 profile）
    {"major": 131, "impersonate": "chrome131", "build": 6778, "patch_range": (69, 205),
     "sec_ch_ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"'},
    {"major": 131, "impersonate": "chrome131", "build": 6778, "patch_range": (206, 350),
     "sec_ch_ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"'},
    # chrome133a 系列（3 个 profile）
    {"major": 133, "impersonate": "chrome133a", "build": 6943, "patch_range": (33, 100),
     "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"'},
    {"major": 133, "impersonate": "chrome133a", "build": 6943, "patch_range": (101, 200),
     "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"'},
    {"major": 133, "impersonate": "chrome133a", "build": 6943, "patch_range": (201, 300),
     "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"'},
    # chrome136 系列（3 个 profile）
    {"major": 136, "impersonate": "chrome136", "build": 7103, "patch_range": (48, 100),
     "sec_ch_ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"'},
    {"major": 136, "impersonate": "chrome136", "build": 7103, "patch_range": (101, 175),
     "sec_ch_ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"'},
    {"major": 136, "impersonate": "chrome136", "build": 7103, "patch_range": (176, 250),
     "sec_ch_ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"'},
    # chrome142 系列（2 个 profile）
    {"major": 142, "impersonate": "chrome142", "build": 7540, "patch_range": (30, 90),
     "sec_ch_ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"'},
    {"major": 142, "impersonate": "chrome142", "build": 7540, "patch_range": (91, 150),
     "sec_ch_ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"'},
]
```

注意：上述 10 个 profile 使用了不同的 patch_range 分段来创建多样性，同一 impersonate 值的 TLS 指纹相同但 UA 中的版本号不同。

### random_chrome_version 改造
```python
def random_chrome_version() -> BrowserProfile:
    profile = random.choice(CHROME_PROFILES)
    major = profile["major"]
    build = profile["build"]
    patch = random.randint(*profile["patch_range"])
    full_ver = f"{major}.0.{build}.{patch}"
    ua = (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{full_ver} Safari/537.36"
    )
    return BrowserProfile(
        impersonate=profile["impersonate"],
        chrome_major=major,
        chrome_full=full_ver,
        user_agent=ua,
        sec_ch_ua=profile["sec_ch_ua"],
    )
```

### register.py 中消费 BrowserProfile
```python
# 改前
self.impersonate, self.chrome_major, self.chrome_full, self.ua, self.sec_ch_ua = random_chrome_version()

# 改后
bp = random_chrome_version()
self.impersonate = bp.impersonate
self.chrome_major = bp.chrome_major
self.chrome_full = bp.chrome_full
self.ua = bp.user_agent
self.sec_ch_ua = bp.sec_ch_ua
```

### sentinel.py 移除默认 UA
```python
# 改前
def __init__(self, device_id=None, user_agent=None):
    self.user_agent = user_agent or (
        "Mozilla/5.0 ... Chrome/145.0.0.0 ..."
    )

# 改后
def __init__(self, device_id=None, user_agent=None):
    if user_agent is None:
        raise ValueError("user_agent is required — use BrowserProfile.user_agent")
    self.device_id = device_id or str(uuid.uuid4())
    self.user_agent = user_agent
```

### random_delay 调用场景分类

register.py 中 14 处 `random_delay` 调用的场景分类：

| 行号 | 当前参数 | 场景 | 建议参数 (mean, std, min) |
|------|---------|------|--------------------------|
| 287 | (0.3, 0.8) | 普通步骤（CSRF 后） | (0.5, 0.15, 0.2) |
| 289 | (0.2, 0.5) | 微延迟（连续 API） | (0.3, 0.1, 0.1) |
| 291 | (0.3, 0.8) | 普通步骤 | (0.5, 0.15, 0.2) |
| 295 | (0.3, 0.8) | 普通步骤 | (0.5, 0.15, 0.2) |
| 303 | (0.5, 1.0) | 普通步骤（表单提交后） | (0.5, 0.15, 0.2) |
| 307 | (0.3, 0.8) | 普通步骤 | (0.5, 0.15, 0.2) |
| 315 | (0.5, 1.0) | 普通步骤 | (0.5, 0.15, 0.2) |
| 317 | (0.3, 0.5) | 微延迟 | (0.3, 0.1, 0.1) |
| 334 | (0.3, 0.8) | 普通步骤 | (0.5, 0.15, 0.2) |
| 339 | (1.0, 2.0) | 高延迟（OTP 等待/重试） | (1.5, 0.4, 0.5) |
| 343 | (0.3, 0.8) | 普通步骤 | (0.5, 0.15, 0.2) |
| 348 | (0.5, 1.5) | 高延迟（验证后） | (1.5, 0.4, 0.5) |
| 352 | (0.2, 0.5) | 微延迟 | (0.3, 0.1, 0.1) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 均匀分布延迟 | 正态/对数正态分布 | 2024+ | 更接近人类行为模式 |
| 单一 Chrome 版本 | 多版本指纹池 | 2024+ | 降低指纹聚集特征 |
| 并发同步启动 | 错开启动 | 2024+ | 避免时序关联检测 |

## Open Questions

1. **Chrome 版本 patch_range 的真实范围**
   - What we know: 每个 major 版本有几十到几百个 patch 发布
   - What's unclear: 具体哪些 patch 在用户中广泛使用
   - Recommendation: 使用宽范围即可，不影响 TLS 指纹（impersonate 按 major 版本）

2. **sentinel.py SDK URL 版本 `20260124ceb8`**
   - What we know: STATE.md 中标记为需确认的 concern
   - What's unclear: 该 SDK 版本是否仍有效
   - Recommendation: 本阶段不动 SDK URL（超出反机器人加固范围），如果失效会表现为 sentinel challenge 请求失败，可在后续阶段处理

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ |
| Config file | pyproject.toml [tool.pytest] |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANTI-01 | SentinelTokenGenerator 不再使用硬编码默认 UA | unit | `uv run pytest tests/test_anti_bot.py::test_sentinel_no_default_ua -x` | ❌ Wave 0 |
| ANTI-02 | BrowserProfile 统一数据源 | unit | `uv run pytest tests/test_anti_bot.py::test_browser_profile_dataclass -x` | ❌ Wave 0 |
| ANTI-03 | CHROME_PROFILES 含 8-12 个版本 | unit | `uv run pytest tests/test_anti_bot.py::test_chrome_profiles_count -x` | ❌ Wave 0 |
| ANTI-04 | 延迟使用正态分布 | unit | `uv run pytest tests/test_anti_bot.py::test_random_delay_gaussian -x` | ❌ Wave 0 |
| ANTI-05 | Worker 启动错开 2-8s | unit | `uv run pytest tests/test_anti_bot.py::test_worker_stagger_delay -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before verify

### Wave 0 Gaps
- [ ] `tests/test_anti_bot.py` — covers ANTI-01 through ANTI-05
- [ ] 无需新增框架或 conftest — 现有 pytest 基础设施完备

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANTI-01 | 修复 SentinelTokenGenerator 默认 UA Chrome/145.0.0.0 | sentinel.py 分析：__init__ 中硬编码默认值，改为 required 参数 |
| ANTI-02 | 统一 BrowserProfile 数据类 | BrowserProfile dataclass 设计，random_chrome_version 返回值改造 |
| ANTI-03 | CHROME_PROFILES 扩充到 8-12 个 | curl_cffi 0.14.0 impersonate 值验证，10 profile 方案 |
| ANTI-04 | 延迟改为场景化正态分布 | random_delay 签名改造，14 处调用点场景分类表 |
| ANTI-05 | Worker 启动错开 2-8s | batch.py ThreadPoolExecutor 提交逻辑改造方案 |
</phase_requirements>

## Sources

### Primary (HIGH confidence)
- 项目源码直接分析：`core/http.py`, `core/sentinel.py`, `core/register.py`, `core/batch.py`
- curl_cffi 0.14.0 BrowserType 枚举（实际 Python 运行验证支持的 impersonate 值）

### Secondary (MEDIUM confidence)
- Chrome 版本 sec_ch_ua 格式 — 现有 CHROME_PROFILES 中的值来自真实浏览器

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 纯 stdlib + 已有依赖
- Architecture: HIGH - 改造现有代码，无新架构引入
- Pitfalls: HIGH - 基于代码分析的具体风险点

**Research date:** 2026-03-15
**Valid until:** 2026-04-15（稳定，无外部依赖变化风险）
