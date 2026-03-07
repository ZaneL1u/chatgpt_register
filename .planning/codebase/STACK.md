# 技术栈

**分析日期：** 2026-03-07

## 语言

**主要语言：**
- Python 3.10+：所有可执行应用代码，集中在 `chatgpt_register.py` 与 `codex/protocol_keygen.py`

**次要语言：**
- TOML：项目元数据与打包配置，位于 `pyproject.toml` 与 `.codex/config.toml`
- JSON：运行时配置与规划配置，位于 `config.example.json`、`.planning/config.json`
- Markdown：使用文档、GSD 工作流说明与仓库约束，位于 `README.md`、`codex/README.md`、`AGENTS.md`、`CLAUDE.md`、`.codex/`

## 运行环境

**环境要求：**
- CPython 3.10 或更高版本：由 `pyproject.toml` 明确要求
- 终端 / CLI 环境：主流程是命令行批处理脚本，不是 Web 服务
- 可用网络：依赖 OpenAI 认证接口、临时邮箱服务、CPA、Sub2API

**包管理：**
- `uv`：README 中推荐的依赖安装与运行方式
- setuptools：构建后端，配置为 `setuptools.build_meta`
- 锁文件：仓库包含 `uv.lock`

## 框架与工具

**核心：**
- 无框架：主程序是脚本式 Python CLI，核心入口为 `chatgpt_register.py`

**测试：**
- 未配置测试框架
- 仓库内未发现 `tests/` 目录、`pytest` 配置或 CI 测试流水线

**构建 / 开发：**
- setuptools 68+ / wheel：用于打包与 console script 生成
- `argparse`：CLI 参数解析，位于 `chatgpt_register.py`
- `ThreadPoolExecutor`：并发批量注册与协议工具的核心并发模型

## 关键依赖

**关键依赖：**
- `curl-cffi` 0.14.0：主注册流程的核心 HTTP 客户端，支持浏览器指纹伪装
- `questionary` 2.1.1：交互式 TUI 选择器，用于上传目标和分组选择
- `rich` 14.3.3：可选的运行时实时面板

**基础设施依赖：**
- Python 标准库 `imaplib` / `email`：Mailcow IMAP 轮询与邮件解析
- Python 标准库 `threading` / `concurrent.futures`：线程池、锁、并发文件写入保护
- `requests` 与 `urllib3`：被 `codex/protocol_keygen.py` 直接使用，但未在 `pyproject.toml` 中声明

## 配置方式

**运行时配置：**
- 主配置来源是与脚本同目录的 `config.json`
- 优先级为 `CLI 参数 > 环境变量 > config.json`
- 关键项包括邮箱提供者、OAuth 配置、代理、上传目标和上传凭证

**项目级配置：**
- `pyproject.toml`：包元数据、依赖、入口命令
- `.planning/config.json`：GSD 工作流配置，现已加入 `language.default = zh-CN` 与 `strict = true` 的语言约束语义
- `.codex/config.toml`：GSD Agent 配置，现已加入中文输出偏好声明
- `AGENTS.md` 与 `CLAUDE.md`：仓库级语言与行为约束文件

## 平台要求

**开发环境：**
- macOS / Linux / Windows 理论上都可运行，只要满足 Python 与网络条件
- Mailcow 模式要求 IMAP 可达
- 交互式路径要求真实 TTY 且已安装可选依赖

**生产 / 实际运行：**
- 没有部署到服务器的目标定义，这是一套本地执行的自动化 CLI
- 运行成功率主要受目标站点策略、代理质量、邮箱域信誉和外部接口稳定性影响

---

*技术栈分析：2026-03-07*
*在主要依赖或配置机制变化后更新*
