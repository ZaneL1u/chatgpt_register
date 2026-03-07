# 测试模式

**分析日期：** 2026-03-07

## 测试框架

**Runner：**
- 当前未配置测试框架
- 未发现 `pytest`、`unittest` 测试套件或 CI 测试流程

**断言库：**
- 当前仓库状态下没有专门的断言库配置

**可执行命令：**
```bash
# 当前没有已提交的自动化测试命令
uv run chatgpt-register --help   # 基本 CLI 烟雾检查
python codex/protocol_keygen.py  # 手动脚本执行，依赖本地配置与额外依赖
```

## 测试文件组织

**位置：**
- 仓库内没有 `tests/` 目录，也没有已提交测试文件

**命名：**
- 还没有测试文件命名约定

**当前结构：**
```text
当前仓库中与功能直接相关的核心文件：
chatgpt_register.py
codex/protocol_keygen.py
config.example.json
README.md
AGENTS.md
CLAUDE.md
```

## 测试组织方式

**套件结构：**
- 当前没有既定的 `describe`、测试类或测试函数组织模式

**现状特征：**
- 验证主要依赖人工执行
- README 中的命令示例和真实运行充当事实上的 smoke test
- 交互流程、多线程、真实网络调用让当前实现不易直接做隔离测试

## Mock 策略

**框架：**
- 未配置 mocking 框架

**当前状态：**
- 没有 HTTP stub、provider fake、IMAP fake、fixture 工厂
- 生产代码默认直接调用真实外部服务

**建议优先 mock：**
- OpenAI 注册 / OAuth 端点
- DuckMail / Mail.tm / Mailcow API 与 IMAP 行为
- CPA 与 Sub2API 上传接口
- 时间、随机值、文件写入，以便获得确定性测试

**不建议 mock：**
- 纯解析函数，如上传目标解析、OTP 提取、JWT payload 解码
- 配置合并逻辑，可通过临时文件和环境变量直接测试

## Fixtures 与工厂

**测试数据：**
- 当前无已提交 fixture
- 非常适合补充 provider 响应样本、OAuth redirect URL、token payload 样本

**建议位置：**
- `tests/fixtures/`：放接口响应与邮件内容样本
- `tests/factories/`：放配置对象、token 数据、provider 输入工厂

## 覆盖率

**要求：**
- 当前没有覆盖率目标，也没有门禁

**配置：**
- 没有覆盖率工具配置

**查看方式：**
```bash
# 需要先引入测试框架后才会有覆盖率命令
```

## 测试类型

**单元测试：**
- 当前缺失
- 第一优先级应覆盖 `_parse_upload_targets`、`_parse_int_list`、`_extract_verification_code`、`_decode_jwt_payload`、provider 配置校验函数

**集成测试：**
- 当前缺失
- 适合覆盖邮箱适配器、上传集成、批处理协调逻辑
- 需要 HTTP / IMAP mock，否则会非常脆弱

**端到端测试：**
- 当前没有
- 全真实注册流强依赖外部环境与目标站点策略，只适合受控环境下的人工或专用沙箱验证

## 常见测试关注点

**并发测试：**
- 当前没有既定模式
- `run_batch()`、共享文件写入锁、token 落盘路径都需要专门的并发安全验证

**错误路径测试：**
- 当前没有既定模式
- 高价值场景包括 provider 配置缺失、远程接口失败、OAuth 半成功半失败、上传目标未配置

**快照测试：**
- 当前不使用

**规划文档约束：**
- 由于仓库已要求 `.planning/` 默认输出中文，后续若补测试，也应覆盖语言配置读取与约束传播是否符合预期

---

*测试分析：2026-03-07*
*测试策略变化后更新*
