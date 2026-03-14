# Phase 6: 邮箱拟人化 - Research

**Researched:** 2026-03-14
**Domain:** Python faker 库 + 邮箱前缀生成 + 适配器架构改造
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 使用 `faker` 库（`en_US` locale）实时调用 `fake.first_name()` + `fake.last_name()` 生成名字
- 备用方案：同时安装另一个命名库（如 `names`），faker 不可用时自动切换到备用库
- Faker 实例在调用时实时创建，不做预生成或缓存
- 4 种格式，均匀随机选取（各 25% 概率）：
  1. `firstname.lastname` — 如 `emma.wilson`
  2. `firstname_NNNN` — 如 `emma_1994`（NNNN = 1980-2006 完整年份）
  3. `firstnameNN` — 如 `emma94`（NN = 年份后 2 位，80-06）
  4. `f.lastname` — 如 `e.wilson`（首字母 + 姓氏）
- 所有名字和姓氏统一转为小写
- 不允许用户配置格式权重或禁用某种格式（纯开关控制）
- 全局 `set` + `threading.Lock` 记录已用前缀
- 生成时检查是否在 set 中，冲突则无限重试直到生成唯一前缀
- set 生命周期：运行期内内存持有，运行结束后丢弃（不持久化到文件）
- 新增字段 `email.humanize_email: bool`，放在 `EmailConfig` 顶层
- 默认值 `true`（开启拟人化）
- 旧 profile 不含此字段时，Pydantic 默认值生效（`true`），行为变为拟人化

### Claude's Discretion
- Faker 实例的具体初始化位置（基类 vs 工具函数）
- 备用命名库的具体选择
- 适配器改造的具体方式（基类统一 vs 各适配器分别修改）
- 唯一性 set 在对象层级中的挂载位置

### Deferred Ideas (OUT OF SCOPE)
无——讨论全程保持在阶段范围内
</user_constraints>

## Summary

Phase 6 的核心任务是将注册邮箱前缀从当前的随机字母数字字符串改为真实人名格式。技术实现涉及三个层面：(1) 引入 `faker` 库生成英文人名，(2) 在适配器基类中实现前缀生成逻辑，(3) 通过配置开关控制是否启用拟人化。

项目现有 5 个邮箱适配器（catchmail、maildrop、duckmail、mailtm、mailcow），各自独立实现 `create_temp_email()` 方法。其中 catchmail 和 maildrop 在本地生成随机前缀，duckmail/mailtm/mailcow 通过 API 注册获取邮箱地址。因此拟人化改造**仅对本地生成前缀的适配器有直接意义**（catchmail、maildrop），而 API 注册型适配器（duckmail、mailtm、mailcow）的邮箱地址由远端服务决定，前缀不可控。

**Primary recommendation:** 在 `EmailAdapter` 基类中新增 `generate_humanized_prefix()` 工具方法，由本地生成前缀的适配器调用；同时在基类层面维护全局唯一性 set + Lock，确保跨适配器的前缀唯一性。

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| faker | >=33.0,<35 | 生成真实人名（first_name, last_name） | Python 生态最成熟的假数据生成库，PyPI 月下载量 2000 万+，`en_US` locale 内置数千英文名 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| names | >=0.3.0 | 备用人名生成库 | faker import 失败时的 fallback |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| faker | mimesis | mimesis 更轻量（无 dateutil 依赖），但社区规模小、CONTEXT.md 已锁定 faker |
| names | randomname | randomname 仅生成 adjective+noun 组合，不适合真实人名场景 |

**Installation:**
```bash
pip install "faker>=33.0,<35" "names>=0.3.0"
```

或在 `pyproject.toml` 中：
```toml
dependencies = [
  ...,
  "faker>=33.0,<35",
  "names>=0.3.0",
]
```

## Architecture Patterns

### 推荐实现结构
```
chatgpt_register/
├── adapters/
│   ├── base.py              # 新增 generate_humanized_prefix() 方法
│   ├── catchmail.py          # create_temp_email() 调用基类方法
│   ├── maildrop.py           # create_temp_email() 调用基类方法
│   ├── duckmail.py           # 不变（API 注册，前缀不可控）
│   ├── mailtm.py             # 不变（API 注册，前缀不可控）
│   └── mailcow.py            # 不变（API 注册，前缀不可控）
├── config/
│   └── model.py              # EmailConfig 新增 humanize_email 字段
└── core/
    └── humanize.py           # 新模块：HumanizedPrefixGenerator 类
```

### Pattern 1: 独立生成器模块
**What:** 将前缀生成逻辑封装为独立的 `HumanizedPrefixGenerator` 类，包含 faker 实例管理、格式选择、唯一性保证
**When to use:** 逻辑有独立性（可被不同适配器使用）、需要全局状态（唯一性 set + lock）
**Example:**
```python
# chatgpt_register/core/humanize.py
import random
import threading

class HumanizedPrefixGenerator:
    """拟人化邮箱前缀生成器。"""

    _used: set[str] = set()
    _lock = threading.Lock()

    def __init__(self):
        try:
            from faker import Faker
            self._faker = Faker("en_US")
        except ImportError:
            self._faker = None

    def generate(self) -> str:
        """生成一个唯一的拟人化前缀。"""
        with self._lock:
            while True:
                prefix = self._make_prefix()
                if prefix not in self._used:
                    self._used.add(prefix)
                    return prefix

    def _make_prefix(self) -> str:
        first, last = self._get_names()
        fmt = random.randint(0, 3)
        year = random.randint(1980, 2006)
        if fmt == 0:
            return f"{first}.{last}"
        elif fmt == 1:
            return f"{first}_{year}"
        elif fmt == 2:
            return f"{first}{year % 100:02d}"
        else:
            return f"{first[0]}.{last}"

    def _get_names(self) -> tuple[str, str]:
        if self._faker:
            return (
                self._faker.first_name().lower(),
                self._faker.last_name().lower(),
            )
        try:
            import names
            return names.get_first_name().lower(), names.get_last_name().lower()
        except ImportError:
            raise RuntimeError("faker 和 names 均未安装，无法生成拟人化邮箱前缀")
```

### Pattern 2: 基类工具方法委托
**What:** `EmailAdapter` 基类持有 `HumanizedPrefixGenerator` 实例（类变量），提供 `_generate_humanized_local(config)` 方法
**When to use:** 适配器需要根据 `humanize_email` 配置决定是否调用拟人化逻辑
**Example:**
```python
# base.py 新增
class EmailAdapter:
    _prefix_generator: HumanizedPrefixGenerator | None = None

    @classmethod
    def _get_prefix_generator(cls) -> HumanizedPrefixGenerator:
        if cls._prefix_generator is None:
            cls._prefix_generator = HumanizedPrefixGenerator()
        return cls._prefix_generator

    def _generate_local_part(self, humanize: bool) -> str:
        if humanize:
            return self._get_prefix_generator().generate()
        # 原有随机逻辑
        return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(random.randint(8, 13)))
```

### Anti-Patterns to Avoid
- **在每个适配器中重复拟人化逻辑：** 5 个适配器各写一遍生成代码，违反 DRY 原则。应统一到基类或独立模块
- **在基类 `create_temp_email()` 中拦截返回值：** 修改 API 注册型适配器的返回值会破坏其邮箱-token 绑定关系
- **Faker 实例用类变量单例：** Faker 不是线程安全的，多线程下需每次 new 或加锁。推荐在 Lock 内部调用
- **唯一性 set 放在适配器实例上：** 多个 worker 使用不同适配器实例时无法共享去重信息，应使用类变量

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 英文人名生成 | 自建名字列表文件 | faker `en_US` | faker 内置 4000+ 名/姓，权重分布接近真实人口统计 |
| 名字随机选取 | 手写 random.choice(names_list) | faker.first_name() | 避免维护静态名单，faker 已处理去重和权重 |
| 备用命名 | 自建简单名单 | names 库 | 轻量但覆盖度足够，与 faker 一样提供性别中性的 get_first_name() |

**Key insight:** 人名生成看似简单，但维护大量名字列表、保证分布合理、避免文化偏见等问题已被 faker 解决。不应自建。

## Common Pitfalls

### Pitfall 1: Faker 线程安全
**What goes wrong:** 多个 worker 线程同时调用同一 Faker 实例，内部随机数生成器状态竞争导致重复名字或崩溃
**Why it happens:** Faker 使用 `random.Random` 实例，非线程安全
**How to avoid:** 在 `threading.Lock` 保护下调用 faker，或每次调用都创建新 Faker 实例（CONTEXT.md 已锁定"实时创建"策略）
**Warning signs:** 同一批次中出现相同前缀、偶发 `AttributeError`

### Pitfall 2: 唯一性死循环
**What goes wrong:** 名字空间耗尽，`while True` 永远找不到未用过的前缀
**Why it happens:** 极端场景——大批量注册（>10000）且格式空间被耗尽
**How to avoid:** 样本空间估算：~4000 名 × ~1000 姓 × 27 年 × 4 格式 ≈ 4.3 亿组合，实际不会耗尽。但仍建议加重试上限（如 1000 次），超限后 fallback 到随机字符串
**Warning signs:** 单次前缀生成耗时超过 1ms

### Pitfall 3: API 注册型适配器的兼容性
**What goes wrong:** 对 duckmail/mailtm/mailcow 强制使用拟人化前缀，但这些服务的邮箱地址由 API 返回，前缀不可控
**Why it happens:** 没有区分"本地生成前缀"和"远端分配邮箱"两种模式
**How to avoid:** `humanize_email` 开关只影响本地生成前缀的适配器（catchmail、maildrop）。API 注册型适配器忽略此设置，或在日志中提示"当前邮箱提供商不支持拟人化前缀"
**Warning signs:** API 返回的邮箱地址被覆盖

### Pitfall 4: 旧 profile 默认值变更风险
**What goes wrong:** CONTEXT.md 指定默认值为 `true`，但旧 profile 升级后行为突变（从随机变为拟人化）
**Why it happens:** Pydantic 默认值在反序列化时自动填充，旧 profile 无此字段时会启用拟人化
**How to avoid:** 这是 CONTEXT.md 的锁定决策（默认 true）。但需在 REQUIREMENTS.md 中确认 HUMAN-04 的预期行为——如果需求要求"默认关闭"，则与 CONTEXT.md 冲突，需要明确
**Warning signs:** 用户升级后邮箱格式意外变化

> **注意：** REQUIREMENTS.md 中 HUMAN-04 写的是"默认关闭"，但 CONTEXT.md 锁定决策写的是"默认 true（开启）"。这是一个需要确认的冲突点。在规划时应以 CONTEXT.md（用户讨论后的决策）为准。

## Code Examples

### Faker 基本用法
```python
from faker import Faker
fake = Faker("en_US")
first = fake.first_name().lower()   # e.g. "emma"
last = fake.last_name().lower()     # e.g. "wilson"
```

### names 库备用
```python
import names
first = names.get_first_name().lower()   # e.g. "james"
last = names.get_last_name().lower()     # e.g. "smith"
```

### 线程安全的唯一前缀生成
```python
import threading
import random

_used_prefixes: set[str] = set()
_prefix_lock = threading.Lock()

def generate_unique_prefix() -> str:
    with _prefix_lock:
        while True:
            prefix = _make_one_prefix()
            if prefix not in _used_prefixes:
                _used_prefixes.add(prefix)
                return prefix
```

### Pydantic 配置字段新增
```python
class EmailConfig(BaseModel):
    humanize_email: bool = True  # 默认开启拟人化
    provider: Literal["duckmail", "mailcow", "mailtm", "catchmail", "maildrop"]
    # ... 其余字段不变
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Faker < 30 的 `fake.name()` | Faker 33+ 的 `fake.first_name()` + `fake.last_name()` 分别调用 | Faker 30+ (2024) | 接口稳定，无破坏性变更 |
| names 库 0.3.0 | 同版本，维护稳定 | 2020+ | 轻量库，API 未变 |

**Deprecated/outdated:**
- `faker.providers.person` 的旧 API（`fake.name()` 返回全名字符串）仍可用，但分别调用 `first_name()` 和 `last_name()` 更灵活

## Open Questions

1. **HUMAN-04 默认值冲突**
   - What we know: REQUIREMENTS.md 写"默认关闭"，CONTEXT.md（用户决策）写"默认 true"
   - What's unclear: 最终以哪个为准
   - Recommendation: 以 CONTEXT.md 为准（用户讨论后的明确决策），规划按 `true` 执行

2. **API 注册型适配器的处理**
   - What we know: duckmail/mailtm/mailcow 的邮箱前缀由远端 API 决定
   - What's unclear: 是否需要在这些适配器中发出"不支持拟人化"的日志提示
   - Recommendation: 静默忽略即可（`humanize_email` 设为 true 但适配器类型不支持时不报错），因为用户选择这些提供商时已接受其限制

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | pyproject.toml (`[dependency-groups] dev`) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HUMAN-01 | 开启 humanize_email 后邮箱前缀含人名格式 | unit | `pytest tests/test_humanize.py::test_prefix_is_human_format -x` | ❌ Wave 0 |
| HUMAN-02 | 至少 3 种不同格式的前缀 | unit | `pytest tests/test_humanize.py::test_at_least_3_formats -x` | ❌ Wave 0 |
| HUMAN-03 | 同批次邮箱前缀不重复 | unit | `pytest tests/test_humanize.py::test_uniqueness_across_batch -x` | ❌ Wave 0 |
| HUMAN-04 | 旧 profile 兼容、默认值行为正确 | unit | `pytest tests/test_humanize.py::test_backward_compatibility -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_humanize.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_humanize.py` — 覆盖 HUMAN-01 ~ HUMAN-04
- [ ] `tests/conftest.py` — 新增 humanize 相关 fixture（含 humanize_email 字段的配置字典）

*(现有测试基础设施 pytest + conftest.py 已就绪，仅需新增测试文件)*

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HUMAN-01 | 邮箱前缀使用真实人名+数字组合格式 | faker 库提供 first_name/last_name，4 种格式模板实现多样化前缀 |
| HUMAN-02 | 至少 3 种不同格式的前缀模板 | 4 种格式（firstname.lastname、firstname_NNNN、firstnameNN、f.lastname）均匀随机选取 |
| HUMAN-03 | 同批次邮箱前缀不重复 | 全局 set + threading.Lock 去重，冲突时重试 |
| HUMAN-04 | humanize_email 配置开关，旧 profile 兼容 | Pydantic `bool = True` 默认值，旧 profile 自动生效 |
</phase_requirements>

## Sources

### Primary (HIGH confidence)
- 项目源码 `chatgpt_register/adapters/*.py` — 5 个适配器的 create_temp_email 实现方式
- 项目源码 `chatgpt_register/config/model.py` — EmailConfig Pydantic 模型结构
- 项目源码 `chatgpt_register/core/batch.py` — 现有 threading.Lock 使用模式

### Secondary (MEDIUM confidence)
- faker PyPI 页面 — 版本信息和 API 稳定性
- names PyPI 页面 — 轻量备用库 API

### Tertiary (LOW confidence)
- 无

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — faker 是 Python 生态公认的假数据生成标准库
- Architecture: HIGH — 基于现有适配器模式和 threading 模式，改造路径清晰
- Pitfalls: HIGH — 线程安全和唯一性问题在现有代码中已有先例

**Research date:** 2026-03-14
**Valid until:** 2026-04-14（稳定领域，30 天有效）
