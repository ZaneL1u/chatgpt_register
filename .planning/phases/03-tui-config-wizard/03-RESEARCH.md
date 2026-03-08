# Phase 3: TUI 配置向导 - 研究

**研究日期:** 2026-03-08
**领域:** Textual 多屏向导 + 条件表单 + TUI 测试
**置信度:** HIGH

<user_constraints>
## 用户约束 (来自 CONTEXT.md)

### 锁定决策
- 向导必须严格线性推进，只能从第一步开始逐步完成，不能跳步。
- 当前步骤只有在校验通过后才能进入下一步，不允许带错前进到最后统一检查。
- 不提供常规“上一步”返回能力。
- 用户中途退出时必须弹出一次确认，避免误退。
- 前面步骤一旦提交通过，就不再返回；最终摘要页是唯一允许回改配置的界面。
- 用户切换邮箱平台时，已填写过的其他平台配置保留在内存中；切回时恢复。
- 用户切换上传目标时，被隐藏的目标配置同样保留，不自动清空。
- 已填写但当前未选中的配置，最终仍应保留在 TOML 中。
- 条件字段尽量预填合理默认值；字段切换时应显示说明文字，而不是静默刷新。
- 字段在失焦时提示校验；点击“下一步”时再次统一校验当前页。
- 错误反馈需要两层：字段下方逐项提示 + 页面顶部错误汇总。
- Bearer token、API key 等敏感字段默认掩码显示，但允许用户手动切换可见。
- 数值类和地址类输入尽量做实时格式校验。
- 摘要页展开显示所有配置项，而不是只显示摘要。
- 摘要页敏感字段默认脱敏，但允许临时展开查看。
- 摘要页允许原地修改字段，并在修改时即时校验。
- 最终执行按钮不需要二次确认弹窗，文案倾向于“我已确认，立即执行”。

### 延迟事项
- profile 列表、profile 派生、`--profile` 启动路径属于 Phase 4。
- 完整移除 `config.json` 兼容层属于 Phase 4。
</user_constraints>

<phase_requirements>
## 阶段需求

| ID | 描述 | 研究支撑 |
|----|------|----------|
| TUI-01 | 通过 Select/RadioSet 选择邮箱平台 | `RadioSet` / `Select` 事件与条件切换模式 |
| TUI-02 | 邮箱平台条件联动展示字段 | `ContentSwitcher` + 持久化草稿状态 |
| TUI-03 | 敏感字段掩码输入 | `Input(password=True)` + 显隐切换 |
| TUI-04 | 多屏 Screen 向导 | `SCREENS` / `switch_screen` / `ModalScreen` |
| TUI-05 | 上传目标条件展开 | `Select` + `ContentSwitcher` |
| TUI-06 | 注册数量和并发数输入与验证 | `Input` validators + 配置模型扩展 |
| TUI-07 | 代理地址可选输入 + 格式验证 | `Input(validators=[URL(...)], valid_empty=True)` |
| CONF-04 | 确认摘要页确认后才开始执行 | 摘要页可编辑投影 + 最终 `build_config()` |
</phase_requirements>

## 概要

Phase 3 应直接采用 Textual 官方的 `Screen` / `ModalScreen` / `ContentSwitcher` / `Input` / `Select` / `RadioSet` 组合，不要再沿用 `questionary` 式一次一问的 CLI 交互。基于 PyPI，`textual` 最新稳定版在 2026-03-08 为 **7.5.0**，项目当前尚未引入该依赖，因此本阶段应显式新增并锁定 Textual 版本。

**核心建议：**

1. 用一个 `WizardApp` 持有唯一草稿状态，向导四步分别是独立 `Screen`。
2. 正常前进使用 `switch_screen`，退出确认单独用 `ModalScreen`。
3. 每个步骤内部的条件字段切换使用 `ContentSwitcher`，不要销毁未选中的子表单。
4. 字段层先用 Textual validators 做即时反馈，步进时再用 Pydantic 子模型/顶层模型做一次强校验。
5. 摘要页不要只是静态文本；应是“可编辑投影”，修改后直接回写草稿状态。
6. 先补齐 `RegConfig.workers`，再让 TUI 暴露并发输入；否则 TUI-06 无法闭环。

## Standard Stack

### 必选

| 组件 | 建议版本 | 用途 | 结论 |
|------|----------|------|------|
| `textual` | `>=7.5,<8` | TUI 应用、Screen、Widget、测试 API | 采用 |
| `textual-dev` | 与 `textual` 同主版本 | Devtools / 调试控制台 | 作为 dev 依赖采用 |
| `pydantic` | 保持现有 `>=2.12,<3` | 最终配置校验、摘要页提交校验 | 继续采用 |
| `pytest` | 保持现有 dev 依赖 | TUI 自动化测试 | 继续采用 |

### 继续复用的仓库资产

| 资产 | 位置 | 用途 |
|------|------|------|
| `RegisterConfig` | `chatgpt_register/config/model.py` | 向导最终产物 |
| `ProfileManager` | `chatgpt_register/config/profile.py` | Phase 4 持久化复用；本阶段只需保持输出结构兼容 |
| `run_batch(config)` | `chatgpt_register/core/batch.py` | 摘要页确认后的执行入口 |
| 旧 CLI 配置映射 | `chatgpt_register/cli.py` | 迁移期参考，不作为 TUI 内部状态来源 |

### 版本建议

- 以 2026-03-08 的 PyPI 为准，`textual` 最新稳定版是 7.5.0。
- 建议先锁到 `>=7.5,<8`，避免 Textual 8 的 API 变化打断 Phase 3/4。
- 如果团队更保守，可直接固定为 `textual==7.5.0`，待 Phase 4 完成后再升级。

## Architecture Patterns

### 模式 1: `WizardApp` + 已安装命名 Screen

**结论:** 用 `SCREENS` 或 `install_screen()` 预装 4 个步骤 Screen 和 1 个退出确认 `ModalScreen`。

**原因:**
- Textual 官方建议对“生命周期贯穿整个 app 的 screen”使用 `SCREENS`。
- 已安装 screen 会常驻内存，这正好满足“步骤间保留状态”“不允许回退但要保留已填数据”的要求。
- 正常步骤推进应使用 `switch_screen()`，因为它替换栈顶 screen，不会把向导做成可回退的堆栈。

**仓库落点:**
- 新子包：`chatgpt_register/tui/`
- 文件建议：
  - `chatgpt_register/tui/app.py`
  - `chatgpt_register/tui/state.py`
  - `chatgpt_register/tui/screens/email.py`
  - `chatgpt_register/tui/screens/registration.py`
  - `chatgpt_register/tui/screens/upload.py`
  - `chatgpt_register/tui/screens/summary.py`
  - `chatgpt_register/tui/screens/confirm_exit.py`

### 模式 2: 单一草稿状态，不直接把 Widget 当数据源

**结论:** App 层维护 `WizardState` / `RegisterConfigDraft`，Screen 只负责读写这份草稿。

**推荐结构:**

```python
@dataclass
class WizardState:
    email_provider: str = "mailtm"
    upload_mode: str = "none"
    draft_email: dict[str, dict] = field(default_factory=dict)
    draft_upload: dict[str, dict] = field(default_factory=dict)
    registration: dict[str, Any] = field(default_factory=dict)
    oauth: dict[str, Any] = field(default_factory=dict)
```

**原因:**
- 用户要求切换 provider / upload target 时保留隐藏字段；这要求状态脱离 widget 生命周期。
- 摘要页可编辑后还要即时回写，同样需要统一状态中心。
- `RegisterConfig` 当前是“最终合法配置”模型，不适合作为半填写草稿；草稿应宽松，提交时再 `build_config()`。

### 模式 3: 条件联动用 `ContentSwitcher`，不要频繁 mount/unmount

**结论:** 邮箱平台区和上传目标区都用 `ContentSwitcher.current = ...` 切换可见子表单。

**原因:**
- `ContentSwitcher` 专门用于在多个子 widget 间切换可见内容。
- child widget 需要唯一 ID，切换的是显示目标而不是销毁对象，这天然有利于保留输入值。
- 这比每次选择变化就重新 compose 一套 widget 更稳，也更容易测试。

**适用位置:**
- `EmailScreen`: `duckmail` / `mailcow` / `mailtm` 子表单
- `UploadScreen`: `none` / `cpa` / `sub2api` / `both` 子表单
- `SummaryScreen`: 可选地按分组切换编辑面板

### 模式 4: 两层验证回路

**结论:** 验证分成“字段层即时反馈”和“步骤层提交校验”。

**字段层:**
- `Input` 使用 `validators=[...]`
- `validate_on=["blur", "changed"]`
- 页面监听 `Input.Changed` / `Input.Blurred`，同步字段错误和顶部错误汇总

**步骤层:**
- 点击“下一步”时将当前 Screen 的数据片段灌入对应的 Pydantic 子模型
- 例如邮箱页构造 `EmailConfig`，注册参数页构造 `RegConfig`
- 摘要页最终用 `RegisterConfig.model_validate(...)` 作为总闸门

**原因:**
- Textual validators 擅长输入时机和单字段格式
- Pydantic 擅长跨字段与结构性约束
- 这两层结合后，既能满足“失焦提示”，又不会漏掉结构校验

### 模式 5: 摘要页做“可编辑投影”，不是跳回前页

**结论:** 摘要页应内嵌与前 3 步同源的字段组件或轻量编辑组件，直接修改 `WizardState`。

**不要这样做:**
- 摘要页放一堆文本，再提供“返回上一步”
- 为摘要页单独造第三套字段 schema

**推荐方式:**
- 摘要页按 4 个组展示：邮箱、注册参数、上传、OAuth
- 每组右侧放“编辑”开关，展开后显示内联控件
- 敏感字段默认脱敏，切换“显示”时只改该字段的 `Input.password`

## Don't Hand-Roll

| 问题 | 不要自己写 | 采用方案 | 原因 |
|------|-----------|----------|------|
| 多屏导航 | 自己维护页面栈和键盘路由 | Textual `Screen` / `switch_screen` / `ModalScreen` | 官方模型已覆盖 |
| 条件表单切换 | 每次选择变化后手动销毁重建 widget | `ContentSwitcher` | 状态保留、逻辑更简单 |
| 单字段校验 | 自己拼一套正则分发器 | `Input` validators + `validation_result` | 有现成事件和错误结构 |
| 数值/URL 校验 | 手写转换 + try/except | `Number` / `Integer` / `Regex` / `URL` / `Function` validators | 官方已提供 |
| 最终配置合法性 | 在 Screen 里散落 if/else | `RegisterConfig.model_validate()` | 与现有配置层统一 |
| 退出确认 | 在 App 内手搓“是否退出”状态机 | `ModalScreen` | 交互语义明确 |

**核心结论:** Phase 3 不应该发明“表单框架”或“状态机框架”；Textual 自己就已经提供了必须的 Screen、消息、验证和测试能力。

## Common Pitfalls

### 陷阱 1: 当前配置模型还没有并发数字段

**现状:** `chatgpt_register/config/model.py` 的 `RegConfig` 只有 `total_accounts`，没有 `workers`。  
**现状:** `chatgpt_register/core/batch.py` 把 `max_workers` 写死为 `3`。

**影响:** 不先补模型和执行层，TUI-06 的“并发数输入 + 验证”做出来也不会生效。

**结论:** Phase 3 计划必须先补 `registration.workers: int = Field(default=3, ge=1)`，并让 `run_batch()` 读取它。

### 陷阱 2: 用 `push_screen()` 做主流程会偷偷形成可回退堆栈

**问题:** 如果“邮箱 -> 注册参数 -> 上传 -> 摘要”都用 `push_screen()`，用户天然可以 `pop_screen()` 回去，这违背“不提供上一步返回”的约束。

**结论:** 主流程统一用 `switch_screen()`；只有退出确认弹窗使用 `push_screen()`。

### 陷阱 3: 退出弹窗重复 `push_screen()` 会堆叠多个确认框

Textual 官方示例明确指出，若每次按退出键都直接 `push_screen()`，会叠多个 modal。  
**结论:** 退出确认要么安装成命名 screen 并复用，要么在触发前检查当前栈顶是否已是该 modal。

### 陷阱 4: `Select` 默认允许空值

`Select.from_values()` 默认 `allow_blank=True`。  
**影响:** 邮箱平台或上传目标若忘记显式关闭，会出现“用户没真正选，但界面看起来像走通了”的状态。

**结论:** 对必选字段统一设 `allow_blank=False`。

### 陷阱 5: 只做 widget 级校验，遗漏结构级约束

**问题:** 单字段校验能保证 URL/数字格式，但保证不了“选了 duckmail 却没有 duckmail 子配置”“选了 sub2api 却缺少 bearer token”。

**结论:** 下一步按钮必须触发 Pydantic 子模型校验；摘要页执行前再跑顶层 `RegisterConfig` 校验。

### 陷阱 6: 切换 provider/target 时直接清空隐藏字段

**问题:** 这会直接违反上下文中的强约束，且会让摘要页与最终 TOML 无法还原用户先前输入。

**结论:** 隐藏不等于删除。未选中的配置段只是不显示，仍保留在 `WizardState`。

### 陷阱 7: 把摘要页做成纯文本，会逼着用户绕回前页

**问题:** 用户明确要求“只能在摘要页回改”。纯文本摘要会把这一要求打回到页面导航层，导致交互违约。

**结论:** 摘要页必须可编辑，且编辑后即时刷新顶部摘要和执行按钮可用状态。

### 陷阱 8: 不建立 TUI 自动化测试，后续重构必碎

**问题:** TUI 交互比普通函数更容易出现焦点、消息、条件渲染回归。

**结论:** Phase 3 从第一批屏幕开始就要上 `app.run_test()` / `pilot.click()` / `pilot.press()` 测试，而不是等 UI 完工再补。

## Code Examples

### 例 1: App 级 Screen 编排

```python
from textual.app import App

from chatgpt_register.tui.screens.email import EmailScreen
from chatgpt_register.tui.screens.registration import RegistrationScreen
from chatgpt_register.tui.screens.upload import UploadScreen
from chatgpt_register.tui.screens.summary import SummaryScreen


class WizardApp(App[RegisterConfig | None]):
    SCREENS = {
        "email": EmailScreen(),
        "registration": RegistrationScreen(),
        "upload": UploadScreen(),
        "summary": SummaryScreen(),
    }

    def on_mount(self) -> None:
        self.switch_screen("email")
```

### 例 2: `RadioSet` 驱动 `ContentSwitcher`

```python
from textual.containers import Container
from textual.widgets import ContentSwitcher, Input, RadioButton, RadioSet


class EmailScreen(Screen):
    def compose(self):
        yield RadioSet(
            RadioButton("DuckMail", id="duckmail"),
            RadioButton("Mailcow", id="mailcow"),
            RadioButton("Mail.tm", id="mailtm"),
            id="provider",
        )
        with ContentSwitcher(initial="mailtm", id="email-panels"):
            yield Container(Input(placeholder="DuckMail Bearer"), id="duckmail")
            yield Container(Input(placeholder="Mailcow API URL"), id="mailcow")
            yield Container(Input(placeholder="Mail.tm API Base"), id="mailtm")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        provider = event.pressed.id
        self.app.state.email_provider = provider
        self.query_one("#email-panels", ContentSwitcher).current = provider
```

### 例 3: 敏感字段与即时校验

```python
from textual.validation import Number, URL
from textual.widgets import Button, Input


token_input = Input(
    password=True,
    placeholder="Bearer token",
    validate_on=["blur", "changed"],
)

proxy_input = Input(
    type="text",
    placeholder="http://127.0.0.1:7890",
    validators=[URL()],
    valid_empty=True,
    validate_on=["blur", "changed"],
)

count_input = Input(
    placeholder="5",
    validators=[Number(minimum=1)],
    validate_on=["blur", "changed"],
)


def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "toggle-token":
        token = self.query_one("#token", Input)
        token.password = not token.password
```

### 例 4: Textual 自动化测试

```python
import pytest

from chatgpt_register.tui.app import WizardApp


@pytest.mark.asyncio
async def test_duckmail_switch_keeps_hidden_state():
    app = WizardApp()
    async with app.run_test() as pilot:
        await pilot.click("#provider")
        await pilot.press("down", "enter")
        await pilot.click("#duckmail-bearer")
        await pilot.press("a", "b", "c")
        await pilot.click("#provider")
        await pilot.press("down", "enter")
        await pilot.click("#provider")
        await pilot.press("up", "enter")
        assert app.state.draft_email["duckmail"]["bearer"] == "abc"
```

## 推荐字段与验证映射

| 向导字段 | 组件 | 即时验证 | 提交时验证 |
|---------|------|----------|-----------|
| 邮箱平台 | `RadioSet` | 必选事件驱动 | `EmailConfig` |
| DuckMail bearer | `Input(password=True)` | 非空 / 长度 | `DuckMailConfig` |
| Mailcow API URL | `Input` + `URL()` | URL | `MailcowConfig` |
| Mailcow IMAP 端口 | `Input` + `Number(minimum=1)` | 数值范围 | `MailcowConfig` |
| 注册数量 | `Input` + `Number(minimum=1)` | 正整数 | `RegConfig` |
| 并发数 | `Input` + `Number(minimum=1)` | 正整数 | `RegConfig` |
| 代理 | `Input` + `URL()` + `valid_empty=True` | URL 或空 | `RegConfig` |
| 上传目标 | `Select(..., allow_blank=False)` | 必选 | `UploadConfig` |
| CPA/Sub2API token | `Input(password=True)` | 非空 | `UploadConfig` |

## 测试策略

### 自动化重点

| 需求 | 测试断言 |
|------|----------|
| TUI-01 | `RadioSet`/`Select` 选择后草稿状态正确更新 |
| TUI-02 | 切换 provider 后只显示对应字段，切回时旧值仍在 |
| TUI-03 | 敏感字段默认掩码；点击显示按钮后切换为明文 |
| TUI-04 | 未通过校验无法进入下一屏；通过后 `switch_screen()` 到下一屏 |
| TUI-05 | 上传目标切换后条件区域变化，旧值不丢 |
| TUI-06 | 非法注册数/并发数阻止进入摘要页 |
| TUI-07 | 代理为空合法；非法 URL 显示错误 |
| CONF-04 | 摘要页编辑后状态变更；点击执行前必须通过顶层校验 |

### 建议命令

```bash
uv run pytest tests/ -q
```

新增 TUI 测试后可按模块拆分：

```bash
uv run pytest tests/test_tui_*.py -q
```

## 实施顺序建议

1. 新增 `textual` / `textual-dev` 依赖。
2. 扩展 `RegConfig` 与 `run_batch()`，补上 `workers`。
3. 建 `chatgpt_register/tui/` 基础结构与 `WizardState`。
4. 先做邮箱页 + 注册参数页，连通 Screen 切换和验证。
5. 再做上传页 + 摘要页编辑。
6. 最后接入 `cli.py`，让 TTY 场景能启动 TUI 并在确认后调用 `run_batch(config)`。

## 来源

### 官方来源
- Textual PyPI: https://pypi.org/project/textual/
- Textual Screens 指南: https://textual.textualize.io/guide/screens/
- Textual Select 文档: https://textual.textualize.io/widgets/select/
- Textual RadioSet 文档: https://textual.textualize.io/widgets/radioset/
- Textual Input 文档: https://textual.textualize.io/widgets/input/
- Textual ContentSwitcher 文档: https://textual.textualize.io/widgets/content_switcher/
- Textual Testing 指南: https://textual.textualize.io/guide/testing/
- Textual Validation API: https://textual.textualize.io/api/validation/

### 本地源码
- `chatgpt_register/config/model.py`
- `chatgpt_register/config/profile.py`
- `chatgpt_register/cli.py`
- `chatgpt_register/core/batch.py`
- `.planning/REQUIREMENTS.md`
- `.planning/phases/03-tui-config-wizard/03-CONTEXT.md`
- `.planning/STATE.md`
