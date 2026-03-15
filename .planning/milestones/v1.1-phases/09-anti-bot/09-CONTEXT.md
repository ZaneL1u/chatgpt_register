# Phase 9：反机器人加固 - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## 阶段边界

统一浏览器指纹来源、扩充 Chrome 版本覆盖范围、将请求延迟改为场景化正态分布、错开并发 worker 启动时间，全面降低注册流程的机器人行为特征。

不涉及新功能开发，纯粹是对现有注册流程的反检测加固。

</domain>

<decisions>
## 实现决策

### 延迟分布策略
- 将 `random_delay()` 从 `random.uniform()` 均匀分布改为 `random.gauss()` 正态分布
- 按场景分三档延迟参数：
  - **普通步骤**（页面跳转、表单提交）：均值 0.5s，标准差 0.15s，下限 clamp 到 0.2s
  - **高延迟场景**（OTP 等待后的操作、重试）：均值 1.5s，标准差 0.4s，下限 clamp 到 0.5s
  - **微延迟**（连续 API 调用之间）：均值 0.3s，标准差 0.1s，下限 clamp 到 0.1s
- 在 `random_delay()` 函数签名中引入 `scenario` 参数或直接传 `(mean, std)` 参数对
- register.py 中约 12 处 `random_delay` 调用需逐一标注所属场景

### Chrome 版本池扩充
- `CHROME_PROFILES` 从 4 个扩充到 10 个左右
- 版本范围覆盖近 6-8 个月的 Chrome 稳定版，不要太旧（低于 Chrome 125 的不加）
- 每个 profile 需包含准确的 `sec_ch_ua`、`build`、`patch_range`、`impersonate` 值
- `impersonate` 值需与 curl_cffi 实际支持的版本对齐（不支持的版本用最接近的）

### BrowserProfile 统一
- 新建 `BrowserProfile` dataclass（或 NamedTuple），包含 `impersonate`、`chrome_major`、`chrome_full`、`user_agent`、`sec_ch_ua` 五个字段
- `random_chrome_version()` 返回 `BrowserProfile` 实例而非裸元组
- `SentinelTokenGenerator` 不再有硬编码默认 UA，构造时必须传入 `user_agent`（或接受 `BrowserProfile`）
- `sentinel.py` 的 `fetch_sentinel_challenge` 和 `build_sentinel_token` 统一从调用方获取浏览器信息，不在内部维护默认值

### Worker 启动错开
- `run_batch()` 中 worker 不再通过 `ThreadPoolExecutor` 同时提交所有任务
- 改为逐个提交，每提交一个 worker 后随机等待 2-8 秒（正态分布，均值 5s，标准差 1.5s，clamp 到 2-8s）
- 第一个 worker 立即启动，不等待

### Claude's Discretion
- 正态分布参数的具体数值微调
- `BrowserProfile` 放在 `http.py` 还是单独文件
- Chrome 版本数据的具体版本号选择（只要满足 8-12 个、覆盖近半年即可）
- worker 错开延迟的日志格式

</decisions>

<specifics>
## 具体想法

无特殊要求 — 按标准反检测实践来做即可。

</specifics>

<code_context>
## 现有代码洞察

### 可复用资产
- `random_chrome_version()` ([http.py:41-53](chatgpt_register/core/http.py#L41-L53))：现有版本选择函数，改造为返回 BrowserProfile
- `CHROME_PROFILES` ([http.py:17-38](chatgpt_register/core/http.py#L17-L38))：现有 4 版本字典列表，原地扩充
- `random_delay()` ([http.py:56-57](chatgpt_register/core/http.py#L56-L57))：现有延迟函数，改造签名

### 已有模式
- register.py 在 `__init__` 中调用 `random_chrome_version()` 获取指纹五元组
- sentinel.py 的 `fetch_sentinel_challenge` / `build_sentinel_token` 接受 `user_agent` 和 `sec_ch_ua` 参数（已有传参通道）
- 延迟调用散布在 register.py 的 `run_register` 方法中

### 集成点
- `ChatGPTRegister.__init__` ([register.py:61](chatgpt_register/core/register.py#L61))：浏览器信息消费入口
- `build_sentinel_token` 调用处 ([register.py:711](chatgpt_register/core/register.py#L711), [register.py:774](chatgpt_register/core/register.py#L774))：sentinel 浏览器信息传入
- `run_batch()` 的 ThreadPoolExecutor 循环 ([batch.py:269-275](chatgpt_register/core/batch.py#L269-L275))：worker 提交逻辑

</code_context>

<deferred>
## 延后想法

无 — 讨论保持在阶段范围内

</deferred>

---

*Phase: 09-anti-bot*
*Context gathered: 2026-03-15*
