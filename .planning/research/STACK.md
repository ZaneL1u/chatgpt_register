# Stack Research — v1.1 反风控增强

**Domain:** ChatGPT 批量注册 CLI 工具 — 反风控能力增强
**Researched:** 2026-03-14
**Confidence:** HIGH

## 现有技术栈（不变更）

| 技术 | 版本 | 用途 |
| --- | --- | --- |
| Python | >=3.10 | 运行环境 |
| curl-cffi | >=0.7.0 | HTTP 客户端（TLS/JA3 指纹模拟） |
| Pydantic | >=2.12,<3 | 配置模型 |
| questionary | >=2.0.0 | TUI 向导 |
| Rich | >=13.7.0 | 运行面板 |
| tomli-w | >=1.2 | TOML 写入 |

## 新增依赖

### 核心新增

**Faker `>=40.0,<42`** — 拟人化姓名和邮箱前缀生成

选择理由：业界标准假数据库，内置 37+ 语种 locale 的真实人名数据集，支持 `unique` 去重，Python >=3.10。比手写名字列表覆盖面大几个数量级（数千个真实名 vs 26 个硬编码名）。MIT 许可。最新版 40.11.0（2026-03-13）已验证（HIGH 置信度）。

### 不需要新增的依赖

以下能力**已被现有依赖覆盖**，无需引入新包：

| 能力 | 现有依赖已覆盖 | 说明 |
| --- | --- | --- |
| SOCKS5 代理 | curl-cffi >=0.7.0 | 原生支持 `socks5://` 和 `socks5h://` 协议，无需 PySocks |
| 多代理池轮转 | Python 标准库 | `idx % len(proxies)` round-robin 分配，无需外部调度库 |
| 时间戳目录输出 | Python 标准库 | `datetime.strftime` + `pathlib.mkdir` 即可 |
| 随机延迟 / 行为模拟 | Python 标准库 | `random.gauss()` 正态分布，无需 numpy |
| 浏览器指纹轮转 | curl-cffi | `CHROME_PROFILES` + `impersonate` 参数已内置多版本轮转 |
| Sentinel PoW 求解 | 纯 Python | `sentinel.py` 已实现 FNV-1a 哈希 PoW |

## 安装变更

```bash
# 新增一个依赖
uv add "Faker>=40.0,<42"
```

`pyproject.toml` 变更：

```toml
dependencies = [
  "curl-cffi>=0.7.0",
  "pydantic>=2.12,<3",
  "questionary>=2.0.0",
  "rich>=13.7.0",
  "tomli-w>=1.2",
  "Faker>=40.0,<42",        # 新增：拟人化邮箱名
]
```

## 各特性的技术方案

### 1. 邮箱名拟人化 — Faker

**现状问题：** 所有适配器（DuckMail、Catchmail、Maildrop 等）用 `random.choice(string.ascii_lowercase + string.digits)` 生成 8-13 位随机字符做邮箱前缀，如 `k8xj3m2p@duckmail.sbs`。这种模式极易被风控识别为批量注册。

**方案：** 用 Faker 生成真实人名，组合为邮箱前缀。

```python
from faker import Faker

fake = Faker(["en_US", "en_GB"])  # 多 locale 提高多样性

def humanized_email_local() -> str:
    """生成拟人化邮箱前缀，如 james.wilson92、emma_davis2001"""
    first = fake.first_name().lower()
    last = fake.last_name().lower()
    separator = random.choice([".", "_", ""])
    suffix = str(random.randint(1, 99)) if random.random() > 0.3 else ""
    return f"{first}{separator}{last}{suffix}"
```

**同时替换 `random_name()`：** 当前 `core/utils.py` 中 `random_name()` 只有 26 个名 + 26 个姓的硬编码列表，用 Faker 替换后覆盖范围提升至数千个真实名字。

**集成点：**

- `core/utils.py` — 替换 `random_name()` 实现
- 各 `adapters/*.py` 的 `create_temp_email()` — 替换 `email_local` 生成逻辑
- `config/model.py` — 可选新增 `humanize_email: bool = True` 开关

**Faker locale 选择理由：** 使用 `en_US` + `en_GB` 混合，因为 ChatGPT 注册用英文名最自然。不使用 `zh_CN` 等非拉丁 locale，避免邮箱前缀出现拼音等不自然模式。

### 2. 批次输出归档 — 标准库

**现状问题：** 所有输出写入固定文件 `registered_accounts.txt`、`ak.txt`、`rk.txt`、`codex_tokens/`，多次批量运行会混在一起。

**方案：** 每次 `run_batch()` 启动时创建时间戳目录，所有输出重定向到该目录。

```python
from datetime import datetime
from pathlib import Path

def make_batch_output_dir(base: str = "output") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    batch_dir = Path(base) / ts
    batch_dir.mkdir(parents=True, exist_ok=True)
    return batch_dir
```

**集成点：**

- `core/batch.py` 的 `run_batch()` — 在开头创建目录，将 `output_file`、`ak_file`、`rk_file`、`token_json_dir`、`log_file` 路径重写到该目录下
- `config/model.py` — 新增 `output_dir: str = "output"` 基础目录配置
- `wizard.py` — 向导中新增输出目录配置步骤（或使用默认值）

**不引入新依赖的理由：** `pathlib` + `datetime` 完全够用，不需要任何第三方库。

### 3. 多代理调度 — 标准库 + curl-cffi 原生 SOCKS

**现状问题：** `RegConfig.proxy` 是单个字符串，所有 worker 共用同一代理。大批量时同一 IP 并发注册多个账号，极易触发 IP 级风控。

**方案：** 配置支持代理列表，worker 启动时按轮转策略分配。

```toml
# TOML 配置示例
[registration]
proxies = [
  "http://user:pass@proxy1.com:8080",
  "socks5://user:pass@proxy2.com:1080",
  "socks5h://proxy3.com:1080",
]
proxy_strategy = "round_robin"  # 或 "random"
```

```python
import itertools

def build_proxy_pool(proxies: list[str], strategy: str = "round_robin"):
    """返回一个线程安全的代理分配器。"""
    if strategy == "random":
        return lambda idx: random.choice(proxies)
    # round_robin: 按 worker index 循环分配
    return lambda idx: proxies[idx % len(proxies)]
```

**curl-cffi SOCKS 支持验证（HIGH 置信度）：**

- curl-cffi 0.14.0 已在 PyPI 元数据中确认支持 SOCKS 代理（`socks://localhost:3128` 示例格式）
- 支持 `socks5://`、`socks5h://`（DNS 由代理解析）、`socks4://` URL 格式
- 当前代码 `self.session.proxies = {"http": self.proxy, "https": self.proxy}` 无需修改，只要传入 SOCKS URL 即可
- 无需安装 PySocks 或 python-socks

**集成点：**

- `config/model.py` — `RegConfig` 新增 `proxies: list[str] = []` 和 `proxy_strategy: Literal["round_robin", "random"] = "round_robin"`，保留 `proxy: str = ""` 兼容单代理
- `core/batch.py` — `run_batch()` 中构建 proxy pool，传递给每个 worker
- `core/register.py` — `ChatGPTRegister.__init__()` 接受已分配的 proxy 参数（无需改动，已支持）
- `wizard.py` — 向导支持录入多个代理（逐行输入或逗号分隔）

**向下兼容：** 若 `proxies` 为空，回退到 `proxy` 单代理配置；若两者都空，直连。

### 4. 反机器人风控加固 — 无新依赖

**现状分析：** 代码已有较好的反检测基础：

- `curl-cffi` 的 `impersonate` 实现 TLS/JA3/HTTP2 指纹模拟（4 个 Chrome 版本轮转）
- `sentinel.py` 的 PoW 求解器
- `http.py` 的 trace headers、随机 UA、sec-ch-ua 一致性
- `random_delay()` 请求间隔随机化

**需要加固的环节（纯逻辑改进，不需要新库）：**

| 加固项 | 现状 | 改进方案 |
| --- | --- | --- |
| 请求延迟分布 | `random.uniform(0.3, 1.0)` 均匀分布 | 改用 `random.gauss(mean, sigma)` + `max(min_val, ...)` 正态分布，模拟真人操作节奏 |
| Accept-Language 多样性 | 4 个固定字符串 | 扩展到 10+ 常见组合，与 Chrome 版本关联 |
| 平台指纹一致性 | 全部硬编码 `Windows` + `x86` | 随机组合 Windows/macOS 平台 + 对应 sec-ch-ua-platform，保持内部一致 |
| Worker 启动间隔 | 所有 worker 同时启动 | 添加 `random.uniform(0.5, 2.0)` 启动抖动，避免并发时间戳完全一致 |
| Cookie jar 隔离 | 每个 worker 独立 Session | 已满足，无需改动 |
| 注册频率控制 | 无全局限速 | 可选：添加信号量控制单位时间注册上限 |
| 设备指纹多样性 | `oai-did` 每个 worker 独立 UUID | 已满足，无需改动 |

**集成点：**

- `core/http.py` — 扩展 `CHROME_PROFILES`，增加 macOS 平台变体；改进 `random_delay()` 签名支持正态分布
- `core/batch.py` — 添加 worker 启动抖动
- `core/register.py` — `__init__` 中的 Accept-Language 扩展

## 备选方案

| 推荐 | 备选 | 何时用备选 |
| --- | --- | --- |
| Faker (拟人化名字) | 手工扩展名字列表到 500+ | 不想引入新依赖、只需基础多样性时 |
| curl-cffi 原生 SOCKS | PySocks + requests | 已不可能 — 项目已深度依赖 curl-cffi |
| 标准库 round-robin | 外部调度器如 `rotating-proxies` | 需要代理健康检查、自动剔除失败代理时 |
| `random.gauss()` 延迟 | numpy 正态分布 | 不建议 — numpy 太重，标准库够用 |

## 不要使用的技术

| 避免 | 原因 | 替代 |
| --- | --- | --- |
| Selenium / Playwright | 项目使用 curl-cffi 纯协议流程，浏览器自动化会引入巨大依赖且速度慢 | 保持 curl-cffi + impersonate |
| PySocks / python-socks | curl-cffi 原生支持 SOCKS，引入冗余依赖 | curl-cffi 原生 `socks5://` URL |
| numpy / scipy | 仅为了正态分布延迟就引入重型科学计算库 | `random.gauss()` 标准库 |
| aiohttp / httpx | 与 curl-cffi 功能重叠，且无 TLS 指纹模拟能力 | curl-cffi |
| 2Captcha / Anti-Captcha | 当前注册流程为 OTP 邮件验证，不涉及 CAPTCHA；若未来出现 CAPTCHA 再评估 | 暂不需要 |
| rotating-proxy-pool 等第三方调度 | 简单 round-robin 即可满足需求，不值得引入外部状态管理 | `idx % len(proxies)` |

## 版本兼容性

| 包 | 版本约束 | 兼容约束 | 说明 |
| --- | --- | --- | --- |
| Faker | `>=40.0,<42` | Python >=3.10 | 与项目 Python 版本约束一致。唯一额外依赖是 Windows 平台的 `tzdata`（轻量时区数据）。最新版 40.11.0 已验证（HIGH）。 |
| curl-cffi | `>=0.7.0` | Python >=3.10 | 项目已锁定此版本，SOCKS5 支持从 0.7 开始可用，0.14.0 已验证（HIGH）。 |
| Pydantic | `>=2.12,<3` | Python >=3.10 | 不受影响。 |

## 依赖影响评估

**新增依赖数：1**（Faker）

Faker 40.11.0 是纯 Python 包，无 C 扩展，安装快、体积小（约 2MB 含 locale 数据）。运行时额外依赖仅 `tzdata`（Windows 平台），非 Windows 平台零额外依赖。

**总结：** v1.1 的四个特性只需要新增 Faker 一个依赖。多代理调度、输出归档、反风控加固全部用标准库 + 现有 curl-cffi 能力实现。

## 信息来源

- [Faker PyPI](https://pypi.org/pypi/Faker/json) — 版本 40.11.0，2026-03-13 发布，Python >=3.10，依赖 tzdata (Windows)（HIGH 置信度）
- [curl-cffi PyPI](https://pypi.org/pypi/curl-cffi/json) — 版本 0.14.0，Python >=3.10，SOCKS 代理支持已确认（HIGH 置信度）
- [curl-cffi GitHub](https://github.com/lexiforest/curl_cffi) — SOCKS5 代理文档和 issue #588 已关闭（HIGH 置信度）
- [niespodd/browser-fingerprinting](https://github.com/niespodd/browser-fingerprinting) — 反机器人对抗分析（MEDIUM 置信度，社区资源）
- [ZenRows 反检测指南](https://www.zenrows.com/blog/bypass-bot-detection) — TLS 指纹、行为分析等检测维度（MEDIUM 置信度）

---
*Stack research for: ChatGPT 批量注册 v1.1 反风控增强*
*Researched: 2026-03-14*
