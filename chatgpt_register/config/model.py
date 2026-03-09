"""RegisterConfig Pydantic v2 数据模型及所有子模型。

覆盖 chatgpt_register.py:414-443 的全部 20+ 全局变量，
提供统一的配置数据结构、联动校验和中文错误消息。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


# ---------------------------------------------------------------------------
# 邮箱平台子模型
# ---------------------------------------------------------------------------


class DuckMailConfig(BaseModel):
    """DuckMail 临时邮箱配置"""

    api_base: str = "https://api.duckmail.sbs"
    bearer: str


class MailcowConfig(BaseModel):
    """Mailcow 自建邮箱配置"""

    api_url: str
    api_key: str
    domain: str = ""
    imap_host: str = ""
    imap_port: int = 993


class MailTmConfig(BaseModel):
    """Mail.tm 临时邮箱配置"""

    api_base: str = "https://api.mail.tm"


class CatchmailConfig(BaseModel):
    """Catchmail.io 免费临时邮箱配置"""

    api_base: str = "https://api.catchmail.io"
    domains: list[str] = Field(
        default_factory=lambda: [
            "catchmail.io",
            "catchmail.cc",
            "catchmail.com",
            "catchmail.net",
            "catchmail.org",
            "catchmail.co",
        ],
        description="可用域名列表（默认全选）",
    )


class MaildropConfig(BaseModel):
    """Maildrop.cc 免费临时邮箱配置"""

    api_base: str = "https://api.maildrop.cc/graphql"


# ---------------------------------------------------------------------------
# 邮箱配置（含平台联动校验）
# ---------------------------------------------------------------------------


class EmailConfig(BaseModel):
    """邮箱配置，包含 provider 与对应平台子模型的联动校验"""

    provider: Literal["duckmail", "mailcow", "mailtm", "catchmail", "maildrop"]
    duckmail: DuckMailConfig | None = None
    mailcow: MailcowConfig | None = None
    mailtm: MailTmConfig | None = None
    catchmail: CatchmailConfig | None = None
    maildrop: MaildropConfig | None = None

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def check_provider_config(self) -> EmailConfig:
        mapping = {
            "duckmail": self.duckmail,
            "mailcow": self.mailcow,
            "mailtm": self.mailtm,
            "catchmail": self.catchmail,
            "maildrop": self.maildrop,
        }
        if mapping.get(self.provider) is None:
            raise ValueError(
                f"选择了 {self.provider} 邮箱平台，"
                f"但未提供 [{self.provider}] 配置节"
            )
        return self


# ---------------------------------------------------------------------------
# OAuth 配置
# ---------------------------------------------------------------------------


class OAuthConfig(BaseModel):
    """OAuth 认证配置"""

    enabled: bool = True
    required: bool = True
    issuer: str = "https://auth.openai.com"
    client_id: str = "app_EMoamEEZ73f0CkXaXp7hrann"
    redirect_uri: str = "http://localhost:1455/auth/callback"


# ---------------------------------------------------------------------------
# 上传目标子模型
# ---------------------------------------------------------------------------


class CpaConfig(BaseModel):
    """CPA 上传配置"""

    api_url: str
    api_token: str


class Sub2ApiConfig(BaseModel):
    """Sub2API 上传配置"""

    api_base: str
    admin_api_key: str
    bearer_token: str
    group_ids: list[int] = Field(default_factory=list)
    account_concurrency: int = 1
    account_priority: int = 1


class UploadConfig(BaseModel):
    """上传配置，包含 targets 与对应子模型的联动校验"""

    targets: list[Literal["cpa", "sub2api"]] = Field(default_factory=list)
    cpa: CpaConfig | None = None
    sub2api: Sub2ApiConfig | None = None

    @model_validator(mode="after")
    def check_target_configs(self) -> UploadConfig:
        if "cpa" in self.targets and self.cpa is None:
            raise ValueError(
                "上传目标包含 cpa，但未提供 [upload.cpa] 配置节"
            )
        if "sub2api" in self.targets and self.sub2api is None:
            raise ValueError(
                "上传目标包含 sub2api，但未提供 [upload.sub2api] 配置节"
            )
        return self


# ---------------------------------------------------------------------------
# 注册参数配置
# ---------------------------------------------------------------------------


class RegConfig(BaseModel):
    """注册参数"""

    total_accounts: int = Field(default=5, ge=1, description="注册账号数量")
    workers: int = Field(default=3, ge=1, description="并发数")
    proxy: str = ""
    output_file: str = "registered_accounts.txt"
    ak_file: str = "ak.txt"
    rk_file: str = "rk.txt"
    token_json_dir: str = "codex_tokens"
    log_file: str = ""


# ---------------------------------------------------------------------------
# 顶层配置
# ---------------------------------------------------------------------------


class RegisterConfig(BaseModel):
    """顶层配置，TOML 文件的根结构。

    全局变量覆盖对照 (chatgpt_register.py:414-443):
      EMAIL_PROVIDER        -> email.provider
      DUCKMAIL_API_BASE     -> email.duckmail.api_base
      DUCKMAIL_BEARER       -> email.duckmail.bearer
      MAILCOW_API_URL       -> email.mailcow.api_url
      MAILCOW_API_KEY       -> email.mailcow.api_key
      MAILCOW_DOMAIN        -> email.mailcow.domain
      MAILCOW_IMAP_HOST     -> email.mailcow.imap_host
      MAILCOW_IMAP_PORT     -> email.mailcow.imap_port
      MAILTM_API_BASE       -> email.mailtm.api_base
      DEFAULT_TOTAL_ACCOUNTS-> registration.total_accounts
      DEFAULT_PROXY         -> registration.proxy
      DEFAULT_OUTPUT_FILE   -> registration.output_file
      ENABLE_OAUTH          -> oauth.enabled
      OAUTH_REQUIRED        -> oauth.required
      OAUTH_ISSUER          -> oauth.issuer
      OAUTH_CLIENT_ID       -> oauth.client_id
      OAUTH_REDIRECT_URI    -> oauth.redirect_uri
      AK_FILE               -> registration.ak_file
      RK_FILE               -> registration.rk_file
      TOKEN_JSON_DIR        -> registration.token_json_dir
      UPLOAD_TARGETS        -> upload.targets
      UPLOAD_API_URL        -> upload.cpa.api_url
      UPLOAD_API_TOKEN      -> upload.cpa.api_token
      SUB2API_API_BASE      -> upload.sub2api.api_base
      SUB2API_ADMIN_API_KEY -> upload.sub2api.admin_api_key
      SUB2API_BEARER_TOKEN  -> upload.sub2api.bearer_token
      SUB2API_GROUP_IDS     -> upload.sub2api.group_ids
      SUB2API_ACCOUNT_CONCURRENCY -> upload.sub2api.account_concurrency
      SUB2API_ACCOUNT_PRIORITY    -> upload.sub2api.account_priority
    """

    email: EmailConfig
    registration: RegConfig = Field(default_factory=RegConfig)
    oauth: OAuthConfig = Field(default_factory=OAuthConfig)
    upload: UploadConfig = Field(default_factory=UploadConfig)


# ---------------------------------------------------------------------------
# 错误格式化
# ---------------------------------------------------------------------------


def format_validation_errors(e: ValidationError) -> str:
    """将 Pydantic ValidationError 格式化为中文可读消息。"""
    messages = []
    for error in e.errors():
        loc = " -> ".join(str(part) for part in error["loc"])
        msg = error["msg"]
        messages.append(f"  配置项 [{loc}]: {msg}")
    return "配置校验失败:\n" + "\n".join(messages)
