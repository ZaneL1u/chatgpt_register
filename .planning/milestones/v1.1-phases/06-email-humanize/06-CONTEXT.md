# Phase 6: 邮箱拟人化 - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## 阶段边界

注册时使用真实人名格式邮箱前缀（如 `emma.wilson92@catchmail.io`），替代当前随机字母数字字符串。通过配置开关控制，旧 profile 向下兼容。所有邮箱适配器统一改造。

</domain>

<decisions>
## 实现决策

### 人名库来源
- 使用 `faker` 库（`en_US` locale）实时调用 `fake.first_name()` + `fake.last_name()` 生成名字
- 备用方案：同时安装另一个命名库（如 `names`），faker 不可用时自动切换到备用库
- Faker 实例在调用时实时创建，不做预生成或缓存

### 前缀格式设计
- 4 种格式，均匀随机选取（各 25% 概率）：
  1. `firstname.lastname` — 如 `emma.wilson`
  2. `firstname_NNNN` — 如 `emma_1994`（NNNN = 1980-2006 完整年份）
  3. `firstnameNN` — 如 `emma94`（NN = 年份后 2 位，80-06）
  4. `f.lastname` — 如 `e.wilson`（首字母 + 姓氏）
- 所有名字和姓氏统一转为小写
- 不允许用户配置格式权重或禁用某种格式（纯开关控制）

### 唯一性保证机制
- 全局 `set` + `threading.Lock` 记录已用前缀
- 生成时检查是否在 set 中，冲突则无限重试直到生成唯一前缀
- set 生命周期：运行期内内存持有，运行结束后丢弃（不持久化到文件）
- 样本空间足够大（名字 × 姓氏 × 年份 × 4 种格式），冲突概率低

### 配置开关位置
- 新增字段 `email.humanize_email: bool`，放在 `EmailConfig` 顶层
- 默认值 `true`（开启拟人化）
- 纯布尔开关，不附带子配置项
- 旧 profile 不含此字段时，Pydantic 默认值生效（`true`），行为变为拟人化

### Claude's Discretion
- Faker 实例的具体初始化位置（基类 vs 工具函数）
- 备用命名库的具体选择
- 适配器改造的具体方式（基类统一 vs 各适配器分别修改）
- 唯一性 set 在对象层级中的挂载位置

</decisions>

<specifics>
## 具体想法

- 年份数字模拟真实用户出生年份（1980-2006），不是纯随机数字
- 4 种格式都是常见真实邮箱前缀风格，混合使用增加拟人化效果
- 默认开启拟人化（`true`），让新用户直接享受更好的反风控效果

</specifics>

<code_context>
## 现有代码洞察

### 可复用资产
- `EmailAdapter` 基类（`chatgpt_register/adapters/base.py`）：`create_temp_email()` 是核心入口，可在此层统一拦截
- 5 个适配器（catchmail、maildrop、duckmail、mailtm、mailcow）：各自覆盖 `create_temp_email()`
- `EmailConfig` Pydantic 模型（`chatgpt_register/config/model.py`）：新增 `humanize_email` 字段的目标位置

### 已建立模式
- 配置使用 Pydantic v2 `BaseModel`，带 `field_validator` 和 `model_validator`
- 适配器模式：基类定义接口，具体适配器继承实现
- 并发使用 `threading`，锁机制已有先例

### 集成点
- `EmailConfig` 模型需新增 `humanize_email: bool = True`
- 各适配器 `create_temp_email()` 需读取 `humanize_email` 配置决定前缀生成方式
- `pyproject.toml` 需新增 `faker` 依赖（+ 备用命名库）

</code_context>

<deferred>
## 延后想法

无——讨论全程保持在阶段范围内

</deferred>

---

*Phase: 06-email-humanize*
*Context gathered: 2026-03-14*
