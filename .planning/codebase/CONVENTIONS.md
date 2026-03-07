# 编码约定

**分析日期：** 2026-03-07

## 命名模式

**文件：**
- Python 模块使用 snake_case，如 `chatgpt_register.py`、`protocol_keygen.py`
- 约束与文档文件使用约定式大写名称，如 `README.md`、`AGENTS.md`、`CLAUDE.md`
- 运行产物使用语义化明文文件名，如 `registered_accounts.txt`、`ak.txt`、`rk.txt`

**函数：**
- 普通函数以 snake_case 为主
- 内部辅助函数大量使用前导下划线，例如 `_load_config()`、`_prepare_sub2api_group_binding()`
- 代码库主要是同步 + 线程模型，没有异步命名约定

**变量：**
- 局部变量使用 snake_case
- 配置加载后的模块级常量使用 UPPER_SNAKE_CASE，例如 `EMAIL_PROVIDER`、`UPLOAD_API_URL`
- HTTP 请求与响应临时变量偏好短名，如 `res`、`resp`、`data`

**类型 / 类：**
- 类名使用 PascalCase，例如 `RuntimeDashboard`、`EmailAdapter`、`ChatGPTRegister`、`ProtocolRegistrar`
- 类型标注只做了选择性使用，没有完整类型系统
- 未使用 dataclass、enum 或配置 schema 模型

## 代码风格

**格式：**
- 没有发现 formatter 配置
- 现有代码普遍采用 4 空格缩进
- 字符串以双引号为主，但风格并不完全统一
- 仓库接受“大文件 + 大函数”的脚本式风格
- 主程序中的注释和用户提示大量使用中文

**Lint：**
- 未发现 lint 配置或 lint 命令
- 风格一致性主要靠人工维护

## 导入组织

**顺序：**
1. Python 标准库
2. 第三方依赖
3. 可选第三方依赖（通常包在 `try/except` 中）

**分组：**
- 导入按大类分块，而非严格工具化排序
- `rich` 的导入使用 `try/except` 包裹，以便降级运行

**路径别名：**
- 无路径别名
- 全部采用直接模块导入

## 错误处理

**模式：**
- 外部 API、IMAP、文件与上传边界大量使用 `try/except Exception`
- 错误通常被转换成可供操作者理解的终端输出，而非自定义异常体系
- 许多帮助函数在失败时返回空列表、`None` 或 `False`，尤其在轮询与可选集成路径上

**错误语义：**
- 配置不完整、关键远程调用失败时倾向于抛异常
- 可恢复或可忽略场景倾向于返回哨兵值
- 日志通常会带上 provider、步骤名、状态码或上传目标信息

## 日志约定

**框架：**
- 默认使用 `print()`
- 在安装 `rich` 且运行于 TTY 时使用实时面板增强体验

**模式：**
- 进度日志常用 `[OAuth]`、`[CPA]`、`[Sub2API]`、worker 标签等前缀
- 日志直接嵌入控制流，没有独立 logger 封装
- 并发输出通过共享锁减少交错

## 注释与文档字符串

**何时注释：**
- 解释协议步骤、provider 行为、已知边界条件、操作提示
- `codex/protocol_keygen.py` 中大量使用区段分隔注释
- 越是逆向还原、越脆弱的流程，注释越多

**Docstring：**
- 许多函数和类有简短中文 docstring
- 顶层帮助函数和关键流程比微小内部函数更常带 docstring

**TODO：**
- 没有统一的 TODO 格式或 issue 关联约定

## 函数设计

**规模：**
- 当前代码库容忍大函数与超大模块
- 只有在重复逻辑明显时才会抽取，例如邮箱适配器类

**参数：**
- 原始值参数较多
- 可选行为经常通过布尔值或模块级全局变量控制

**返回值：**
- 风格混合：worker 返回 tuple，解析函数返回 dict，状态辅助函数返回 bool
- 常见写法是 guard clause 与 early return

## 模块设计

**导出：**
- 单文件可执行模块暴露一个主入口和大量内部辅助函数
- 没有显式公共 API 层

**Barrel / 聚合导出：**
- 不使用
- 如果代码继续增长，后续需要手动抽模块，而不是依赖现成目录边界

**仓库级约束：**
- 面向工具链的编码 / 输出约束不写在程序代码里，而写在 `AGENTS.md`、`CLAUDE.md`、`.planning/config.json`、`.codex/config.toml`
- 规划文档默认要求使用简体中文，这已经成为仓库约定的一部分

---

*约定分析：2026-03-07*
*风格或约束变化后更新*
