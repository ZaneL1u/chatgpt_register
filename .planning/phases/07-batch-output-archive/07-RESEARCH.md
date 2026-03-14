# Phase 7: 批次输出归档 - Research

**Researched:** 2026-03-15
**Domain:** Python 文件输出路径管理
**Confidence:** HIGH

## Summary

本阶段目标是将批量注册产生的所有结果文件（registered_accounts.txt、ak.txt、rk.txt、codex_tokens/、log 文件）自动写入 `output/YYYYMMDD_HHMM/` 归档子目录，取代当前直接写入项目根目录的行为。

技术上仅涉及 Python 标准库（`datetime`、`pathlib`、`os`），无需引入任何新依赖。核心改动集中在 `run_batch()` 函数入口处创建归档目录，并将所有文件路径重定向到该目录下。

**Primary recommendation:** 在 `run_batch()` 最前端创建一个归档目录生成函数，所有下游文件路径（output_file、ak_file、rk_file、token_json_dir、log_file）统一指向该目录。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
无显式锁定决策 — 所有实现细节均委托给 Claude。

### Claude's Discretion
以下决策均由用户委托 Claude 自行决定：

**归档目录策略：**
- 在 `run_batch()` 开始时创建归档目录 `output/YYYYMMDD_HHMM/`，所有文件直接写入该目录
- 时间戳使用本地时间（与现有日志时间一致）
- 同一分钟内多次运行时追加 `_N` 后缀（如 `20260315_1430_2`）
- 日志文件（log_file）也一并写入归档目录

**配置与兼容性：**
- 归档行为默认开启，无需额外开关
- `RegConfig` 中的 `output_file`、`ak_file`、`rk_file`、`token_json_dir` 字段仅作为文件名使用（忽略路径前缀），实际写入归档目录
- `output/` 前缀固定，不提供额外配置项（保持简单）
- 旧配置无需修改即可生效

**归档后的用户反馈：**
- 注册完成后终端摘要中显示归档目录完整路径
- Dashboard 面板启动时显示当前归档目录路径

**历史数据迁移：**
- 不处理已存在的旧格式结果文件
- 只影响新运行，旧文件保留原位

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BATCH-01 | 注册完成后，所有结果文件（tokens、ak、rk、token json）自动写入 `output/<YYYYMMDD_HHMM>/` 归档目录 | 归档目录生成函数 + run_batch 路径重定向 + save_tokens 路径传递 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathlib | stdlib | 路径构造与操作 | 项目已使用 Path，类型安全 |
| datetime | stdlib | 时间戳生成 | 本地时间格式化 |
| os | stdlib | 目录创建、路径拼接 | 项目已使用 os.path / os.makedirs |

### Supporting
无需额外依赖。

### Alternatives Considered
无 — 纯标准库操作，无替代方案讨论必要。

## Architecture Patterns

### 归档目录生成模式

**What:** 在 `run_batch()` 入口创建 `output/YYYYMMDD_HHMM/` 目录，返回 Path 对象
**When to use:** 每次 `run_batch()` 调用

```python
from datetime import datetime
from pathlib import Path

def create_archive_dir(base: str = "output") -> Path:
    """生成带时间戳的归档目录，冲突时追加 _N 后缀。"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    candidate = Path(base) / stamp
    if not candidate.exists():
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    # 同一分钟内多次运行
    n = 2
    while True:
        candidate = Path(base) / f"{stamp}_{n}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        n += 1
```

### 路径重定向模式

**What:** 从 `RegConfig` 字段中提取纯文件名（`os.path.basename`），拼接到归档目录
**When to use:** `run_batch()` 创建归档目录后

```python
archive_dir = create_archive_dir()
output_file = str(archive_dir / Path(config.registration.output_file).name)
ak_file = str(archive_dir / Path(config.registration.ak_file).name)
rk_file = str(archive_dir / Path(config.registration.rk_file).name)
token_json_dir = str(archive_dir / Path(config.registration.token_json_dir).name)
log_file = str(archive_dir / "batch.log")
```

### Integration Points

| 修改位置 | 当前行为 | 归档后行为 |
|----------|----------|-----------|
| `run_batch()` (batch.py:150) | 直接使用 `config.registration.output_file` | 使用 `archive_dir / basename(output_file)` |
| `_register_one()` (batch.py:60) | 接收 `output_file` 参数 | 不变 — 调用方传入归档路径 |
| `ChatGPTRegister.save_tokens()` (register.py:956) | 读取 `config.registration.ak_file` 等 | 需传入归档路径覆盖或修改 config 副本 |
| `_open_log_file()` (batch.py:24) | 写入 `config.registration.log_file` | 写入归档目录下 |
| `dashboard` 启动时 | 无归档信息 | 显示归档目录路径 |
| 注册完成摘要 | 显示 `output_file` | 显示归档目录完整路径 |

### Anti-Patterns to Avoid
- **直接修改 config 对象:** Pydantic model 可能触发 validation，应该在 `run_batch()` 内部用局部变量覆盖路径，而非修改 `config.registration` 字段
- **TOCTOU 竞态:** `exists()` 检查后再 `mkdir()` 存在竞态，使用 `mkdir(exist_ok=True)` 规避
- **绝对路径残留:** `token_json_dir` 的 `save_codex_tokens` 中有 `os.path.isabs()` 判断，归档路径需确保是相对路径或统一处理

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 时间戳格式化 | 手动拼接字符串 | `datetime.now().strftime()` | 标准库已足够 |
| 目录创建 | 手动递归检查 | `Path.mkdir(parents=True, exist_ok=True)` | 原子性、线程安全 |

## Common Pitfalls

### Pitfall 1: save_tokens 路径硬读 config
**What goes wrong:** `ChatGPTRegister.save_tokens()` 直接从 `self.config.registration.ak_file` 读取路径，不经过归档重定向
**Why it happens:** save_tokens 在 register.py 中调用 save_codex_tokens，路径来自 config 而非外部传入
**How to avoid:** 在创建 `ChatGPTRegister` 实例之前，修改传入 config 的注册字段，或在 `save_tokens` 中增加路径覆盖参数
**Warning signs:** tokens 文件写到项目根目录而非归档目录

### Pitfall 2: 同一分钟内冲突
**What goes wrong:** 快速连续运行两次 `run_batch()`，第二次覆盖第一次结果
**Why it happens:** 时间戳精度只到分钟
**How to avoid:** 检测目录已存在时追加 `_N` 后缀
**Warning signs:** 归档目录内文件数量异常多

### Pitfall 3: Dashboard 不显示归档路径
**What goes wrong:** 用户不知道结果文件写到了哪里
**Why it happens:** Dashboard 初始化时不传入归档目录信息
**How to avoid:** 在 banner 或 summary 中显示归档目录路径

## Code Examples

### 现有 run_batch 入口 (batch.py:150-160)
```python
def run_batch(config: RegisterConfig):
    total_accounts = config.registration.total_accounts
    output_file = config.registration.output_file    # 直接使用
    log_file = config.registration.log_file
    max_workers = config.registration.workers
```

### 现有 save_tokens 调用链 (register.py:956-970)
```python
def save_tokens(self, email: str, tokens: dict) -> None:
    save_codex_tokens(
        email, tokens,
        ak_file=self.config.registration.ak_file,     # 直接从 config 读取
        rk_file=self.config.registration.rk_file,
        token_json_dir=self.config.registration.token_json_dir,
        ...
    )
```

### 推荐改造方式

最简洁的方式是在 `run_batch()` 中创建一个 config 的浅拷贝（或直接修改 registration 字段），使下游所有代码自动拿到归档路径：

```python
import copy

def run_batch(config: RegisterConfig):
    archive_dir = create_archive_dir()

    # 创建 config 副本，重定向所有输出路径到归档目录
    config = config.model_copy(deep=True)
    reg = config.registration
    reg.output_file = str(archive_dir / Path(reg.output_file).name)
    reg.ak_file = str(archive_dir / Path(reg.ak_file).name)
    reg.rk_file = str(archive_dir / Path(reg.rk_file).name)
    reg.token_json_dir = str(archive_dir / Path(reg.token_json_dir).name)
    if reg.log_file:
        reg.log_file = str(archive_dir / Path(reg.log_file).name)
    else:
        reg.log_file = str(archive_dir / "batch.log")

    # 后续代码无需任何修改，所有路径自动指向归档目录
```

这种方式的优势：
1. 下游的 `_register_one`、`save_tokens`、`save_codex_tokens` 全部零改动
2. config.model_copy() 是 Pydantic v2 标准 API，安全可靠
3. 归档逻辑集中在一个位置，易于维护

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (已安装) |
| Config file | pyproject.toml |
| Quick run command | `python -m pytest tests/test_archive.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BATCH-01 | 归档目录生成（时间戳格式、冲突后缀） | unit | `python -m pytest tests/test_archive.py::test_create_archive_dir -x` | :x: Wave 0 |
| BATCH-01 | 路径重定向（output/ak/rk/token_json/log 均指向归档目录） | unit | `python -m pytest tests/test_archive.py::test_path_redirection -x` | :x: Wave 0 |
| BATCH-01 | run_batch 集成（归档目录实际被创建和使用） | integration | `python -m pytest tests/test_archive.py::test_run_batch_archive -x` | :x: Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_archive.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before verify

### Wave 0 Gaps
- [ ] `tests/test_archive.py` — covers BATCH-01 (归档目录生成、路径重定向、集成测试)

## Sources

### Primary (HIGH confidence)
- 项目源码直接审查：batch.py、tokens.py、register.py、model.py、dashboard.py
- Python 标准库文档：pathlib、datetime、os

### Secondary (MEDIUM confidence)
- Pydantic v2 model_copy() API — 用于 config 浅拷贝

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 纯标准库，无版本风险
- Architecture: HIGH — 改动点明确，影响范围可控
- Pitfalls: HIGH — 已识别所有路径传递链路

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable — 纯内部重构)
