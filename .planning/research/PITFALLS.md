# 陷阱研究

**领域:** 为现有同步 Python CLI 工具集成 Textual TUI 配置向导 + TOML Profile 机制
**调研日期:** 2026-03-07
**置信度:** HIGH（大部分基于官方文档与代码库实际分析）

## 严重陷阱

### 陷阱 1: Textual 事件循环与现有同步注册流程的冲突

**出了什么问题：**
Textual 基于 `asyncio` 事件循环运行。当前 `chatgpt_register.py` 的核心注册流程（`run_batch` / `_register_one`）是纯同步代码，使用 `ThreadPoolExecutor` + `threading.Lock`。如果在 Textual App 内部直接调用这些同步函数，会阻塞事件循环，导致 TUI 完全冻结。

**为什么会犯这个错误：**
开发者倾向于在 TUI 向导收集完配置后直接调用 `run_batch()`，这在普通 CLI 脚本中完全正常，但在 Textual 的 async 上下文中会立即冻结界面。`@work` 装饰器看似能解决问题，但如果没有设置 `thread=True`，对普通同步函数会抛异常。

**如何避免：**
- TUI 向导与注册执行应严格分离为两个阶段：TUI 只负责收集配置并输出为 TOML，注册流程在 TUI 退出后以独立进程/上下文运行
- 如果确实需要在 TUI 内展示注册进度，使用 `@work(thread=True)` 将同步注册逻辑放入线程 worker，通过 `call_from_thread()` 或 `post_message()` 回传 UI 更新
- 绝不在 Textual 的 async handler 中调用 `time.sleep()`、`ThreadPoolExecutor.submit().result()` 等阻塞操作

**预警信号：**
- TUI 启动后界面无响应、无法接受键盘输入
- 按键事件堆积，退出后一次性输出
- 开发时 `textual console` 报 "event loop blocked" 警告

**应在哪个阶段解决：**
架构设计阶段 -- 在写第一行 TUI 代码之前就确定"TUI 只管配置收集，注册流程在 TUI 之外运行"的边界

---

### 陷阱 2: 全局可变状态阻碍模块拆分

**出了什么问题：**
当前代码在模块顶层执行 `_CONFIG = _load_config()` 并将结果展开为 20+ 个全局变量（`SUB2API_API_BASE`、`EMAIL_PROVIDER` 等）。这些全局变量在整个文件中被直接引用。引入 TUI 后，配置值在 import 时就已固化，TUI 收集到的新配置无法回写到这些全局变量，除非显式 `global` 赋值 -- 这极易出错且不可测试。

**为什么会犯这个错误：**
在单文件脚本中，模块级全局变量是最简单的共享状态方式。重构时容易忽视这些隐式依赖，以为只要改了 `_CONFIG` 字典就够了。

**如何避免：**
- 在拆分模块之前，先将所有全局配置变量收拢为一个不可变的配置数据类（`dataclass` 或 `pydantic.BaseModel`）
- 配置对象通过函数参数自顶向下传递，不依赖 import 时副作用
- TOML profile 加载后直接构造配置对象，老的 `config.json` + 环境变量路径作为可选兼容层保留到完全迁移完毕

**预警信号：**
- 单元测试中修改配置不生效，因为模块级变量在 import 时已固化
- TUI 选择的值与实际注册使用的值不一致
- `grep -c 'global ' chatgpt_register.py` 返回大量结果

**应在哪个阶段解决：**
模块拆分阶段 -- 这是拆分的前提条件，不解决这个问题就无法安全地将代码拆为多个模块

---

### 陷阱 3: 在 2000+ 行单文件上直接叠加 TUI 代码

**出了什么问题：**
在不先拆分模块的情况下，直接在 `chatgpt_register.py` 中添加 Textual App、Screen、Widget 类。文件膨胀到 3000+ 行，Textual 的 async 代码与现有同步代码混杂，import 循环、命名冲突、测试困难全部涌现。

**为什么会犯这个错误：**
"先加 TUI 功能，再慢慢重构"的想法很诱人。但 Textual 应用本身就需要定义多个类（App、Screen、Widget），每个类有自己的生命周期方法，与现有同步代码风格完全不同。

**如何避免：**
- 先拆分，后集成。在引入任何 TUI 代码之前，至少将以下模块独立出来：
  - `config.py` — 配置加载/合并/验证
  - `providers/` — 邮箱适配器
  - `core.py` — 注册流程编排
  - `upload.py` — 上传逻辑
- TUI 代码放在独立的 `tui/` 包中，只通过配置对象和注册入口函数与业务逻辑交互

**预警信号：**
- 单文件超过 2500 行且还在增长
- 修改 TUI 样式时不小心影响注册逻辑
- 无法独立运行 TUI 测试

**应在哪个阶段解决：**
第一阶段（模块拆分），必须在 TUI 开发之前完成

---

### 陷阱 4: Rich Live 面板与 Textual App 的终端控制权冲突

**出了什么问题：**
现有 `RuntimeDashboard` 使用 `rich.live.Live(screen=True)` 接管整个终端输出。Textual 运行时也会完全接管终端（stdin/stdout）。两者不能同时存在于同一进程中 -- 会导致终端渲染错乱、光标消失、输出混杂。

**为什么会犯这个错误：**
Rich 和 Textual 都来自 Textualize，开发者可能以为它们可以无缝共存。实际上 Textual 在运行时会替换 Rich 的 Console，两者的 screen 模式互斥。

**如何避免：**
- 方案 A（推荐）：TUI 向导结束后退出 Textual App，注册阶段继续使用现有 `RuntimeDashboard`（Rich Live），两者串行不并行
- 方案 B：将 `RuntimeDashboard` 改写为 Textual Widget，在 TUI 内展示注册进度。但这意味着注册流程必须以 Textual worker 方式运行，复杂度显著增加
- 绝不在同一时刻同时运行 `Live()` 和 `App.run()`

**预警信号：**
- 终端出现大量 ANSI 转义字符残留
- `print()` 输出被吞掉或出现在错误位置
- 程序退出后终端状态异常（需要 `reset` 命令恢复）

**应在哪个阶段解决：**
架构设计阶段 -- 必须在开始前决定 TUI 和 Dashboard 的共存模式

---

### 陷阱 5: TOML Profile 的 schema 设计不向前兼容

**出了什么问题：**
第一版 TOML profile schema 设计得过于松散（纯平铺 key-value）或过于紧耦合（一对一映射当前代码中的全局变量名），导致后续增加新邮箱 provider、新上传目标、新 OAuth 参数时必须修改 schema 或做复杂迁移。

**为什么会犯这个错误：**
直接将现有 `config.json` 的字典结构翻译成 TOML，没有考虑 TOML 的分层表（table）能力和未来扩展性。

**如何避免：**
- 使用 TOML 的嵌套 table 组织 provider 配置，而非平铺所有 key：
  ```toml
  [profile]
  name = "production"

  [email]
  provider = "duckmail"

  [email.duckmail]
  api_base = "https://api.duckmail.sbs"
  bearer = "xxx"

  [registration]
  total_accounts = 10
  enable_oauth = true

  [upload.cpa]
  api_url = "..."
  api_token = "..."
  ```
- 加入 `schema_version` 字段，便于未来做自动迁移
- 用 `pydantic` 或 `dataclass` 做 schema 校验，在加载时报明确错误而非静默使用默认值

**预警信号：**
- 不同 provider 的配置 key 需要前缀区分（`mailcow_api_url` vs `duckmail_api_base`）
- 添加新 provider 需要修改 10+ 处代码
- 用户手动编辑 TOML 时容易写错 key 名

**应在哪个阶段解决：**
配置层设计阶段 -- TOML schema 是整个 TUI 的基础，必须最先确定

---

## 中等陷阱

### 陷阱 6: questionary 与 Textual 的混合残留

**出了什么问题：**
现有代码依赖 `questionary` 做交互选择（`_prompt_upload_targets` 等函数）。重构时只替换了部分交互为 Textual，保留了 questionary 的调用路径，导致两种交互方式在不同场景下混用，用户体验割裂。

**如何避免：**
- 在引入 Textual 的同时列出所有 questionary 调用点，一次性规划替换
- 保留 `--non-interactive` 模式作为无 TUI 的降级路径（CI/CD 环境需要），但不保留 questionary 路径
- 完成迁移后从 `pyproject.toml` 中移除 questionary 依赖

**预警信号：**
- `grep questionary` 在 Textual 版本中仍有结果
- 部分配置走 TUI、部分弹出 questionary 纯文本选择
- CI 环境意外触发 TUI 或 questionary prompt

**应在哪个阶段解决：**
TUI 开发阶段 -- 与 Textual 向导开发同步完成

---

### 陷阱 7: TOML 的布尔值与环境变量的字符串类型不匹配

**出了什么问题：**
TOML 原生支持 `true`/`false` 布尔类型，但环境变量和旧 config.json 中 `"enable_oauth"` 的值可能是字符串 `"True"`、`"1"`、`"yes"`。`tomllib` 加载时类型是精确的，但合并环境变量覆盖时如果不做类型转换，会出现 `"true" != True` 的微妙 bug。

**如何避免：**
- 统一使用配置数据类作为类型守门人：所有来源（TOML、环境变量、CLI 参数）的值都经过同一个类型转换层
- 现有的 `_as_bool()` 函数方向正确，需要将其提升为配置层的统一入口而非散落在各处
- 为数值型配置（port、concurrency）同样做显式类型转换

**预警信号：**
- `if config["enable_oauth"]` 在 TOML 来源下为 `True`，在环境变量覆盖下为 `"true"`（字符串），行为不同
- 测试中硬编码布尔值通过，实际运行中环境变量覆盖不生效

**应在哪个阶段解决：**
配置层实现阶段

---

### 陷阱 8: Profile 存储路径的权限与跨平台问题

**出了什么问题：**
默认路径 `~/.chatgpt-register/profiles/` 在 macOS/Linux 下工作正常，但可能在以下场景出问题：
- 用户 HOME 目录不可写（某些容器/CI 环境）
- Windows 路径分隔符和 HOME 展开不一致
- 多个工具实例并发写同一 profile 文件

**如何避免：**
- 使用 `pathlib.Path.home()` 而非 `os.environ["HOME"]`
- 提供 `--config-dir` CLI 参数和 `CHATGPT_REGISTER_CONFIG_DIR` 环境变量作为覆盖
- Profile 写入使用原子写（写临时文件 + rename），避免写到一半被中断导致文件损坏
- 首次使用时检查目录权限并给出可操作的错误提示

**预警信号：**
- CI 环境中报 `PermissionError` 或 `FileNotFoundError`
- Windows 用户报路径问题
- 并发运行后 profile 文件内容截断

**应在哪个阶段解决：**
配置层实现阶段

---

### 陷阱 9: 敏感信息明文写入 TOML Profile

**出了什么问题：**
`bearer_token`、`api_key`、`admin_api_key` 等秘密值直接写入 TOML 文件。用户可能不小心将 `~/.chatgpt-register/profiles/` 目录提交到版本控制或分享给他人。

**如何避免：**
- 敏感字段支持环境变量引用语法：`bearer = "${DUCKMAIL_BEARER}"`，Profile 只存占位符
- 在 TOML 文件头部添加注释警告敏感信息
- 提供 `--show-secrets` / `--hide-secrets` 控制 TUI 确认摘要中是否显示完整密钥
- 考虑 `chmod 600` 自动设置文件权限（仅 Unix）

**预警信号：**
- `git diff` 中出现 API key
- 用户在 issue 中贴出带密钥的配置文件
- 文件权限为 644（所有人可读）

**应在哪个阶段解决：**
配置层实现阶段（schema 设计时就纳入考虑）

---

## 轻微陷阱

### 陷阱 10: Textual 测试模式被忽略

**出了什么问题：**
Textual 提供了 `App.run_test()` 用于自动化测试 TUI 行为（模拟按键、检查 widget 状态），但开发者跳过了 TUI 测试，只测试业务逻辑，导致 TUI 交互流程中的 bug 到手动测试才发现。

**如何避免：**
- 从第一个 Screen 开始就用 `async with app.run_test()` 编写 pilot 测试
- 至少覆盖：完整配置流程、Profile 加载、异常输入处理

**预警信号：**
- TUI 代码没有对应的 test 文件
- 每次修改 TUI 都需要手动跑一遍才放心

**应在哪个阶段解决：**
TUI 开发阶段 -- 与功能开发同步

---

### 陷阱 11: config.json 迁移没有过渡期

**出了什么问题：**
直接删除 config.json 支持，没有提供自动迁移工具。已有用户的配置丢失，需要从头在 TUI 中重新输入所有值。

**如何避免：**
- 实现一个 `migrate` 子命令：检测旧 config.json，自动转换为 TOML profile
- 首次启动时如果发现 config.json 存在且没有 TOML profile，自动提示迁移
- 迁移完成后将旧文件重命名为 `config.json.bak` 而非直接删除

**预警信号：**
- 用户升级后报"配置丢失"
- README 中的旧配置示例与新版本不兼容

**应在哪个阶段解决：**
配置迁移阶段 -- 在正式发布新版本之前

---

## 技术债模式

| 捷径 | 短期收益 | 长期代价 | 何时可接受 |
|------|---------|---------|-----------|
| 不拆模块直接加 TUI | 更快出原型 | 文件膨胀、测试困难、async/sync 混杂 | 永远不可接受 |
| TOML schema 不加版本号 | 少写几行代码 | 未来 schema 变更无法自动迁移 | 永远不可接受 |
| 保留 questionary 做降级 | 减少初期改动量 | 维护两套交互逻辑 | 仅在过渡期（不超过一个版本） |
| 敏感值直接写入 TOML | 实现简单 | 安全风险、用户信任 | 仅 MVP 阶段，正式版必须支持环境变量引用 |
| 跳过 Textual pilot 测试 | 开发速度快 | TUI 回归 bug 只能手动发现 | 仅原型阶段 |

## 集成相关陷阱

| 集成点 | 常见错误 | 正确做法 |
|--------|---------|---------|
| Textual + Rich Live | 同时运行导致终端冲突 | 串行执行：TUI 先退出，Rich Live 后启动 |
| Textual + ThreadPoolExecutor | 在 async handler 中调用 `.result()` 阻塞事件循环 | 使用 `@work(thread=True)` + `call_from_thread()` |
| TOML + 环境变量 | 类型不匹配（string vs bool/int） | 统一类型转换层 |
| Textual + CI/CD | CI 无终端导致 TUI 崩溃 | 检测 `sys.stdin.isatty()`，提供 `--non-interactive` 降级 |

## 性能陷阱

| 陷阱 | 症状 | 预防 | 何时触发 |
|------|------|------|---------|
| TUI 启动时加载所有 profile 文件 | 首次显示延迟 > 1s | 延迟加载，仅列出文件名 | profile 数超过 50 个 |
| Textual worker 中未检查 `is_cancelled` | 退出 TUI 后后台线程继续运行 | 长循环中轮询 `worker.is_cancelled` | 用户按 Ctrl+C 中途退出 |
| 配置验证在每次 widget 变化时触发 | TUI 输入卡顿 | debounce 验证或仅在提交时验证 | 复杂表单场景 |

## 安全风险

| 错误 | 风险 | 预防 |
|------|------|------|
| API key 明文存入 TOML | 泄露到版本控制或共享 | 支持 `${ENV_VAR}` 引用语法 |
| Profile 文件权限过宽 | 同机其他用户可读 | Unix 上自动 `chmod 600` |
| TUI 确认摘要显示完整密钥 | 肩窥或截图泄露 | 默认掩码，`--show-secrets` 才显示 |

## UX 陷阱

| 陷阱 | 用户影响 | 更好的做法 |
|------|---------|-----------|
| TUI 向导步骤过多 | 用户厌烦，放弃配置 | 合理分屏，相关选项放同一 Screen |
| 没有配置确认步骤 | 用户不确定将要执行什么 | 提交前展示配置摘要 |
| Profile 选择没有预览 | 用户不知道选的是哪套配置 | 选中 profile 时侧栏显示关键参数 |
| 报错信息只有 traceback | 普通用户看不懂 | 捕获并翻译为可操作的中文提示 |

## "看起来完成了但其实没有"检查清单

- [ ] **TUI 向导:** 常缺少边界输入处理（空字符串、超长值、特殊字符） -- 验证方式：用空值和极端值跑一遍完整流程
- [ ] **Profile 管理:** 常缺少删除和重命名功能 -- 验证方式：检查 CRUD 完整性
- [ ] **配置迁移:** 常缺少旧格式的 edge case 处理（如 config.json 中有非标准字段） -- 验证方式：用真实的旧 config.json 测试迁移
- [ ] **非交互模式:** 常缺少与 TUI 模式的行为一致性 -- 验证方式：同一配置在两种模式下产生相同结果
- [ ] **错误恢复:** TUI 崩溃后终端状态异常 -- 验证方式：在各步骤 Ctrl+C，检查终端是否正常恢复

## 恢复策略

| 陷阱 | 恢复代价 | 恢复步骤 |
|------|---------|---------|
| 全局状态未收拢就开始 TUI 开发 | HIGH | 停下来，先完成配置数据类重构，再继续 TUI |
| TOML schema 不兼容需要修改 | MEDIUM | 添加 schema_version，编写迁移脚本，bump 版本号 |
| Rich Live 与 Textual 冲突 | LOW | 改为串行执行模式，TUI 退出后再启动 Rich Dashboard |
| questionary 残留调用 | LOW | 全局搜索替换，移除依赖 |
| 敏感值已泄露到 TOML | HIGH | 轮换所有密钥，添加环境变量引用支持，通知用户 |

## 陷阱-阶段映射

| 陷阱 | 预防阶段 | 验证方式 |
|------|---------|---------|
| async/sync 事件循环冲突 | 架构设计 | TUI 和注册流程可独立运行，互不阻塞 |
| 全局可变状态 | 模块拆分 | `grep 'global ' *.py` 返回 0 结果，所有配置通过参数传递 |
| 单文件膨胀 | 模块拆分 | 最大单文件不超过 500 行 |
| Rich/Textual 终端冲突 | 架构设计 | 手动测试完整流程：TUI 配置 -> 确认 -> 注册 -> Dashboard |
| TOML schema 不兼容 | 配置层设计 | schema 包含 version 字段，有测试覆盖向后兼容 |
| questionary 残留 | TUI 开发 | `grep -r questionary` 在最终版中无结果 |
| 类型不匹配 | 配置层实现 | 环境变量覆盖的单元测试覆盖 bool/int/list 类型 |
| 路径权限问题 | 配置层实现 | CI 中测试无 HOME 和只读 HOME 场景 |
| 敏感信息泄露 | 配置层设计 | Profile 模板中敏感字段默认为环境变量引用 |
| 缺少 TUI 测试 | TUI 开发 | 每个 Screen 有对应的 pilot 测试 |
| 缺少迁移工具 | 发布前 | 旧 config.json 能自动转换为 TOML profile |

## 信息来源

- [Textual Workers 官方文档](https://textual.textualize.io/guide/workers/) -- async/sync 集成的权威指南 (HIGH)
- [Textual FAQ](https://textual.textualize.io/FAQ/) -- 常见问题汇总 (HIGH)
- [Textual GitHub Discussion #1828](https://github.com/Textualize/textual/discussions/1828) -- 在 Textual 中运行阻塞 API 的社区讨论 (MEDIUM)
- [Textual GitHub Discussion #4510](https://github.com/Textualize/textual/discussions/4510) -- 线程 worker 无法停止的问题 (MEDIUM)
- [Textual GitHub Issue #3472](https://github.com/Textualize/textual/issues/3472) -- 线程 worker 嵌套调用导致崩溃 (MEDIUM)
- [Real Python: Python and TOML](https://realpython.com/python-toml/) -- TOML 配置最佳实践 (MEDIUM)
- 项目代码库 `chatgpt_register.py` 实际分析 -- 全局状态、配置加载、线程模型 (HIGH)
- 项目 `.planning/codebase/CONCERNS.md` -- 已知技术债清单 (HIGH)

---
*陷阱研究: 为现有同步 CLI 集成 Textual TUI + TOML Profile*
*调研日期: 2026-03-07*
