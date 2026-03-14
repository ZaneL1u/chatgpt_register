# Pitfalls Research

**Domain:** ChatGPT 批量注册工具 — v1.1 反风控增强（邮箱拟人化、多代理调度、反机器人加固、批次归档）
**Researched:** 2026-03-14
**Confidence:** HIGH（基于代码审计 + 行业实践调研）

## Critical Pitfalls

### Pitfall 1: 代理切换导致注册会话断裂

**What goes wrong:**
注册流程是多步有状态会话（首页 → CSRF → Signin → Authorize → Register → OTP → CreateAccount → Callback，外加 OAuth 7 步），当前 `ChatGPTRegister.__init__` 中 `self.proxy` 在整个实例生命周期内保持不变。如果引入多代理池后在注册流程**中途**切换代理 IP，OpenAI 的会话绑定机制（cookie + IP 关联、Cloudflare session affinity）会立即将请求判定为可疑，返回 403 或触发额外验证。

**Why it happens:**
开发者在实现代理池时容易按"每个 HTTP 请求轮换代理"的直觉设计 rotation 策略。当前 `batch.py` 的 `_register_one()` 在任务开始时创建 `ChatGPTRegister` 实例，代理在 `__init__` 时绑定到 `self.session.proxies` — 这个粒度恰好正确。但扩展为多代理池时，如果在 session 级别做代理轮换（比如用代理网关的自动轮换功能），就会破坏此约束。

**How to avoid:**

- 代理分配粒度必须是 **per-task**（每个注册任务），不是 per-request
- 在 `run_batch()` 层做代理分配：从池中取出代理 → 传入 `_register_one()` 的 config 覆盖 `registration.proxy` → 整个注册 + OAuth 流程完成后归还
- 同一个 `ChatGPTRegister` 实例生命周期内，`self.proxy` 和 `self.session.proxies` 不可变
- 禁止使用代理网关的自动轮换模式（如 BrightData 的 `session` 参数需要固定）

**Warning signs:**

- 注册步骤 3（Authorize）或步骤 5（Send OTP）频繁 403
- OAuth 流程中 `login_session` cookie 丢失
- 成功率随并发数增加急剧下降，但单线程运行正常

**Phase to address:**
多代理调度阶段 — 应为第一个实现的反风控特性，因其他特性（拟人化、反机器人排查）的效果验证依赖代理基础设施正确工作

---

### Pitfall 2: Sentinel/PoW 环境指纹与 HTTP 头指纹不一致

**What goes wrong:**
`sentinel.py` 的 `SentinelTokenGenerator._get_config()` 生成的环境指纹（屏幕分辨率 `"1920x1080"`、User-Agent、navigator 属性等）与 `register.py` 中 `ChatGPTRegister.__init__` 设置的 HTTP 请求头（`sec-ch-ua`、`User-Agent`、`sec-ch-ua-platform: "Windows"`）是**分别生成**的。OpenAI 可以通过对比 Sentinel payload 中声称的浏览器环境与 HTTP 层的 TLS/header 指纹来检测矛盾。

**Why it happens:**
当前代码中 `build_sentinel_token()` 接受 `user_agent` 和 `sec_ch_ua` 参数并传给 `SentinelTokenGenerator`，但 `_get_config()` 内部还有独立的硬编码值（屏幕分辨率、locale、SDK URL 版本号 `20260124ceb8` 等），这些并未从 HTTP session 配置中统一派生。目前 `register.py:82` 也硬编码了 `'"Windows"'` 和 `'"x86"'`，恰好与 sentinel 一致 — 但这种一致性是**偶然的巧合**，不是结构化保证。反风控加固时如果只改了 HTTP 头侧而忘记同步 sentinel 侧（或反之），就会产生可被检测的矛盾。

**How to avoid:**

- 创建一个 `BrowserProfile` 数据类，统一存放 UA、platform、screen resolution、locale、Chrome 版本号等所有浏览器标识属性
- `ChatGPTRegister.__init__` 和 `SentinelTokenGenerator._get_config()` 都从同一个 `BrowserProfile` 实例读取
- 确保 `CHROME_PROFILES` 表中的 `sec_ch_ua` 版本号与 `impersonate` 参数和 UA 字符串中的版本号完全一致（当前代码已做到，但新增浏览器版本时容易遗漏）
- Sentinel SDK URL 中的版本号应可配置或从挑战响应中动态获取

**Warning signs:**

- Sentinel challenge 返回更高 difficulty（PoW 难度升级意味着被怀疑）
- 注册步骤 2（Signin/authorize/continue）开始出现额外验证要求
- OAuth 步骤 2 返回 `invalid_auth_step` 的频率明显上升

**Phase to address:**
反机器人风险排查阶段 — 统一指纹生成是加固注册流程的核心前提

---

### Pitfall 3: Sentinel 默认 UA 与 CHROME_PROFILES 版本矛盾（潜伏 Bug）

**What goes wrong:**
`SentinelTokenGenerator.__init__` 的默认 `user_agent` 硬编码为 `Chrome/145.0.0.0`，但 `http.py` 的 `CHROME_PROFILES` 中没有版本 145（当前包含 131、133、136、142）。在正常注册流程中，`build_sentinel_token()` 会显式传入从 `random_chrome_version()` 得到的 UA — 所以主路径暂时安全。但若任何代码路径直接调用 `SentinelTokenGenerator()` 不传 `user_agent`，或将来有人重构 sentinel 调用时省略参数，就会产生版本 145 的 UA 同时配合非 145 Chrome 的 TLS 指纹，形成可检测矛盾。

**Why it happens:**
`SentinelTokenGenerator.__init__` 和 `CHROME_PROFILES` 是两处独立维护的 UA 来源，没有从统一数据结构派生。每次添加新 Chrome 版本到 `CHROME_PROFILES` 时，开发者需要记住也要更新 sentinel 默认 UA — 这是一个"两处维护"的隐患。

**How to avoid:**

- `SentinelTokenGenerator.__init__` 的默认 UA 应从 `CHROME_PROFILES` 动态读取（如取最新 major），不能硬编码
- 或者将默认 UA 设为 `None` 并添加断言：`assert user_agent is not None, "必须传入 user_agent"`
- 添加测试用例：验证 `SentinelTokenGenerator` 在不传 UA 时抛出异常，而不是静默使用错误的默认值

**Warning signs:**

- Sentinel payload 解码后的 UA 字符串版本与 HTTP 请求头 `User-Agent` 版本不一致
- `fetch_sentinel_challenge()` 成功但 `build_sentinel_token()` 返回的 token 被拒绝（OpenAI 返回 401/403 在 sentinel 验证步骤）

**Phase to address:**
反机器人风险排查阶段 — 在 BrowserProfile 统一指纹重构时一并修复

---

### Pitfall 4: 邮箱拟人化改错位置——名字只影响 ChatGPT 账户名，不影响邮箱前缀

**What goes wrong:**
`batch.py` 中的 `random_name()` 调用生成的 `name` 变量用于 ChatGPT 账户的显示名（传入 `run_register(email, chatgpt_password, name, birthdate, ...)`），**不影响邮箱地址本身**。而邮箱地址前缀由各适配器的 `create_temp_email()` 独立生成：`CatchmailAdapter` 和 `MaildropAdapter` 使用纯随机字母数字（8-13 位），`DuckMail` / `Mail.tm` 等也有各自的生成逻辑。如果开发者仅扩展 `random_name()` 并认为"拟人化完成"，会发现实际注册的邮箱地址仍然是 `xk3m9qjlpv@catchmail.io` 这样的乱码。

**Why it happens:**
`random_name()` 的作用域仅限于 `batch.py` 中的 `name` 变量（用于账户注册），而邮箱地址前缀的生成逻辑分散在 5 个不同适配器文件中。职责分散导致开发者容易只改一处。

**How to avoid:**

- 在适配器基类 `EmailAdapter.create_temp_email()` 中提供可选的 `name_generator` 钩子，或在构造时接受名字生成函数
- 在 `_register_one()` 中先生成拟人化名字（`name, local_part = generate_human_name()`），然后将 `local_part` 传给适配器生成邮箱，同一个 `name` 也用于 ChatGPT 账户注册 — 保证邮箱前缀与显示名匹配
- 明确 v1.1 验收标准：生成 1000 个邮箱地址，检查本地部分（`@` 前）是否包含可识别的人名格式，而不是随机字符串

**Warning signs:**

- 运行后 `registered_accounts.txt` 中邮箱地址前缀仍是随机字母数字
- 测试生成 100 个邮箱：`xk3m9qjlpv@catchmail.io`、`r5t8jmn2kp@catchmail.io` — 均无人名特征

**Phase to address:**
邮箱名拟人化阶段 — 这是该特性的核心实现位置，必须改适配器层，不只是 `utils.py`

---

### Pitfall 5: 邮箱名拟人化的统计可检测性

**What goes wrong:**
当前 `random_name()` 只有 26 个 first name + 26 个 last name = 676 种组合。在批量注册场景下，短时间内从同一临时邮箱域名（如 `catchmail.io`）注册大量 `firstname.lastname+数字` 格式的邮箱，分布明显异于真实用户注册模式。关联检测系统可以通过邮箱前缀的模式相似度和注册时间的聚集度来识别批量行为。

**Why it happens:**

- 名字池太小：676 种组合在注册 100+ 账号后碰撞概率显著上升
- 邮箱前缀格式单一：如果所有邮箱都是 `jamessmith42@catchmail.io` 这种统一模式，格式本身就是检测信号
- 临时邮箱域名本身就在风控黑名单中，名字再像也经不住域名层面的封堵
- 名字来源全部是英文名，如果注册 IP 显示在非英语国家，构成 locale 不一致信号

**How to avoid:**

- 扩展名字库到至少 500+ first name x 500+ last name，涵盖多族裔姓名（与 IP 地理位置匹配更佳）
- 邮箱前缀格式多样化：随机使用 `firstname.lastname`、`firstnamelastname`、`f.lastname`、`firstname_l`、`lastname.firstname123` 等至少 5 种模板
- 数字后缀的分布应模拟真实用户习惯：出生年份后两位（85-02）比纯随机 4 位数更自然
- 名字库外置为数据文件（如 JSON/CSV），便于更新和扩展，无需改代码发版

**Warning signs:**

- 注册成功率在同一邮箱平台上随批次推进逐渐下降
- OpenAI 开始对特定邮箱域名施加额外验证（如要求手机号）
- 多个账号被同时封禁（关联检测命中同批次账号）

**Phase to address:**
邮箱名拟人化阶段 — 这是该特性的核心设计问题

---

### Pitfall 6: 并发 Worker 的启动时间模式暴露机器行为

**What goes wrong:**
当前 `run_batch()` 使用 `ThreadPoolExecutor` 一次性 submit 所有任务。假设 `workers=5, total_accounts=20`，前 5 个任务几乎同时启动，在同一秒内从 5 个不同 IP 开始完全相同的注册流程（首页 → CSRF → Signin...）。虽然 `random_delay()` 在**步骤间**加了 0.3-1.0 秒的均匀随机延迟，但**任务之间**没有错开启动时间。这种时序特征在 OpenAI 的关联检测中极为明显。

**Why it happens:**
`ThreadPoolExecutor` 提交所有 future 后，前 `max_workers` 个任务立即并发启动 — 这是线程池的正常行为。开发者关注了单任务内的步骤间拟真延迟，但忽略了任务间的启动间隔。此外，当前 `random_delay()` 使用均匀分布 `random.uniform(low, high)`，而真实人类的操作间隔更符合对数正态分布（大多数快速操作 + 少数较长停顿）。

**How to avoid:**

- 在 `run_batch()` 中，每个 `executor.submit()` 之间加入随机启动延迟（2-8 秒）
- 或在 `_register_one()` 开始时加入基于任务序号的错开延迟：`time.sleep(random.uniform(1.0, 3.0) * (idx % workers))`
- 将 `random_delay()` 的分布从均匀分布改为对数正态分布或 beta 分布
- 可选的 "慢启动" 模式：前几个任务间隔较大，后续在代理池容量范围内逐渐缩短

**Warning signs:**

- 日志中首批 worker 的 "Visit homepage" 时间戳在同一秒内
- 高并发时成功率明显低于低并发（排除资源瓶颈因素）
- 所有 worker 的步骤间延迟呈现相同的分布模式

**Phase to address:**
反机器人风险排查阶段 — 可独立于代理和邮箱拟人化实施

---

### Pitfall 7: 代理池耗尽与降级的灾难性后果

**What goes wrong:**
当代理池中的代理全部被活跃任务占用，或因连续失败全被标记为不可用时，后续任务无代理可用。三种灾难场景：(a) 所有任务挂起等待代理归还形成死锁；(b) 静默回退到无代理直连，暴露真实 IP；(c) 多个任务被迫复用同一代理，违反 per-task 绑定原则。

**Why it happens:**
代理池的并发安全设计比看起来复杂得多。需要考虑：借出/归还的原子性、任务异常退出时代理不被归还（泄漏）、失败代理的冷却期与重试窗口、池大小与 worker 数的动态约束。当前 `batch.py` 的 `_register_one()` 在 `finally` 块中清理 Mailcow 邮箱，但没有代理归还逻辑（因为当前只有单代理）— 引入代理池后必须加入类似的 finally 归还机制。

**How to avoid:**

- 启动时强制校验：`workers <= len(proxy_list)`，不满足则报错退出
- 在向导中校验：如果 `workers > len(proxy_list)`，提示用户降低并发数或增加代理
- 代理借出使用带超时的信号量或队列：等待超过 60 秒则任务标记为失败，而非无限等待
- 代理归还必须在 `finally` 块中执行，确保异常退出也能归还
- 归还时检查代理健康：如果该代理在使用期间出现连续注册失败，标记为冷却状态（30-60 秒后才能再次借出）
- **绝对禁止**无代理回退 — 宁可任务失败也不暴露真实 IP

**Warning signs:**

- 日志中出现长时间无输出（任务在等待代理分配）
- 部分任务日志显示代理地址为空但注册"成功"（直连）
- Dashboard 显示 worker 数远少于配置的并发数

**Phase to address:**
多代理调度阶段 — 池管理与借出/归还机制是该阶段的核心设计

---

### Pitfall 8: 邮箱 API 与注册流程使用同一代理产生关联

**What goes wrong:**
当前 `ChatGPTRegister._create_email_http_session()` 创建的邮箱 API session 使用与注册主流程相同的 `self.proxy`（代码行 130-131：`if self.proxy: session.proxies = {"http": self.proxy, "https": self.proxy}`）。这意味着同一个 IP 既在 `chatgpt.com` 注册账号，又在 `api.catchmail.io` 创建邮箱。如果 OpenAI 与临时邮箱服务商有数据共享（或 OpenAI 自行检测已知临时邮箱 API 的访问日志），相同 IP 的两个行为会被关联。

**Why it happens:**
`_create_email_http_session()` 在实现时直接复用 `self.proxy`。这在单代理场景下没有问题（反正只有一个 IP），但在多代理场景下，最佳实践是让邮箱 API 调用走独立的网络路径（直连或使用不同的代理），与注册流程的代理分离。

**How to avoid:**

- 邮箱 API 调用使用与注册流程**不同的**网络路径：直连（邮箱 API 通常不限制 IP）或使用专门的邮箱代理
- 在 `RegisterConfig` 中新增可选的 `email_proxy` 字段，默认为空（直连）
- 至少确保邮箱 API 代理和注册代理不是同一个 IP

**Warning signs:**

- 临时邮箱域名突然被 OpenAI 标记为高风险（拦截率上升）
- 邮箱创建成功但 OTP 邮件始终无法收到（被邮箱平台限速或封禁）

**Phase to address:**
多代理调度阶段 — 在设计代理分配策略时一并考虑邮箱 API 的网络路径

---

### Pitfall 9: 批次归档输出路径为相对路径导致文件写入位置错误

**What goes wrong:**
`RegConfig` 中的 `output_file`、`ak_file`、`rk_file`、`token_json_dir` 全部是裸字符串默认值（`"registered_accounts.txt"`、`"ak.txt"`、`"rk.txt"`、`"codex_tokens"`），代表相对于**进程当前工作目录**的路径。批次归档功能要在 `run_batch()` 开始时创建 `archives/YYYYMMDD_HHMM/` 目录，如果实现时只创建了目录但没有重写这 4 个路径字段，实际写入仍发生在当前工作目录，归档目录为空，日志显示"归档成功"但用户找不到文件。

**Why it happens:**
`run_batch()` 直接使用 `config.registration.output_file` 等字符串，没有 Path 规范化步骤。批次归档的新功能需要在任务开始前修改这些路径，但 `RegConfig` 是 Pydantic 模型，改字段值需要通过 `model_copy(update=...)` 或直接赋值。开发者容易创建了目录但忘记将所有 4 个输出路径重定向到新目录。

**How to avoid:**

- 批次归档功能在 `run_batch()` 入口处集中重写：生成归档目录路径 → 创建目录 → 创建 `config` 的副本（`config.model_copy(update={"registration": config.registration.model_copy(update={...})})`）并替换 4 个路径
- 以绝对路径形式重写所有输出路径，避免进程工作目录变化的影响
- 运行结束时明确打印归档目录的绝对路径作为验收信号

**Warning signs:**

- 运行后归档目录存在但为空
- `registered_accounts.txt`、`ak.txt`、`rk.txt` 出现在启动命令所在的工作目录而非归档目录
- `codex_tokens/` 子目录出现在工作目录根目录

**Phase to address:**
批次输出归档阶段 — 路径重写是该功能的第一步实现

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
| --- | --- | --- | --- |
| 名字池硬编码在 `utils.py` 中 | 实现简单、无外部依赖 | 更新名字库需要改代码 + 发版 | MVP 可以，v1.2 应外置为数据文件 |
| `random_delay()` 使用均匀分布 | 实现简单 | 均匀分布不像人类行为（真实用户更符合对数正态分布） | v1.1 反风控阶段应升级 |
| 代理列表只支持 TOML 配置静态定义 | 与现有 Profile 机制一致 | 无法运行时动态添加/移除代理 | CLI 工具场景可接受 |
| Sentinel SDK URL 版本号硬编码（`20260124ceb8`） | 快速匹配当前版本 | OpenAI 更新 SDK 版本后静默失效 | 需要监控机制或可配置化，不可长期接受 |
| 邮箱 API 和注册流程共用代理 | 无需额外配置字段 | 产生 IP 级关联信号 | v1.1 可接受（多数邮箱 API 无 IP 限制），v1.2 应分离 |
| `SentinelTokenGenerator` 默认 UA 硬编码（`Chrome/145.0.0.0`） | 开发时减少参数传递 | 与 `CHROME_PROFILES`（无 v145）永久不一致 | 永远不可接受，v1.1 应删除默认值或改为断言 |
| 批次归档目录路径在各调用点拼接 | 实现快速 | 多处拼接逻辑不一致导致文件散落 | 永远不可接受，归档路径必须单点生成 |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
| --- | --- | --- |
| 代理格式多样性 | 假设所有代理都是 `http://host:port` 格式 | 支持 `http://host:port`、`http://user:pass@host:port`、`socks5://user:pass@host:port` 等多种格式，用 URL 解析统一处理 |
| 代理健康检查 | 对代理发起到 `chatgpt.com` 的测试请求 | 健康检查只验证代理连通性（如访问 `httpbin.org/ip`），不访问目标站点 — 避免提前暴露意图 |
| `curl_cffi` impersonate + 自定义头 | 新增 Chrome 版本时 `impersonate` 值与 `sec_ch_ua` 不匹配 | `CHROME_PROFILES` 表中每一行的 impersonate、sec_ch_ua、major 必须严格一致，添加新版本时做交叉校验 |
| 批次归档目录 + 并发写入 | 多个 worker 各自用 `datetime.now()` 生成目录名导致写入不同目录 | 归档目录名必须在 `run_batch()` 开始时一次性生成，通过参数传递给所有 worker |
| 输出文件路径重定向 | 只重定向了 `registered_accounts.txt`，遗漏了 `ak.txt`、`rk.txt`、`codex_tokens/` | 所有输出路径（`output_file`、`ak_file`、`rk_file`、`token_json_dir`）必须统一重定向到归档目录 |
| 邮箱 API 限速 | 多个 worker 同时轮询同一邮箱平台的收件 API 触发限速 | 对邮箱 API 的轮询加全局速率限制（如每秒最多 2 次），或为不同 worker 的轮询间隔加入随机偏移 |
| 适配器拟人化改造范围 | 以为改 `random_name()` 就完成了拟人化，实际邮箱前缀仍是随机字符 | 拟人化必须同时改 `utils.py` 的名字生成逻辑 **和** 各适配器的 `create_temp_email()` 方法 |
| 多代理与 TOML Profile 向导集成 | 向导中只有单代理输入字段，多代理只能手动编辑 TOML | 向导增加"从文件导入代理列表"步骤（一行一个 URL），减少用户错误输入 |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
| --- | --- | --- | --- |
| 代理池太小导致 worker 排队 | worker 空闲等待代理，实际并发远低于配置 | 启动时动态调整：`actual_workers = min(workers, proxy_count)` | 代理数 < worker 数时 |
| 所有代理在同一 ASN/子网 | 初期正常，50+ 注册后全部被封 | 代理来源多样化（至少 3 个以上 ASN），文档中提醒用户 | 注册 50+ 账号后 |
| 名字池碰撞导致重复邮箱 | 邮箱创建 API 返回地址已存在错误 | 邮箱前缀加入足够随机性 + 适配器层做重试 | 名字池 < 1000 且批量 > 50 时 |
| Sentinel PoW 难度飙升 | token 生成从毫秒级升到秒级，阻塞 worker 线程 | 设置 PoW 计算超时（MAX_ATTEMPTS 上限），超时中止该任务 | 同一 IP 短时间多次请求后 |
| OTP 邮件等待超时堆积 | 多个 worker 同时轮询同一邮箱 API，超时后 worker 积压 | 邮箱 API 访问加全局限速锁，worker 的轮询间隔随机错开 | 并发 > 5 且使用同一邮箱平台时 |
| `_log_file_handle` 模块级全局残留 | 第二次调用 `run_batch()` 时日志写入旧文件句柄 | `run_batch()` 入口重置所有模块级全局变量，或改用 class 封装替代全局状态 | 在同一进程中多次调用 `run_batch()` 时 |

## Security Mistakes

| Mistake | Risk | Prevention |
| --- | --- | --- |
| 代理凭证明文存储在 TOML Profile 中 | 认证代理的用户名/密码泄露 | Profile 文件权限 600 + 文档提醒不要提交到版本控制 |
| 批次归档目录中明文存储账号密码 | `registered_accounts.txt` 含 ChatGPT 密码和邮箱密码 | 确保归档目录权限正确（700），可选提供输出脱敏模式 |
| 日志中打印完整 OAuth token | `_log()` 截取 response body 前 1000 字符可能包含 `access_token` | 对 `access_token`、`refresh_token` 字段做脱敏后再输出 |
| 代理健康检查暴露意图 | 对代理发起到目标站点的测试请求等于预告行为 | 健康检查使用中性目标（httpbin），不访问 chatgpt.com |
| 无代理静默回退到直连 | 暴露本机真实 IP | 代理获取失败时立即抛出异常终止任务，禁止回退 |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
| --- | --- | --- |
| 多代理配置需要手动输入每个代理地址 | 配置繁琐、易出错 | 支持从文件导入代理列表（一行一个 URL），向导只问代理文件路径 |
| 代理失败原因不透明 | 用户不知道是代理问题、邮箱问题还是注册流程问题 | Dashboard 中显示每个 worker 的代理地址和代理状态（正常/超时/被封） |
| 拟人化配置选项过多 | 用户不知道该调哪些参数 | 提供 "自动" 默认值（推荐配置），只有高级用户需要调整名字库、前缀模板等 |
| 批次归档目录不直觉 | 运行结束后用户找不到结果文件 | 运行结束时打印归档目录完整绝对路径 + Dashboard 中实时显示当前输出路径 |
| 代理池大小与并发数不匹配无提示 | 用户设了 10 并发但只有 2 个代理，实际效果远不如预期 | 在配置确认摘要和启动时明确提示有效并发数 |

## "Looks Done But Isn't" Checklist

- [ ] **邮箱拟人化（邮箱前缀）:** 只改了 `random_name()` ≠ 邮箱地址拟人化 — 验证：检查 `registered_accounts.txt` 中邮箱地址的 `@` 前部分是否包含人名格式，而非随机字母数字
- [ ] **邮箱拟人化（统计分布）:** 名字看起来真实 ≠ 分布统计真实 — 验证：生成 1000 个邮箱前缀，检查碰撞率 < 0.1%、格式种类 >= 5 种
- [ ] **代理轮换:** 代理正确分配 ≠ 代理正确归还 — 验证：注入 Exception 模拟任务异常退出，确认代理仍被归还到池中
- [ ] **批次归档（路径重定向）:** 归档目录创建成功 ≠ 所有输出文件都在正确目录 — 验证：确认 `ak.txt`、`rk.txt`、`codex_tokens/` 也在归档目录，不仅是 `registered_accounts.txt`
- [ ] **随机延迟:** 步骤间有延迟 ≠ 时序不可检测 — 验证：记录 100 次延迟值的分布图，确认不是均匀分布（应呈现偏态/长尾）
- [ ] **指纹一致性:** HTTP 头正确 ≠ Sentinel payload 一致 — 验证：抓包对比 HTTP 请求中的 UA/platform 与 sentinel token 解码后的对应字段
- [ ] **指纹一致性（Sentinel 默认 UA）:** `build_sentinel_token()` 显式传 UA ≠ 所有代码路径都安全 — 验证：确认 `SentinelTokenGenerator()` 不传 UA 时会报错而非使用错误默认值
- [ ] **代理池健康:** 代理 TCP 可连接 ≠ 代理未被目标站封禁 — 验证：健康检查应包含对目标站点返回 200 的判断（不仅是 TCP 握手成功）
- [ ] **并发安全:** 单线程测试通过 ≠ 多线程安全 — 验证：10 个 worker 同时借出/归还代理，无竞态、无泄漏
- [ ] **适配器覆盖:** 改了一个适配器 ≠ 改完所有适配器 — 验证：Catchmail、Maildrop、DuckMail、Mail.tm 的 `create_temp_email()` 全部产出人名格式前缀

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
| --- | --- | --- |
| 代理切换导致会话断裂 | LOW | 修改代理分配粒度为 per-task，无需改注册核心流程（`ChatGPTRegister` 已支持） |
| Sentinel 指纹不一致 | MEDIUM | 需要重构为统一 `BrowserProfile`，涉及 `http.py`、`register.py`、`sentinel.py` 三个模块 |
| Sentinel 默认 UA 版本矛盾 | LOW | 删除默认 UA 字符串，改为断言或从 `CHROME_PROFILES` 动态取最新版本 |
| 邮箱拟人化改错位置 | LOW | 在 `_register_one()` 中先生成名字，再传给适配器；或在适配器基类加 name_generator 钩子 |
| 邮箱名统计可检测 | LOW | 扩展名字库 + 多前缀模板是纯数据/生成逻辑变更，不影响核心流程 |
| 并发启动同步化 | LOW | 在 `run_batch()` 的 submit 循环中加延迟，约 10 行代码改动 |
| 代理池耗尽死锁 | MEDIUM | 需要引入带超时的信号量或队列，涉及 `run_batch()` 的并发编排模型 |
| 邮箱 API 与注册共用代理 | LOW | 在 `_create_email_http_session()` 中增加独立代理配置项 |
| 批次归档遗漏输出文件 | LOW | 统一输出路径生成逻辑，在 `run_batch()` 开始时确定所有路径并传递 |
| 批次归档相对路径写错位置 | LOW | 使用 `Path.cwd() / archive_dir` 生成绝对路径，替换 config 中所有输出路径 |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
| --- | --- | --- |
| 代理切换导致会话断裂 | 多代理调度 | 5 代理 x 10 账号并发测试，日志确认每个任务全程使用同一代理 IP |
| Sentinel 指纹不一致 | 反机器人排查 | 抓包解码 sentinel token payload，比对 HTTP 头中 UA/platform/chrome 版本 |
| Sentinel 默认 UA 版本矛盾 | 反机器人排查 | 单元测试：`SentinelTokenGenerator()` 不传 UA 时抛出 AssertionError |
| 邮箱拟人化改错位置（适配器层） | 邮箱名拟人化 | 检查注册后 `registered_accounts.txt` 中邮箱前缀格式，确认含人名而非随机字符 |
| 邮箱名统计可检测 | 邮箱名拟人化 | 生成 1000 个邮箱前缀：碰撞率 < 0.1%，格式模板 >= 5 种 |
| 并发启动同步化 | 反机器人排查 | 日志中 worker 启动时间间隔 >= 2 秒 |
| 代理池耗尽 | 多代理调度 | worker=10、proxy=3 场景：程序在启动前报错退出，不死锁 |
| 邮箱 API 代理关联 | 多代理调度 | 邮箱 API 和注册流程的出口 IP 不同（tcpdump 验证） |
| 批次归档路径遗漏 | 批次输出归档 | 运行后确认归档目录包含全部 4 类输出文件 |
| 批次归档相对路径错位 | 批次输出归档 | 在非项目根目录启动程序，确认归档文件出现在归档目录而非启动目录 |
| Sentinel SDK 版本过期 | 反机器人排查 | sentinel 端点异常响应时日志输出明确的版本不匹配警告 |

## Sources

- [Castle.io — 机器人注册攻击基础设施分析](https://blog.castle.io/inside-a-bot-operators-email-verification-infrastructure/) — 邮箱拟人化与检测信号 (MEDIUM)
- [plainproxies.com — 代理轮换与 ASN 多样性对检测的影响](https://plainproxies.com/blog/integrations/proxy-rotation-asn-diversity-ip-reputation-detection) — 代理池管理最佳实践 (MEDIUM)
- [IPinfo.io — 住宅代理共享基础设施与快速轮换](https://ipinfo.io/blog/residential-proxy-shared-infrastructure-churn) — 代理池 IP 复用风险 (MEDIUM)
- [joinmassive.com — 住宅代理池管理完整指南](https://www.joinmassive.com/blog/residential-proxy-pool-management) — 池大小与并发数关系 (MEDIUM)
- [curl_cffi 官方文档 — impersonate 使用指南](https://curl-cffi.readthedocs.io/en/v0.11.1/impersonate.html) — TLS 指纹限制 (HIGH)
- [brightdata.com — 2026 年 curl_cffi 爬虫实践](https://brightdata.com/blog/web-data/web-scraping-with-curl-cffi) — curl_cffi 局限性 (MEDIUM)
- [GitHub: openai-sentinel — Sentinel PoW token 逆向工程](https://github.com/leetanshaj/openai-sentinel) — Sentinel 机制参考 (MEDIUM)
- [alinr.com — ChatGPT Web HAR 架构分析](https://alinr.com/experiments/chatgpt-har-architecture-conversation-data.html) — Sentinel gating 架构 (MEDIUM)
- 代码审计：`chatgpt_register/core/register.py`、`core/http.py`、`core/sentinel.py`、`core/batch.py`、`core/utils.py`、`config/model.py`、`adapters/catchmail.py`、`adapters/maildrop.py` (HIGH)

---
*Pitfalls research for: ChatGPT 批量注册工具 v1.1 反风控增强*
*Researched: 2026-03-14*
