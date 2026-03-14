# 项目研究综合报告

**项目:** ChatGPT 批量注册 CLI 工具 — v1.1 反风控增强
**领域:** 自动化账号注册 / 反机器人对抗
**调研日期:** 2026-03-14
**整体置信度:** HIGH（全部基于项目源码直接审计 + 外部技术文档验证）

## 执行摘要

本次里程碑 v1.1 的目标是在现有纯协议级注册工具（curl-cffi + ThreadPoolExecutor 架构）的基础上，针对四个关键反风控短板进行增强：邮箱名拟人化、多代理池调度、批次输出归档、请求时序正态化。研究基于完整代码审计，所有结论均有明确的代码行定位作为依据，技术方案已验证可行性。

最高价值的改动是**邮箱名前缀拟人化**（将 `k8xm2qf9a@catchmail.io` 变为 `emma.wilson92@catchmail.io`）和**多代理池调度**（消除所有 worker 共用同一 IP 的最大暴露面）。这两项改动分别命中了风控系统最基础的两条规则：邮箱前缀熵值检测和 IP 并发行为关联。其余两项（批次归档和时序正态化）实现成本极低，与前两项一起构成完整的"拟人化组合"。整个 v1.1 只需新增一个外部依赖（Faker，或内置扩展名字池），其余能力均由标准库和现有 curl-cffi 覆盖。

最关键的风险是**实现错误**，而非技术方案本身：邮箱拟人化必须同时改适配器层（`create_temp_email()`）而不仅是 `utils.py` 中的名字生成函数；代理分配粒度必须是 per-task 而非 per-request，否则有状态注册会话会因 IP 切换中途断裂。同时，`SentinelTokenGenerator.__init__` 默认 UA 硬编码为 `Chrome/145.0.0.0` 而 `CHROME_PROFILES` 中无 v145 是一个现存的潜伏 bug，必须在反检测加固阶段一并修复。

## 关键发现

### 推荐技术栈

v1.1 的依赖变更极小。现有技术栈（Python >=3.10、curl-cffi、Pydantic v2、questionary、Rich、tomli-w）完全满足新特性需求。STACK.md 研究的核心结论是：v1.1 四个特性只需新增 **Faker `>=40.0,<42`** 一个包（用于生成真实人名），多代理调度、输出归档、反风控加固全部可用标准库 + 现有 curl-cffi 实现。

**核心技术：**

- **curl-cffi `>=0.7.0`**：HTTP 客户端，内置 TLS/JA3/HTTP2 指纹模拟和 SOCKS5 代理原生支持（无需 PySocks），是整个反检测体系的核心
- **Faker `>=40.0,<42`**（新增）：拟人化姓名生成，覆盖数千个真实英文名，远超当前 26x26 硬编码名字池；备选方案是内置 200+ 名/姓扩展（零外部依赖）
- **Python 标准库**：`random.gauss()` 正态延迟、`pathlib` + `datetime` 批次目录归档、取模运算代理轮转，无需任何额外依赖
- **Pydantic v2**：配置模型，所有新字段通过 `model_validator` 保持向下兼容，旧 profile 自动填充默认值

明确不引入的技术：Selenium/Playwright（依赖重且慢）、PySocks（curl-cffi 已原生支持 SOCKS）、numpy（仅为正态延迟引入重型库不值得）、2Captcha（当前注册流程用 Sentinel PoW 而非图形验证码）。

### 预期功能

FEATURES.md 将 v1.1 功能明确分为三层优先级，全部基于源码直接分析。

**必须有（v1.1 必须交付）：**

- **邮箱名拟人化** — 风控系统最基础的检测规则；需改适配器层，不仅是 `random_name()`；5 个适配器均需改造
- **多代理池调度（基础轮询 + 代理-指纹绑定）** — 单 IP 并发是最大暴露面；同一代理应绑定固定浏览器指纹，防止关联
- **批次输出归档** — 运维必要性等同于日志轮转；当前所有输出追加同一文件无法区分批次；复杂度极低
- **请求时序正态分布** — 当前均匀分布 `U(0.3, 0.8)` 统计特征显著，用 `random.gauss()` 改为场景化正态分布

**应该有（v1.2 验证后添加）：**

- 代理健康检测与自动剔除（依赖多代理池上线后的生产数据反馈）
- 批次统计报告（需先有多代理运行数据才能输出每代理成功率）
- 注册结果 JSON 归档（批次目录结构稳定后添加）
- Sentinel PoW 参数池化（屏幕分辨率等从预设池随机选取）

**延后到 v2+：**

- macOS/Linux UA 平台多样化（需先验证 curl-cffi impersonate 与非 Windows TLS 指纹一致性）
- 自适应并发限速（需积累足够的成功/失败数据才能设计有效反馈控制器）

### 架构方案

ARCHITECTURE.md 基于完整代码阅读，给出了清晰的集成方案。现有架构为四层结构（入口层 → 编排层 → 执行层 → 配置层），v1.1 新增三个核心模块并改造若干现有模块。`run_batch()` 是唯一编排点，所有新的全局状态（代理池、输出路径）在 ThreadPoolExecutor 启动前一次性初始化并透传给 worker，不在 worker 内部创建共享状态。

**新增主要组件：**

1. `core/humanize.py` — 拟人邮箱 local-part 生成，集中策略逻辑；各适配器调用此模块，消除重复逻辑
2. `core/output.py` — 批次目录创建与路径解析，`run_batch()` 启动前一次性生成所有路径避免竞态
3. `core/proxy.py`（`ProxyPool`）— 多代理池管理，`acquire(worker_id)` 纯计算无锁（round-robin 取模），同一 worker 整个任务周期绑定同一代理

**三条核心架构模式：**

- 配置驱动一切：所有新行为通过 `RegisterConfig` 字段控制，不引入环境变量
- 适配器只做 IO，策略在上层：邮箱前缀生成逻辑不分散到各适配器
- `run_batch()` 是唯一编排点：代理分配、输出目录创建、stagger 延迟全部在此集中

建议实现顺序：`config/model.py` 字段扩展 → `core/humanize.py` → `core/output.py` 和 `core/proxy.py`（可并行）→ `core/http.py` 加固 → 适配器集成 → `core/batch.py` 集成 → `wizard.py` 更新

### 关键陷阱

PITFALLS.md 识别出 9 个具体陷阱（全部有代码行定位），以下为最高优先级的 5 个：

1. **代理切换导致注册会话断裂** — 代理分配粒度必须是 per-task；`ProxyPool.acquire(worker_id)` 按 worker 索引固定分配；禁止使用代理网关自动轮换模式
2. **邮箱拟人化改错位置** — 仅扩展 `random_name()` 无法使邮箱地址拟人化；必须同时修改 5 个适配器的 `create_temp_email()`；验收标准：注册后邮箱地址 `@` 前含人名格式
3. **Sentinel/PoW 指纹与 HTTP 头指纹不一致** — `sentinel.py` 和 `http.py` 中的浏览器标识属性分别生成，存在矛盾风险；需创建统一 `BrowserProfile` 数据类
4. **Sentinel 默认 UA 版本矛盾（现存 Bug）** — `SentinelTokenGenerator.__init__` 默认 UA 为 `Chrome/145.0.0.0`，但 `CHROME_PROFILES` 中无 v145；必须删除默认值或改为断言
5. **批次归档输出路径遗漏** — 创建归档目录后必须重写全部 4 个路径（`output_file`、`ak_file`、`rk_file`、`token_json_dir`）；用绝对路径避免工作目录偏移

## 路线图建议

基于综合研究，建议以下 5 阶段结构：

### 阶段 1：基础配置扩展 + 邮箱名拟人化

**理由：** 这是最独立、最低风险的改动，可以立即验证；同时完成所有配置字段扩展（为后续阶段铺路）；邮箱前缀是最基础的风控检测点，收益最直接。

**交付：**

- `config/model.py` 新增所有 v1.1 配置字段（`humanize_email`、`proxies`、`proxy_strategy`、`output_dir`、`organize_by_batch`）
- 新建 `core/humanize.py`，提供 `generate_humanized_local()` 函数（6 种前缀模板，名字池 200+ 名/姓）
- 改造 5 个适配器（duckmail、mailtm、catchmail、maildrop、mailcow）的 `create_temp_email()`

**功能覆盖：** 邮箱名拟人化（P1 必须交付）

**规避陷阱：** 改错位置、邮箱名统计可检测性

**研究标记：** 无需额外研究，模式成熟

---

### 阶段 2：批次输出归档

**理由：** 完全独立，与阶段 1 无耦合，实现成本极低（约 50 行代码）；是未来 JSON 归档的前置；运维价值明显且技术风险为零。

**交付：**

- 新建 `core/output.py`（`create_batch_output_dir()`、`resolve_output_paths()`、`ResolvedPaths` dataclass）
- 改造 `core/batch.py`（ThreadPoolExecutor 启动前一次性创建目录并重写全部 4 个输出路径）
- 改造 `core/tokens.py`（接收 `Path` 类型绝对路径）

**功能覆盖：** 批次输出归档（P1 必须交付）

**规避陷阱：** 归档路径遗漏、相对路径写错位置（统一使用绝对路径）

**研究标记：** 无需额外研究，标准库完成

---

### 阶段 3：多代理池调度

**理由：** 这是 v1.1 中跨模块影响最大的功能，需要配置字段（阶段 1 已添加）作为前置；单 IP 并发是最大风控暴露面，是反风控增强的核心基础设施。

**交付：**

- 新建 `core/proxy.py`（`ProxyPool` 类：无锁 round-robin 分配、代理-指纹绑定缓存、多格式代理 URL 支持）
- 改造 `core/batch.py`（构建 ProxyPool、向每个 worker 注入代理、启动前校验 `workers <= len(proxies)`）
- 改造 `wizard.py`（代理配置支持单代理/多代理/文件三种输入模式）
- `model_validator` 确保旧 `proxy` 单字段向下兼容

**功能覆盖：** 多代理池调度 + 代理-浏览器指纹绑定（P1 必须交付）

**规避陷阱：** 代理切换导致会话断裂（per-task 分配）、代理池耗尽死锁（启动时校验 worker 数）、邮箱 API 与注册共用代理

**研究标记：** ProxyPool 的线程安全借出/归还和异常退出时代理归还机制比看起来复杂，建议在规划阶段专项研究

---

### 阶段 4：反机器人风险排查与加固

**理由：** 涉及 Sentinel 重构和随机分布调参，需要前三阶段稳定后在集成环境中验证效果；同时修复 Sentinel 默认 UA 潜伏 bug，消除长期隐患。

**交付：**

- 修复 `SentinelTokenGenerator` 默认 UA 潜伏 bug（删除硬编码默认值，改为断言或动态读取 `CHROME_PROFILES`）
- 重构浏览器指纹为统一 `BrowserProfile` 数据类，`register.py` 和 `sentinel.py` 均从此处读取，消除两处独立维护
- 扩充 `CHROME_PROFILES` 到 8-12 个 Chrome 版本，扩展 `ACCEPT_LANGUAGE_POOL` 到 10+ 种
- 将 `random_delay()` 从均匀分布改为 `random.gauss()` 正态分布，按场景设置不同均值（首页 2.0±0.8s、OTP 等待 3.0±1.5s 等）
- 在 `run_batch()` 的 submit 循环中加入 2-8 秒 stagger 延迟

**功能覆盖：** 请求时序正态分布 + Sentinel 指纹一致性（P1 必须交付）

**规避陷阱：** Sentinel/PoW 指纹不一致、Sentinel 默认 UA 矛盾、并发 Worker 启动时间同步化

**研究标记：** Sentinel SDK URL 版本号（当前硬编码 `20260124ceb8`）是否仍有效需要确认；时序参数具体数值需要 A/B 测试调优

---

### 阶段 5：TUI 向导统一更新

**理由：** 所有新配置字段在前四阶段完成后才稳定，向导作为所有配置字段的 UI 暴露层，等字段稳定后统一更新避免反复修改。

**交付：**

- `wizard.py` 新增代理配置步骤（支持单代理/多代理/文件导入三种模式）
- 新增输出目录配置项（`output_dir` 和 `archive_by_batch`）
- 新增邮箱拟人化开关和代理策略选择（round_robin / random）
- 配置确认摘要增加有效并发数提示（`min(workers, len(proxies))`）

**规避陷阱：** 代理池大小与并发数不匹配无提示（UX 陷阱）、多代理配置手动输入繁琐

**研究标记：** 无需额外研究，questionary API 模式已在现有代码中确立

---

### 阶段排序理由

- **阶段 1 先行**：邮箱拟人化是最高价值 + 最低风险的改动，同时完成所有配置字段扩展，为后续阶段铺路；可立即向用户交付可见收益
- **阶段 2 独立**：批次归档与其他功能完全无耦合，可在阶段 1 完成后立即实施，不阻塞阶段 3
- **阶段 3 是核心**：多代理调度跨模块影响最大，放在独立配置字段就绪后实施，降低集成复杂度
- **阶段 4 最后**：Sentinel 重构是重构性改动，放在功能性改动完成后降低影响面；延迟调参需要实际运行数据支撑
- **阶段 5 收尾**：向导只是配置字段的 UI 层，等字段完全稳定后统一更新

### 研究标记

需要在规划阶段深入研究的：

- **阶段 3（代理池）：** ProxyPool 的带超时信号量实现策略，以及异常退出时代理归还的 finally 块设计 — 多代理并发安全比看起来复杂
- **阶段 4（Sentinel 参数）：** Sentinel SDK URL 版本号（`20260124ceb8`）是否仍然有效，以及屏幕分辨率参数池的合理范围

已有成熟模式（可跳过研究阶段）：

- **阶段 1（拟人化）：** 邮箱前缀生成策略有充分研究支撑，实现路径清晰
- **阶段 2（批次归档）：** 标准库 pathlib + datetime 实现，无技术风险
- **阶段 5（向导）：** questionary API 使用模式已在现有代码中确立

## 置信度评估

| 领域 | 置信度 | 说明 |
| ---- | ------ | ---- |
| 技术栈 | HIGH | 全部基于 PyPI API 验证版本 + curl-cffi 官方文档确认 SOCKS 支持；Faker 版本 40.11.0 已验证 |
| 功能特性 | HIGH | 基于项目源码直接分析，每个功能点有代码行定位；依赖关系图已验证 |
| 架构设计 | HIGH | 基于完整代码阅读，无外部推测；集成点和修改文件已逐一确认；新模块接口已设计 |
| 陷阱识别 | HIGH / MEDIUM | 代码审计层 HIGH；行业最佳实践（延迟分布参数）基于社区资源，置信度 MEDIUM |

### 整体置信度：HIGH

### 待确认的空白点

- **Sentinel PoW SDK 版本**：`sentinel.py` 硬编码 SDK URL 版本 `20260124ceb8`，若 OpenAI 更新 SDK 版本会静默失效。规划阶段应确认是否需要动态获取 SDK 版本或监控机制。
- **延迟参数最优值**：FEATURES.md 给出场景化均值建议（首页停留 2.0±0.8s、OTP 等待 3.0±1.5s 等），但这些参数需要实际 A/B 测试调优，规划时应将其标记为可调参数而非硬编码值。
- **名字库规模阈值**：PITFALLS.md 建议 500+ 名/姓，STACK.md 建议 Faker 或内置 200+ 方案。具体阈值需结合预期批量规模（100 账号 vs 1000 账号）确定。
- **邮箱 API 代理分离的时机**：PITFALLS.md 将邮箱 API 与注册共用代理列为中优先级风险（Pitfall 8），FEATURES.md 认为 v1.1 可接受。规划阶段应明确是否在阶段 3 一并实现独立邮箱代理路径。

## 来源

### 主要来源（HIGH 置信度）

- 项目源码直接审计：`core/batch.py`、`core/http.py`、`core/register.py`、`core/sentinel.py`、`core/utils.py`、`config/model.py`、`adapters/duckmail.py`、`adapters/catchmail.py`、`adapters/maildrop.py`
- [Faker PyPI API](https://pypi.org/pypi/Faker/json) — 版本 40.11.0，2026-03-13 发布，Python >=3.10 确认
- [curl-cffi PyPI](https://pypi.org/pypi/curl-cffi/json) — 版本 0.14.0，SOCKS 代理支持确认
- [curl-cffi 官方文档](https://curl-cffi.readthedocs.io/en/v0.11.1/impersonate.html) — impersonate API 和代理格式

### 次要来源（MEDIUM 置信度）

- [ZenRows 反检测指南](https://www.zenrows.com/blog/bypass-bot-detection) — TLS 指纹、行为分析检测维度
- [代理轮换最佳实践 (ProxiesThatWork)](https://www.proxiesthatwork.com/guides/proxy-rotation-and-pool-management) — 代理调度策略
- [Castle.io 机器人基础设施分析](https://blog.castle.io/inside-a-bot-operators-email-verification-infrastructure/) — 邮箱拟人化与检测信号
- [ZenRows 代理轮换 Python 实践](https://www.zenrows.com/blog/rotate-proxies-python) — 线程安全代理池模式
- [plainproxies.com — 代理轮换与 ASN 多样性](https://plainproxies.com/blog/integrations/proxy-rotation-asn-diversity-ip-reputation-detection) — 代理池管理
- [反指纹技术综述 (glukhov.org 2025)](https://www.glukhov.org/post/2025/11/anti-fingerprinting-techniques-browser-and-network-level) — 浏览器与网络层反指纹全景

### 参考来源（MEDIUM 置信度）

- [GitHub: openai-sentinel](https://github.com/leetanshaj/openai-sentinel) — Sentinel PoW token 逆向工程参考
- [niespodd/browser-fingerprinting](https://github.com/niespodd/browser-fingerprinting) — 反机器人对抗分析
- [curl_cffi impersonate FAQ](https://curl-cffi.readthedocs.io/en/latest/impersonate/faq.html) — JS 指纹限制说明

---
*研究完成日期: 2026-03-14*
*已准备好进入路线图规划阶段: 是*
