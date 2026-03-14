"""邮箱适配器子包 — 提供 build_email_adapter 工厂函数。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatgpt_register.adapters.base import EmailAdapter
    from chatgpt_register.config.model import RegisterConfig


def build_email_adapter(register, config: RegisterConfig) -> EmailAdapter:
    """根据 config.email.provider 创建对应的邮箱适配器实例。"""
    provider = config.email.provider

    if provider == "duckmail":
        from chatgpt_register.adapters.duckmail import DuckMailAdapter
        if config.email.duckmail is None:
            raise Exception("email_provider=duckmail 但未设置 duckmail 配置节")
        return DuckMailAdapter(register, config.email.duckmail)

    if provider == "mailcow":
        from chatgpt_register.adapters.mailcow import MailcowAdapter
        if config.email.mailcow is None:
            raise Exception("email_provider=mailcow 但未设置 mailcow 配置节")
        return MailcowAdapter(register, config.email.mailcow)

    if provider == "mailtm":
        from chatgpt_register.adapters.mailtm import MailTmAdapter
        if config.email.mailtm is None:
            raise Exception("email_provider=mailtm 但未设置 mailtm 配置节")
        return MailTmAdapter(register, config.email.mailtm)

    if provider == "catchmail":
        from chatgpt_register.adapters.catchmail import CatchmailAdapter
        if config.email.catchmail is None:
            raise Exception("email_provider=catchmail 但未设置 catchmail 配置节")
        return CatchmailAdapter(register, config.email.catchmail, humanize_email=config.email.humanize_email)

    if provider == "maildrop":
        from chatgpt_register.adapters.maildrop import MaildropAdapter
        if config.email.maildrop is None:
            raise Exception("email_provider=maildrop 但未设置 maildrop 配置节")
        return MaildropAdapter(register, config.email.maildrop, humanize_email=config.email.humanize_email)

    raise Exception(f"未知邮箱提供者: {provider}，仅支持: duckmail / mailcow / mailtm / catchmail / maildrop")
