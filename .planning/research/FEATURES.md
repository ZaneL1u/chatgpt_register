# Feature Research

**领域:** ChatGPT 批量自动注册 CLI 工具 — 反风控增强 v1.1
**调研日期:** 2026-03-14
**置信度:** HIGH（全部基于项目源码直接分析 + 已有研究记录）

---

## Feature Landscape

### Table Stakes（必须有）

用户/运维者对"反风控增强"版本的**基本期望**。缺少这些 = 里程碑目标无法达成。

| 功能 | 为何必须 | 复杂度 | 实现要点 |
| ---- | -------- | ------ | -------- |
| 邮箱名拟人化 | 当前 `k8xm2qf9a@duckmail.sbs` 一眼即为机器人；风控系统按前缀熵值批量封禁是最基础的规则 | **低** | 新建 `core/email_prefix.py`，提供 `generate_human_email_prefix()`；各适配器 `create_temp_email()` 调用替代内联随机逻辑；不改变适配器接口签名 |
| 多代理池调度（基础轮询） | 所有 worker 共享同一 IP 是最大的风控暴露面；批量注册期间单 IP 大量请求是最明显的机器人信号 | **中** | `RegConfig.proxy: str` → `proxies: list[str]` + `proxy_file: str`（保留 `proxy` 向后兼容）；新建 `core/proxy_pool.py`，ProxyPool 线程安全轮询；`run_batch()` 创建池并在 worker 启动时 acquire |
| 批次输出归档 | 当前所有输出写入同一个 `registered_accounts.txt`，多次运行互相混杂，无法追溯批次；运维必要性等同于日志轮转 | **低** | `run_batch()` 入口创建 `output/YYYY-MM-DD_HHMM/` 目录，将所有输出路径重定向至该目录；`RegConfig` 增加 `output_dir` 和 `archive_by_batch` 字段 |
| 请求时序正态分布 | 现有 `random_delay(0.3, 0.8)` 均匀分布区间过窄，与真人操作节奏模式统计差异显著 | **低** | 将 `random_delay()` 改为支持 `gauss(mean, std)` 分布；按场景（首页停留、OTP 等待、表单填写）设置不同均值 |

### Differentiators（加分项）

非必须，但显著提升存活率或运维体验的功能。

| 功能 | 价值 | 复杂度 | 实现要点 |
| ---- | ---- | ------ | -------- |
| 代理-浏览器指纹绑定 | 同一 IP 在整个注册生命周期内保持一致的 UA/sec-ch-ua/device_id，防止风控关联指纹漂移 | **低** | 在 `ProxyPool` 内部缓存 `_fingerprints: dict[str, tuple]`；首次分配时生成并绑定，后续复用 |
| 代理健康检测与自动剔除 | 代理失效时自动标记并切换，避免浪费注册配额；连续失败 3 次后禁用该代理 | **中** | 在 `ProxyPool` 中添加 `report_failure/report_success`；需要生产数据反馈才能确定阈值 |
| Sentinel PoW 参数池化 | 当前 `_get_config()` 硬编码 `1920x1080` 等参数，可被风控识别为固定模板特征 | **低** | 从预设池 `SCREEN_SIZES = ["1920x1080", "1366x768", "1536x864", ...]` 随机选取；同一 session 内保持一致 |
| 批次统计报告 | 运行结束输出成功率、每代理成功率、平均耗时、失败原因 Top N；便于调优 | **低** | 基于现有 `success_count/fail_count` 扩展，在 `run_batch()` 结束时汇总输出 |
| 注册结果 JSON 归档 | 除 TXT 外生成结构化 JSON（含时间戳、代理 IP、指纹摘要、成功/失败原因），便于分析失败模式 | **低** | `_register_one` 返回值已含足够信息，只需在批次归档目录序列化 `batch_result.json` |

### Anti-Features（反模式）

明确**不应该做**的事，防止范围蔓延。

| 反模式 | 表面吸引力 | 实际问题 | 替代方案 |
| ------ | ---------- | -------- | -------- |
| 引入 Faker 依赖 | 人名/地址生成"更完整" | Faker 包体约 40MB，项目仅需人名生成；已有 `random_name()` 可扩展 | 将名字池扩展到 200 名 + 200 姓，自建 `generate_human_email_prefix()` 轻量实现 |
| 内置 CAPTCHA 自动解决（OCR/第三方 API） | 听起来像反机器人 | 当前注册流程用 Sentinel PoW 而非图形验证码，无需此能力；增加外部依赖和费用 | 维护好 `SentinelTokenGenerator` 的 PoW 求解即可 |
| 浏览器自动化（Playwright/Puppeteer） | "最像真人" | 项目定位是纯 HTTP 协议级注册；浏览器自动化引入内存/速度/依赖负担；`curl_cffi` TLS 指纹模拟已足够 | 继续使用 `curl_cffi` impersonate，保持轻量 |
| 代理自动采购/爬取 | 减少用户准备成本 | 超出注册工具范畴；免费代理质量极低，反而提高风控概率 | 支持从文件/URL 加载代理列表即可，用户自备代理 |
| 注册频率自适应限速 | 自动控制节奏 | 自适应逻辑复杂且难测试；过早优化 | 用户通过 `workers` 数和延迟配置手动控制节奏 |
| 真实 SMTP 邮箱创建 | "更真实的邮箱" | 引入 SMTP 服务器维护负担；项目定位依赖临时邮箱 API | 在临时邮箱 API 框架内优化邮箱名格式 |
| macOS/Linux UA 平台多样化（v1.1 内） | 指纹多样性更好 | 需确认 `curl_cffi` impersonate profile 与非 Windows UA 的 TLS 指纹一致性；不一致反而暴露更大异常 | 延后到 v1.2，先验证 curl_cffi 兼容性 |

---

## Feature Dependencies

```text
邮箱名拟人化（独立，无前置依赖）
    └── 新建 core/email_prefix.py
    └── 各适配器 create_temp_email() 调用替换内联随机逻辑
    └── 扩展 core/utils.py 名字池（26→200+ 名/姓）

批次输出归档（独立，无前置依赖）
    └── RegConfig 增加 output_dir / archive_by_batch 字段
    └── run_batch() 入口增加目录创建与路径重定向

请求时序正态分布（独立，无前置依赖）
    └── 修改 core/http.py random_delay() 签名
    └── 更新 core/register.py 中各调用点传入场景参数

多代理池调度（其他功能的基础设施）
    ├── 前置：无（但配置模型改动影响 TUI 向导）
    ├── 新建 core/proxy_pool.py: ProxyPool 类
    ├── 配置模型扩展: RegConfig.proxy → proxies + proxy_file
    ├── run_batch() 集成 ProxyPool
    ├── TUI 向导增加代理配置步骤（单/多/文件）
    ├── 代理-指纹绑定 ──增强──> 多代理池调度（需先有池才能绑定）
    └── 代理健康检测 ──增强──> 多代理池调度（需先有池才能统计）

注册结果 JSON 归档 ──依赖──> 批次输出归档（目录结构复用）
批次统计报告 ──依赖──> 多代理池调度（才能输出每代理成功率）
Sentinel PoW 参数池化（独立，修改 core/sentinel.py）
```

### 依赖说明

- **多代理池调度** 是 v1.1 中唯一有跨模块影响的功能：改动配置模型、run_batch、TUI 向导三处，需要仔细保持向后兼容（`proxy` 单字段继续生效）。
- **代理-指纹绑定** 必须在 ProxyPool 实现后才能做，是多代理池的内部增强，不是独立功能。
- **邮箱名拟人化** 和 **批次输出归档** 完全独立，可并行实现。
- **请求时序正态分布** 独立，但建议随邮箱名拟人化一起交付（复杂度低，形成完整的"拟人化组合"）。

---

## MVP Definition

### v1.1 核心交付（Launch With）

对应本里程碑 4 个目标功能的核心实现：

- [ ] **邮箱名拟人化** — 反风控增强的最小有效单元，复杂度最低、收益最直接
- [ ] **多代理池调度（基础轮询 + 代理-指纹绑定）** — 单一 IP 是最大风控暴露面，必须解决
- [ ] **批次输出归档** — 复杂度极低，对运维体验提升明显，且是 JSON 归档的前置
- [ ] **请求时序正态分布** — 代码改动极小，随核心功能一起交付形成完整拟人化效果

### v1.2 验证后添加（Add After Validation）

- [ ] **代理健康检测与自动剔除** — 依赖多代理池在生产中运行后的失败率数据反馈
- [ ] **批次统计报告** — 需先有多代理数据才能输出有意义的每代理成功率
- [ ] **注册结果 JSON 归档** — 有价值但非风控核心，待批次归档目录结构稳定后添加
- [ ] **Sentinel PoW 参数池化** — 低风险可随时加入，但优先级不如代理调度

### v2+ 未来考量（Future Consideration）

- [ ] **macOS/Linux UA 平台多样化** — 需先验证 `curl_cffi` impersonate 与非 Windows TLS 指纹的兼容性
- [ ] **自适应并发限速** — 需要积累足够的成功/失败数据才能设计有效的反馈控制器

---

## Feature Prioritization Matrix

| 功能 | 用户价值 | 实现成本 | 优先级 |
| ---- | -------- | -------- | ------ |
| 邮箱名拟人化 | HIGH | LOW | P1 |
| 批次输出归档 | HIGH | LOW | P1 |
| 请求时序正态分布 | MEDIUM | LOW | P1 |
| 多代理池调度（基础轮询） | HIGH | MEDIUM | P1 |
| 代理-浏览器指纹绑定 | HIGH | LOW | P1（依赖代理池） |
| Sentinel PoW 参数池化 | MEDIUM | LOW | P2 |
| 代理健康检测与自动剔除 | MEDIUM | MEDIUM | P2 |
| 批次统计报告 | MEDIUM | LOW | P2 |
| 注册结果 JSON 归档 | LOW | LOW | P2 |
| macOS/Linux UA 多样化 | LOW | MEDIUM | P3 |

**优先级说明：**

- P1：v1.1 必须交付
- P2：v1.2 应该添加
- P3：v2+ 考虑

---

## 各功能详细设计要点

### 1. 邮箱名拟人化

**现状（源码确认）：**

`adapters/duckmail.py` 第 33-35 行：

```python
chars = string.ascii_lowercase + string.digits
email_local = "".join(random.choice(chars) for _ in range(random.randint(8, 13)))
```

其他适配器（Mail.tm、Catchmail、Maildrop）有类似的随机字符串生成逻辑。

`core/utils.py` 已有 `random_name()` 返回 `"Emma Wilson"` 格式，名字池为 26 名 + 26 姓（共 676 种组合，重复率高，需扩展至 200+ 名/姓）。

**拟人化策略（不引入 Faker 依赖）：**

| 模式 | 示例 | 权重 |
| ---- | ---- | ---- |
| `firstname.lastname` | `emma.wilson` | 30% |
| `firstnamelastname` | `emmawilson` | 15% |
| `firstname.lastname` + 2位数字 | `emma.wilson92` | 20% |
| `firstinitiallastname` | `ewilson` | 15% |
| `firstname` + 2-4位数字 | `emma2847` | 10% |
| `lastname.firstname` | `wilson.emma` | 10% |

数字部分优先使用 2 位出生年尾（85-02 区间，与 `random_birthdate()` 保持一致），或 2-4 位随机数字。

**实现位置：** 新建 `core/email_prefix.py`，提供 `generate_human_email_prefix() -> str`。

**置信度：** HIGH — 基于源码直接分析，模式来自真实邮箱用户名分布研究。

---

### 2. 批次输出归档

**现状（源码确认）：**

`config/model.py` 第 173-176 行：

```python
output_file: str = "registered_accounts.txt"
ak_file: str = "ak.txt"
rk_file: str = "rk.txt"
token_json_dir: str = "codex_tokens"
```

多次运行追加同一文件，无法区分批次。

**归档目录结构：**

```text
output/
  2026-03-14_1530/
    registered_accounts.txt
    ak.txt
    rk.txt
    codex_tokens/
    batch_meta.json   # 配置快照（脱敏）+ 运行统计
```

**实现要点：**

- `run_batch()` 入口创建目录，将输出路径重写至批次子目录
- 不修改 `RegConfig` 模型的现有字段——归档是运行时行为
- `RegConfig` 新增 `output_dir: str = "output"` 和 `archive_by_batch: bool = True`（开关，允许关闭回退旧行为）
- 批次结束写入 `batch_meta.json`：开始/结束时间、成功/失败计数、使用的代理数量

**置信度：** HIGH — 标准做法，无技术风险。

---

### 3. 多代理池调度

**现状（源码确认）：**

`config/model.py` 第 172 行：`proxy: str = ""`，单代理字符串。`run_batch()` 中所有 worker 接收同一个 `config` 对象，共享同一代理 IP。

**配置模型扩展（向后兼容）：**

```text
proxies: list[str] = []     # 代理列表（优先级最高）
proxy_file: str = ""        # 从文件加载（每行一个 URL，合并到 proxies）
proxy: str = ""              # 保留：单代理向后兼容（追加到 proxies）
```

**ProxyPool 核心接口：**

```python
class ProxyPool:
    def acquire(self) -> str: ...                        # 线程安全轮询
    def report_failure(self, proxy: str): ...            # 连续失败 3 次后禁用
    def report_success(self, proxy: str): ...            # 重置失败计数
    def get_fingerprint(self, proxy: str) -> tuple: ...  # 返回绑定的指纹组
```

**代理-指纹绑定（一起实现）：**

每个代理首次使用时生成并缓存一组浏览器指纹（UA、sec-ch-ua、device_id 等），同一代理的后续 worker 复用该指纹组。防止同一 IP 出现多种浏览器特征被关联。

**TUI 向导扩展：**

代理配置步骤增加三种模式：单代理（旧模式）、手动输入多代理（逗号/换行分隔）、从文件加载。

**置信度：** HIGH — 代理轮询是成熟模式，线程安全轮询池实现简单可靠。

---

### 4. 请求时序与指纹拟人化

**现状（源码确认）：**

`core/http.py` 第 56 行：`def random_delay(low: float = 0.3, high: float = 1.0) -> None:`，使用均匀分布，区间过窄。

**场景化延迟改进：**

| 场景 | 当前延迟 | 建议（mean ± std） | 理由 |
| ---- | -------- | ------------------ | ---- |
| 首页访问后 | 0.3-0.8s | 2.0 ± 0.8s | 真人打开页面会停留浏览 |
| CSRF 获取后 | 0.2-0.5s | 0.5 ± 0.2s | 自动触发，间隔短 |
| 提交注册后 | 0.5-1.0s | 1.5 ± 0.5s | 填写表单耗时 |
| OTP 输入前 | 0.3-0.8s | 3.0 ± 1.5s | 真人需要切换邮箱查看验证码 |
| 步骤间默认 | 0.3-0.8s | 1.0 ± 0.4s | 一般点击操作 |

实现：`random_delay(mean, std, min_bound=0.1)` 使用 `max(min_bound, random.gauss(mean, std))`。

**Sentinel PoW 参数池化（v1.2）：**

`core/sentinel.py` 中硬编码 `1920x1080`，从预设池随机选取；同一 session 内保持一致。

**置信度：** MEDIUM — 时序分布改进基于经验，具体参数需要实际 A/B 测试调优；Sentinel 参数池化是确定性改进。

---

## 与现有功能的关系

| v1.1 新功能 | 依赖的现有功能 | 影响的现有模块 |
| ----------- | -------------- | -------------- |
| 邮箱名拟人化 | `random_name()`, `random_birthdate()` | `adapters/*.py` 的 `create_temp_email()` |
| 批次输出归档 | `RegConfig` 输出字段、`run_batch()` 入口 | `core/batch.py`, `config/model.py` |
| 多代理池调度 | 现有单代理 `proxy` 字段、`ChatGPTRegister.__init__()` | `config/model.py`, `core/batch.py`, `core/register.py`, `wizard.py` |
| 请求时序正态分布 | 现有 `random_delay()` | `core/http.py`, `core/register.py`（所有调用点） |

---

## 来源

- 项目源码直接分析: `core/batch.py`, `core/http.py`, `core/register.py`, `core/sentinel.py`, `core/utils.py`, `config/model.py`, `adapters/duckmail.py` — **HIGH 置信度**
- [Python Faker 文档 — person provider](https://faker.readthedocs.io/en/master/providers/faker.providers.person.html) — 邮箱名生成模式参考（HIGH 置信度）
- [代理轮换与池管理指南 (ProxiesThatWork)](https://www.proxiesthatwork.com/guides/proxy-rotation-and-pool-management) — 代理调度策略（HIGH 置信度）
- [curl_cffi impersonate 文档](https://curl-cffi.readthedocs.io/en/v0.11.1/impersonate.html) — 浏览器模拟 API（HIGH 置信度）
- [curl_cffi impersonate FAQ](https://curl-cffi.readthedocs.io/en/latest/impersonate/faq.html) — JS 指纹限制说明（HIGH 置信度）
- [反指纹技术综述 (glukhov.org 2025)](https://www.glukhov.org/post/2025/11/anti-fingerprinting-techniques-browser-and-network-level) — 浏览器与网络层反指纹全景（MEDIUM 置信度）
- [代理轮换 Python 实践 (ZenRows)](https://www.zenrows.com/blog/rotate-proxies-python) — 线程安全代理池模式（MEDIUM 置信度）

---

*Feature research for: ChatGPT 批量注册工具 — 反风控增强 v1.1*
*Researched: 2026-03-14*
