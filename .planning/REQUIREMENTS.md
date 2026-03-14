# 需求文档：ChatGPT Register v1.1 反风控增强

**定义日期：** 2026-03-14
**核心价值：** 用户通过交互式向导完成所有注册配置，无需手动编辑任何配置文件

## v1.1 需求

### HUMAN — 邮箱拟人化

- [ ] **HUMAN-01**：用户注册时使用真实人名+数字组合格式的邮箱前缀（如 `emma.wilson92@catchmail.io`），替代当前乱码前缀
- [ ] **HUMAN-02**：系统能从多种前缀模板中生成邮箱前缀（`firstname.lastname`、`firstname_NNNN`、`firstnameNN` 等至少 3 种）
- [ ] **HUMAN-03**：同一批次注册中，系统保证所有邮箱前缀不重复
- [ ] **HUMAN-04**：用户能通过 `humanize_email` 配置项开启/关闭拟人化功能，旧 profile 向下兼容（默认关闭）

### BATCH — 批次输出归档

- [ ] **BATCH-01**：注册完成后，所有结果文件（tokens、ak、rk、token json）自动写入 `output/<YYYYMMDD_HHMM>/` 归档目录

### PROXY — 多代理调度

- [ ] **PROXY-01**：用户能在配置中指定多个代理地址（新增 `proxies: list[str]` 字段）
- [ ] **PROXY-02**：`proxies` 字段支持 SOCKS5、SOCKS4、HTTP 混合格式（`socks5://user:pass@host:port`）
- [ ] **PROXY-03**：系统以 round-robin 策略将代理分配给并发 worker
- [ ] **PROXY-04**：同一 worker 在整个注册任务周期内绑定同一代理，不在任务中途切换
- [ ] **PROXY-05**：旧 `proxy` 单字段 profile 能自动迁移到新 `proxies` 列表，无需用户修改
- [ ] **PROXY-06**：向导支持多代理输入（逐行输入 / 从文件导入 / 单代理向下兼容）

### ANTI — 反机器人加固

- [ ] **ANTI-01**：修复 `SentinelTokenGenerator` 默认 UA `Chrome/145.0.0.0` 与 `CHROME_PROFILES` 不一致的潜伏 bug
- [ ] **ANTI-02**：统一 `BrowserProfile` 数据类，`register.py` 和 `sentinel.py` 均从同一数据源读取浏览器标识，消除两处独立维护
- [ ] **ANTI-03**：`CHROME_PROFILES` 扩充到 8-12 个 Chrome 版本，每次注册随机选取
- [ ] **ANTI-04**：请求延迟从均匀分布 `U(0.3, 0.8)` 改为场景化正态分布（`random.gauss()`），OTP 等待等高延迟场景单独调参
- [ ] **ANTI-05**：`run_batch()` 中并发 worker 启动引入 2-8s 随机错开延迟，避免所有 worker 同步启动

## v1.2 需求（延后）

### PROXY — 高级调度

- **PROXY-ADV-01**：代理-浏览器指纹绑定（同一代理固定同一 Chrome profile）
- **PROXY-ADV-02**：代理健康检测与自动剔除（基于生产数据反馈）

### BATCH — 高级归档

- **BATCH-ADV-01**：`organize_by_batch` 开关（目前固定开启）
- **BATCH-ADV-02**：批次统计报告（每代理成功率等）
- **BATCH-ADV-03**：注册结果 JSON 归档（结构化归档）

## Out of Scope

| 功能 | 原因 |
|------|------|
| macOS/Linux UA 多样化 | 需验证 curl-cffi impersonate 与非 Windows TLS 指纹一致性，v2+ |
| 代理自采购/代理池管理服务 | 超出 CLI 工具范畴 |
| CAPTCHA 解决 | 当前注册流程使用 Sentinel PoW，无图形验证码 |
| 浏览器自动化（Playwright/Selenium） | 依赖重、速度慢，与现有纯协议方案冲突 |
| 自适应并发限速 | 需积累足够成功/失败数据才能设计反馈控制器，v2+ |

## 需求追踪

路线图创建后填充。

| 需求 | 阶段 | 状态 |
|------|------|------|
| HUMAN-01 | — | 待定 |
| HUMAN-02 | — | 待定 |
| HUMAN-03 | — | 待定 |
| HUMAN-04 | — | 待定 |
| BATCH-01 | — | 待定 |
| PROXY-01 | — | 待定 |
| PROXY-02 | — | 待定 |
| PROXY-03 | — | 待定 |
| PROXY-04 | — | 待定 |
| PROXY-05 | — | 待定 |
| PROXY-06 | — | 待定 |
| ANTI-01 | — | 待定 |
| ANTI-02 | — | 待定 |
| ANTI-03 | — | 待定 |
| ANTI-04 | — | 待定 |
| ANTI-05 | — | 待定 |

**覆盖情况：**
- v1.1 需求：15 个
- 已映射到阶段：0
- 未映射：15 个 ⚠️

---
*需求定义日期：2026-03-14*
*最后更新：2026-03-14 — v1.1 初始定义*
