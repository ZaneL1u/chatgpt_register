# Phase 8: 多代理池调度 - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

用户能配置多个代理，并发 worker 自动按动态负载均衡分配并全程绑定同一代理，向导支持便捷的多代理输入方式，旧 profile 自动兼容。不涉及代理健康监测、自动故障转移等高级代理管理功能。

</domain>

<decisions>
## Implementation Decisions

### 代理分配策略
- 采用动态负载均衡：每个 worker 启动时获取当前负载最小的代理
- 不限制同一代理的并发使用数（代理数少于 worker 数时自动复用）
- worker 全程绑定同一代理，中途代理失败不切换，直接报错
- RuntimeDashboard 显示每个 worker 当前绑定的代理 IP，方便观察负载分布

### 向导多代理输入
- 统一多行文本输入：支持直接粘贴多行代理地址，空行结束
- 文件路径自动识别：输入内容如果是 `.txt` 文件路径则自动读取文件内容
- 输入后显示解析摘要确认：「解析到 3 个 SOCKS5 + 1 个 HTTP 代理」
- 单/多自动切换：单个代理直接走单行输入（与现有体验一致），多个代理使用多行输入界面

### 旧配置迁移
- 双字段兼容：配置模型同时保留 `proxy`（单个，向下兼容）和 `proxies`（列表，新功能）
- `proxies` 优先：当 `proxies` 非空时使用 `proxies`，否则回退到 `proxy` 单字段
- 内存转换不写回：加载旧 profile 时在内存中将 `proxy` 转换为 `proxies` 列表，不修改原始 TOML 文件
- 日志提示：迁移时打印一行提示「已将 proxy 单字段自动转换为 proxies 列表」
- 新字段命名为 `proxies`，类型 `list[str]`，默认空列表

### 代理格式与校验
- 双模式向导：提供「直接输入完整地址」和「分步填写」（先选协议、再填 host:port、可选认证）两种模式
- 智能解析：支持 `socks5://user:pass@host:port`、`http://host:port`、`host:port`（默认 http）等格式
- 格式错误处理：警告并跳过无效行，继续使用其余合法代理
- 代理可用性校验：Claude's Discretion — 由实现阶段决定是否加入启动前连通性测试

### Claude's Discretion
- 代理可用性校验的具体实现方式（是否启动前 TCP 连通测试）
- ProxyPool 类的内部数据结构和线程安全实现
- 解析摘要的具体展示格式
- 分步填写模式的具体交互步骤

</decisions>

<specifics>
## Specific Ideas

- 用户希望向导体验流畅：单个代理时保持与现有完全一致的体验，多个代理时自然过渡到多行输入
- 文件导入场景：代理供应商通常提供 `.txt` 文件，每行一个代理地址，需要无缝支持
- Dashboard 代理显示：参考现有 worker 状态表，增加代理列，显示代理地址（脱敏或截断）

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RegConfig`（[model.py](chatgpt_register/config/model.py)）：现有 `proxy: str` 字段，需扩展为 `proxies: list[str]`
- `RuntimeDashboard`（[dashboard.py](chatgpt_register/dashboard.py)）：现有 worker 状态表，可扩展代理列
- `questionary` 向导框架（[wizard.py](chatgpt_register/wizard.py)）：现有单行代理输入，需改造为多行/多模式
- `ThreadPoolExecutor`（[batch.py](chatgpt_register/core/batch.py)）：现有线程池并发模型，代理分配逻辑需嵌入此处

### Established Patterns
- Pydantic v2 配置模型 + `model_validator` 联动校验
- `questionary` 交互式向导（select / text / confirm / checkbox）
- `threading.Lock` 线程安全模式
- `_register_one()` 中通过 `config.registration.proxy` 传递代理给 `ChatGPTRegister`

### Integration Points
- `_register_one()` 的 `proxy` 参数传递：需从 ProxyPool 获取而非直接读 config
- `ChatGPTRegister.__init__()` 的 `proxy` 参数：保持单个 proxy 字符串接口不变
- `_ask_registration_config()` 向导函数：需改造代理输入部分
- `ProfileManager.load()` / `.save()`：需处理新旧字段序列化

</code_context>

<deferred>
## Deferred Ideas

None — 讨论保持在 phase 范围内

</deferred>

---

*Phase: 08-proxy-pool*
*Context gathered: 2026-03-15*
