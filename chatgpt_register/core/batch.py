"""批处理编排 — run_batch(config: RegisterConfig)。"""

from __future__ import annotations

import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from chatgpt_register.adapters.mailcow import MailcowAdapter
from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.core.register import ChatGPTRegister
from chatgpt_register.core.utils import generate_password, random_birthdate, random_name
from chatgpt_register.dashboard import RICH_AVAILABLE, RuntimeDashboard, route_print_to_dashboard

_print_lock = threading.Lock()
_file_lock = threading.Lock()


def _provider_label(provider: str) -> str:
    labels = {
        "duckmail": "DuckMail",
        "mailcow": "Mailcow",
        "mailtm": "Mail.tm",
    }
    return labels.get(provider, provider or "Unknown")


def _email_provider_endpoint_hint(config: RegisterConfig) -> str:
    provider = config.email.provider
    if provider == "duckmail" and config.email.duckmail:
        return config.email.duckmail.api_base
    if provider == "mailcow" and config.email.mailcow:
        return f"{config.email.mailcow.api_url} | 域名: {config.email.mailcow.domain}"
    if provider == "mailtm" and config.email.mailtm:
        return config.email.mailtm.api_base
    return ""


def _register_one(idx, total, config: RegisterConfig, output_file: str, print_lock, file_lock, dashboard=None):
    reg = None
    mailcow_email = None

    if dashboard is not None:
        dashboard.register_worker(idx, tag=f"任务-{idx}")

    try:
        reg = ChatGPTRegister(
            config=config,
            proxy=config.registration.proxy or None,
            tag=f"{idx}",
            worker_id=idx,
            dashboard=dashboard,
            print_lock=print_lock,
            file_lock=file_lock,
        )

        provider_name = _provider_label(config.email.provider)
        reg._print(f"[{provider_name}] 创建临时邮箱...")
        email, email_pwd, mail_token = reg.create_temp_email()
        tag = email.split("@")[0]
        reg.tag = tag
        if dashboard is not None:
            dashboard.update_worker(idx, "临时邮箱创建成功", tag=tag)

        if isinstance(reg.email_adapter, MailcowAdapter):
            mailcow_email = email

        chatgpt_password = generate_password()
        name = random_name()
        birthdate = random_birthdate()

        with print_lock:
            print(f"\n{'='*60}")
            print(f"  [{idx}/{total}] 注册: {email}")
            print(f"  ChatGPT密码: {chatgpt_password}")
            print(f"  邮箱密码: {email_pwd}")
            print(f"  姓名: {name} | 生日: {birthdate}")
            print(f"{'='*60}")

        reg.run_register(email, chatgpt_password, name, birthdate, mail_token)

        oauth_ok = True
        if config.oauth.enabled:
            reg._print("[OAuth] 开始获取 Codex Token...")
            tokens = reg.perform_codex_oauth_login_http(email, chatgpt_password, mail_token=mail_token)
            oauth_ok = bool(tokens and tokens.get("access_token"))
            if oauth_ok:
                reg.save_tokens(email, tokens)
                reg._print("[OAuth] Token 已保存")
            else:
                msg = "OAuth 获取失败"
                if config.oauth.required:
                    raise Exception(f"{msg}（oauth.required=true）")
                reg._print(f"[OAuth] {msg}（按配置继续）")

        with file_lock:
            with open(output_file, "a", encoding="utf-8") as out:
                out.write(f"{email}----{chatgpt_password}----{email_pwd}----oauth={'ok' if oauth_ok else 'fail'}\n")

        with print_lock:
            print(f"\n[OK] [{tag}] {email} 注册成功!")
        if dashboard is not None:
            dashboard.complete_worker(idx, True, status="注册成功")
        return True, email, None

    except Exception as e:
        error_msg = str(e)
        with print_lock:
            print(f"\n[FAIL] [{idx}] 注册失败: {error_msg}")
            print(traceback.format_exc())
        if dashboard is not None:
            dashboard.complete_worker(idx, False, status=f"失败: {error_msg}")
        return False, None, error_msg

    finally:
        if mailcow_email and reg is not None and isinstance(reg.email_adapter, MailcowAdapter):
            try:
                ok = reg.email_adapter.delete_mailbox(mailcow_email)
                if ok:
                    with print_lock:
                        print(f"  [Mailcow] 已清理临时邮箱: {mailcow_email}")
                else:
                    with print_lock:
                        print(f"  [Mailcow] 清理邮箱失败: {mailcow_email}（可手动删除）")
            except Exception:
                pass


def run_batch(config: RegisterConfig):
    """并发批量注册，接收 RegisterConfig 实例作为唯一配置入口。"""
    total_accounts = config.registration.total_accounts
    output_file = config.registration.output_file
    max_workers = config.registration.workers
    actual_workers = min(max_workers, total_accounts)
    provider_name = _provider_label(config.email.provider)

    dashboard = None
    if RICH_AVAILABLE and sys.stdin.isatty() and sys.stdout.isatty():
        dashboard = RuntimeDashboard(
            total_accounts=total_accounts,
            max_workers=actual_workers,
            provider_name=provider_name,
        )
        dashboard.start()
    elif not RICH_AVAILABLE:
        print("未安装 rich，已回退为普通日志输出。执行 `uv sync` 可启用实时面板。")

    success_count = 0
    fail_count = 0
    start_time = time.time()

    try:
        with route_print_to_dashboard(dashboard):
            print(f"\n{'#'*60}")
            print(f"  ChatGPT 批量自动注册 ({provider_name} 邮箱)")
            print(f"  注册数量: {total_accounts} | 并发数: {actual_workers}")
            print(f"  提供者配置: {_email_provider_endpoint_hint(config)}")
            print(f"  OAuth: {'开启' if config.oauth.enabled else '关闭'} | required: {'是' if config.oauth.required else '否'}")
            if config.oauth.enabled:
                print(f"  OAuth Issuer: {config.oauth.issuer}")
                print(f"  OAuth Client: {config.oauth.client_id}")
                print(f"  Token输出: {config.registration.token_json_dir}/, {config.registration.ak_file}, {config.registration.rk_file}")
            print(f"  输出文件: {output_file}")
            print(f"{'#'*60}\n")

            with ThreadPoolExecutor(max_workers=actual_workers) as executor:
                futures = {}
                for idx in range(1, total_accounts + 1):
                    future = executor.submit(
                        _register_one, idx, total_accounts, config, output_file, _print_lock, _file_lock, dashboard
                    )
                    futures[future] = idx

                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        ok, email, err = future.result()
                        if ok:
                            success_count += 1
                            if dashboard is not None:
                                dashboard.add_result(True)
                        else:
                            fail_count += 1
                            if dashboard is not None:
                                dashboard.add_result(False)
                            print(f"  [账号 {idx}] 失败: {err}")
                    except Exception as e:
                        fail_count += 1
                        if dashboard is not None:
                            dashboard.add_result(False)
                            dashboard.complete_worker(idx, False, status=f"线程异常: {e}")
                        with _print_lock:
                            print(f"[FAIL] 账号 {idx} 线程异常: {e}")
    finally:
        elapsed = time.time() - start_time
        avg = elapsed / total_accounts if total_accounts else 0
        if dashboard is not None:
            dashboard.stop()

        print(f"\n{'#'*60}")
        print(f"  注册完成! 耗时 {elapsed:.1f} 秒")
        print(f"  总数: {total_accounts} | 成功: {success_count} | 失败: {fail_count}")
        print(f"  平均速度: {avg:.1f} 秒/个")
        if success_count > 0:
            print(f"  结果文件: {output_file}")
        print(f"{'#'*60}")
