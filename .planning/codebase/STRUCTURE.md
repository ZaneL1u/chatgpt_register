# 代码结构

**分析日期：** 2026-03-07

## 目录布局

```text
chatgpt_register/
├── .codex/                    # GSD workflow、agent、skill 与本地 Codex 配置
├── .planning/                 # GSD 生成的规划与代码地图
│   ├── codebase/              # 代码库映射文档
│   └── config.json            # GSD 项目配置，包含语言策略
├── codex/                     # 协议 key 生成工具与说明文档
├── chatgpt_register.egg-info/ # setuptools 生成的包元数据
├── AGENTS.md                  # 仓库级通用行为 / 语言约束
├── CLAUDE.md                  # GSD 子代理读取的项目级约束
├── chatgpt_register.py        # 主 CLI 实现
├── config.example.json        # 示例运行配置
├── pyproject.toml             # Python 包定义与入口命令
├── README.md                  # 用户说明文档
└── uv.lock                    # `uv` 锁文件
```

## 目录用途

**`.codex/`：**
- 目的：承载 GSD 自动化资源与 agent 配置
- 包含：`agents/`、`skills/`、`get-shit-done/`、`.codex/config.toml`
- 关键文件：`.codex/get-shit-done/workflows/map-codebase.md`、`.codex/skills/gsd-map-codebase/SKILL.md`
- 子目录：`agents/`、`skills/`、`get-shit-done/`

**`.planning/`：**
- 目的：保存 GSD 生成的项目状态与参考文档
- 包含：`.planning/codebase/*.md`、`.planning/config.json`
- 关键文件：`.planning/config.json` 中已记录中文优先输出策略
- 子目录：`codebase/`

**`codex/`：**
- 目的：保存独立的协议 key 生成工具
- 包含：`protocol_keygen.py`、`README.md`
- 关键文件：`codex/protocol_keygen.py`
- 子目录：无

**`chatgpt_register.egg-info/`：**
- 目的：本地构建 / 安装生成的包元数据
- 包含：依赖、入口点、源文件索引等信息
- 关键文件：`entry_points.txt`、`requires.txt`、`PKG-INFO`
- 子目录：无

## 关键文件位置

**入口点：**
- `chatgpt_register.py`：主程序入口与核心业务逻辑
- `codex/protocol_keygen.py`：独立工具入口

**配置：**
- `pyproject.toml`：包元数据、依赖、console script
- `config.example.json`：运行配置示例
- `.planning/config.json`：GSD 项目配置
- `.codex/config.toml`：GSD Agent 配置
- `.gitignore`：忽略本地 secret 与运行产物

**核心逻辑：**
- `chatgpt_register.py`：注册流程、邮箱适配器、OAuth、上传、运行面板
- `codex/protocol_keygen.py`：另一套纯 HTTP 协议流程

**测试：**
- 当前未发现 `tests/` 目录或测试文件

**文档：**
- `README.md`：主文档
- `codex/README.md`：协议工具文档
- `AGENTS.md`：通用行为 / 语言策略
- `CLAUDE.md`：项目级 GSD 指令
- `.planning/codebase/*.md`：代码地图参考文档

## 命名约定

**文件：**
- Python 模块使用 snake_case：`chatgpt_register.py`、`protocol_keygen.py`
- 核心说明文档使用约定式命名：`README.md`、`AGENTS.md`、`CLAUDE.md`
- 示例配置使用 `*.example.json`

**目录：**
- 目录大多使用小写：`codex/`、`.codex/`
- 点目录用于本地工具与规划状态

**特殊模式：**
- 主要可执行逻辑仍采用“单文件模块”而不是包化目录结构
- 项目约束通过根目录文档文件传递给工具链

## 新代码应放哪里

**新增注册功能：**
- 主实现：`chatgpt_register.py`
- 相关文档：`README.md`、`config.example.json`
- 如影响结构或约束：同步更新 `.planning/codebase/*.md`

**新增协议工具能力：**
- 实现：`codex/protocol_keygen.py`
- 文档：`codex/README.md`

**新增测试：**
- 建议新增顶层 `tests/` 目录
- 优先覆盖：配置解析、上传目标解析、OTP 提取、邮箱适配器

**新增仓库约束：**
- 面向 Codex / GSD 的行为约束：根目录 `AGENTS.md` 与 `CLAUDE.md`
- 面向 GSD 配置的默认值：`.planning/config.json` 与 `.codex/config.toml`

## 特殊目录

**`.planning/`：**
- 目的：GSD 生成产物目录
- 来源：工作流自动创建
- 是否提交：当前项目已经提交这类文档

**`chatgpt_register.egg-info/`：**
- 目的：打包元数据
- 来源：setuptools 生成
- 是否提交：当前仓库中已存在，但这类目录在很多项目里通常不会提交

---

*结构分析：2026-03-07*
*目录结构变化后更新*
