# 路线图: ChatGPT Register TUI 化重构

## Milestones

- ✅ **v1.0 TUI 化重构 MVP** — Phases 1-5 (shipped 2026-03-08)
- 🚧 **v1.1 反风控增强** — Phases 6-9 (in progress)

## Phases

<details>
<summary>✅ v1.0 TUI 化重构 MVP (Phases 1-5) — SHIPPED 2026-03-08</summary>

- [x] Phase 1: 配置层基础 (2/2 plans) — completed 2026-03-08
- [x] Phase 2: 模块拆分 (2/2 plans) — completed 2026-03-07
- [x] Phase 3: TUI 配置向导 (2/2 plans) — completed 2026-03-08
- [x] Phase 4: CLI 集成与 Profile 管理 (3/3 plans) — completed 2026-03-08
- [x] Phase 5: Phase 4 验收闭环 (1/1 plan) — completed 2026-03-08

详见: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 反风控增强 (进行中)

**里程碑目标：** 提升批量注册的拟真度，通过邮箱名拟人化、多代理调度、批次归档、请求时序正态化四个维度降低被风控识别为机器人的概率

- [x] **Phase 6: 邮箱拟人化** — 配置模型扩展 + 邮箱前缀真人名生成，所有适配器改造
- [x] **Phase 7: 批次输出归档** — 按 `output/<YYYYMMDD_HHMM>/` 目录自动归档所有结果文件
- [x] **Phase 8: 多代理池调度** — proxies 多代理配置、round-robin 分配、向导多代理输入
- [x] **Phase 9: 反机器人加固** — 统一浏览器指纹、扩充 Chrome 版本池、正态延迟、stagger 启动

## Phase Details

### Phase 6: 邮箱拟人化

**Goal**: 注册时使用真实人名格式邮箱前缀（如 `emma.wilson92@catchmail.io`），并通过配置开关控制，旧 profile 无缝兼容

**Depends on**: Phase 5（v1.0 已完成）

**Requirements**: HUMAN-01, HUMAN-02, HUMAN-03, HUMAN-04

**Success Criteria** (what must be TRUE):

1. 开启 `humanize_email: true` 后，注册产生的邮箱地址 `@` 前含人名格式（firstname.lastname、firstname_NNNN 等），不再是乱码字符串
2. 同一批次中所有注册账号的邮箱前缀均不重复
3. 系统能生成至少 3 种不同格式的邮箱前缀（如 `firstname.lastname`、`firstname_NNNN`、`firstnameNN`）
4. 不设置 `humanize_email` 字段的旧 profile 加载后正常运行，行为与之前一致（默认关闭）

**Plans**: 3/3 complete

### Phase 7: 批次输出归档

**Goal**: 每次注册完成后，所有结果文件自动归档到带时间戳的独立目录，便于追踪和区分历史批次

**Depends on**: Phase 6

**Requirements**: BATCH-01

**Success Criteria** (what must be TRUE):

1. 注册完成后，`output/` 下自动生成 `YYYYMMDD_HHMM` 格式子目录
2. tokens、ak、rk、token json 全部写入该归档子目录，不再追加到同一文件
3. 多次运行产生多个独立归档目录，历史结果不被覆盖

**Plans**: 3/3 complete

### Phase 8: 多代理池调度

**Goal**: 用户能配置多个代理，并发 worker 自动按 round-robin 分配并全程绑定同一代理，向导支持便捷的多代理输入方式，旧 profile 自动兼容

**Depends on**: Phase 6（配置字段已扩展）

**Requirements**: PROXY-01, PROXY-02, PROXY-03, PROXY-04, PROXY-05, PROXY-06

**Success Criteria** (what must be TRUE):

1. 用户能在 profile 中配置 `proxies` 列表，支持 SOCKS5、SOCKS4、HTTP 混合格式
2. 并发运行时，每个 worker 绑定不同代理，且整个注册任务周期内不切换（可通过日志或 RuntimeDashboard 观察到不同 worker 使用不同代理 IP）
3. 含旧 `proxy` 单字段的 profile 加载后自动转换为 `proxies` 列表，无需用户手动修改
4. 向导中可逐行输入多个代理地址、从文件导入，也可只输入单个代理（向下兼容）

**Plans**: 3/3 complete

### Phase 9: 反机器人加固

**Goal**: 统一浏览器指纹来源、扩充 Chrome 版本覆盖范围、将请求延迟改为场景化正态分布、错开并发 worker 启动时间，全面降低注册流程的机器人行为特征

**Depends on**: Phase 8

**Requirements**: ANTI-01, ANTI-02, ANTI-03, ANTI-04, ANTI-05

**Success Criteria** (what must be TRUE):

1. `SentinelTokenGenerator` 不再使用硬编码默认 UA `Chrome/145.0.0.0`，UA 版本始终来自 `CHROME_PROFILES` 中实际存在的版本（可通过日志验证无版本矛盾）
2. `register.py` 和 `sentinel.py` 的浏览器标识属性来自同一 `BrowserProfile` 数据类，代码中不再有两处独立维护的浏览器信息
3. `CHROME_PROFILES` 包含 8-12 个不同 Chrome 版本，每次注册随机选取（可通过多次运行日志观察到版本多样性）
4. 注册过程中的请求延迟不再是均匀分布，OTP 等待等高延迟场景与普通步骤使用不同正态参数（可通过调试日志验证延迟分布形态）
5. 多 worker 并发启动时，各 worker 实际开始时间错开 2-8 秒，不再同步启动（可通过日志时间戳观察）

**Plans**: 3/3 complete

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
| ----- | --------- | -------------- | ------ | --------- |
| 1. 配置层基础 | v1.0 | 2/2 | Complete | 2026-03-08 |
| 2. 模块拆分 | v1.0 | 2/2 | Complete | 2026-03-07 |
| 3. TUI 配置向导 | v1.0 | 2/2 | Complete | 2026-03-08 |
| 4. CLI 集成与 Profile 管理 | v1.0 | 3/3 | Complete | 2026-03-08 |
| 5. Phase 4 验收闭环 | v1.0 | 1/1 | Complete | 2026-03-08 |
| 6. 邮箱拟人化 | v1.1 | 3/3 | Complete | 2026-03-15 |
| 7. 批次输出归档 | v1.1 | 3/3 | Complete | 2026-03-15 |
| 8. 多代理池调度 | v1.1 | 3/3 | Complete | 2026-03-15 |
| 9. 反机器人加固 | v1.1 | 3/3 | Complete | 2026-03-15 |
