"""批处理编排 — run_batch(config: RegisterConfig)。"""

from __future__ import annotations

import random
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from chatgpt_register.adapters.mailcow import MailcowAdapter
from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.core.archive import create_archive_dir, prepare_archive_paths
from chatgpt_register.core.proxy_pool import ProxyPool
from chatgpt_register.core.register import ChatGPTRegister
from chatgpt_register.core.utils import generate_password, provider_display_name, random_birthdate, random_name
from chatgpt_register.dashboard import RICH_AVAILABLE, RuntimeDashboard, route_print_to_dashboard

_print_lock = threading.Lock()
_file_lock = threading.Lock()
_log_lock = threading.Lock()
_log_file_handle = None


def _open_log_file(log_path: str):
    """打开日志文件，自动创建父目录。"""
    global _log_file_handle
    if not log_path:
        return
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    _log_file_handle = p.open("a", encoding="utf-8")


def _close_log_file():
    global _log_file_handle
    if _log_file_handle:
        _log_file_handle.close()
        _log_file_handle = None


def _log_write(msg: str):
    """线程安全地写一行到日志文件。"""
    if _log_file_handle:
        with _log_lock:
            _log_file_handle.write(msg + "\n")
            _log_file_handle.flush()


def _email_provider_endpoint_hint(config: RegisterConfig) -> str:
    provider = config.email.provider
    if provider == "duckmail" and config.email.duckmail:
        return config.email.duckmail.api_base
    if provider == "mailcow" and config.email.mailcow:
        return f"{config.email.mailcow.api_url} | 域名: {config.email.mailcow.domain}"
    if provider == "mailtm" and config.email.mailtm:
        return config.email.mailtm.api_base
    return ""


def _register_one(idx, total, config: RegisterConfig, output_file: str, print_lock, file_lock, dashboard=None, proxy_pool=None):
    reg = None
    mailcow_email = None
    proxy = None

    # 从代理池获取代理（如果有池），否则使用配置中的单代理
    if proxy_pool is not None:
        proxy = proxy_pool.acquire()
    else:
        proxy = config.registration.proxy or None

    if dashboard is not None:
        dashboard.register_worker(idx, tag=f"任务-{idx}", proxy=proxy or "")

    try:
        reg = ChatGPTRegister(
            config=config,
            proxy=proxy,
            tag=f"{idx}",
            worker_id=idx,
            dashboard=dashboard,
            print_lock=print_lock,
            file_lock=file_lock,
        )

        provider_name = provider_display_name(config.email.provider)
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
        # 释放代理回池（必须在 finally 中确保异常退出也释放）
        if proxy_pool is not None and proxy is not None:
            proxy_pool.release(proxy)

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
    import builtins

    # --- 归档目录：所有结果文件写入 output/YYYYMMDD_HHMM/ ---
    archive_dir = create_archive_dir()
    archive_paths = prepare_archive_paths(
        archive_dir,
        output_file=config.registration.output_file,
        ak_file=config.registration.ak_file,
        rk_file=config.registration.rk_file,
        token_json_dir=config.registration.token_json_dir,
        log_file=config.registration.log_file,
    )

    # 创建 config 副本，重定向输出路径到归档目录
    config = config.model_copy(deep=True)
    config.registration.output_file = archive_paths["output_file"]
    config.registration.ak_file = archive_paths["ak_file"]
    config.registration.rk_file = archive_paths["rk_file"]
    config.registration.token_json_dir = archive_paths["token_json_dir"]
    config.registration.log_file = archive_paths["log_file"]

    total_accounts = config.registration.total_accounts
    output_file = config.registration.output_file
    log_file = config.registration.log_file
    max_workers = config.registration.workers
    actual_workers = min(max_workers, total_accounts)
    provider_name = provider_display_name(config.email.provider)

    # 构建代理池
    effective_proxies = config.registration.proxies
    proxy_pool = ProxyPool(effective_proxies) if effective_proxies else None

    # 旧 proxy 单字段迁移提示
    if config.registration.proxy and not config.registration.proxies:
        # model_validator 已完成迁移，此处只打印提示
        print(f"[迁移] 旧 proxy 字段已自动转换为 proxies 列表，建议更新 profile 配置")
    elif proxy_pool is not None and config.registration.proxy and config.registration.proxies:
        # proxies 非空，proxy 字段被忽略
        print(f"[提示] 检测到 proxy 和 proxies 同时存在，已忽略旧 proxy 字段")

    # 设置日志文件
    if log_file:
        _open_log_file(log_file)
        _log_write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始批量注册")

    # 包装 print，同时写入日志文件
    original_print = builtins.print

    def _tee_print(*args, **kwargs):
        original_print(*args, **kwargs)
        if _log_file_handle:
            sep = kwargs.get("sep", " ")
            msg = sep.join(str(a) for a in args)
            _log_write(msg)

    if log_file:
        builtins.print = _tee_print

    dashboard = None
    if RICH_AVAILABLE and sys.stdin.isatty() and sys.stdout.isatty():
        dashboard = RuntimeDashboard(
            total_accounts=total_accounts,
            max_workers=actual_workers,
            provider_name=provider_name,
        )
        # 当 dashboard 启用时，print 会被重定向到 dashboard.log()
        # 需要额外 hook dashboard.log 来同时写入日志文件
        if log_file:
            _orig_dashboard_log = dashboard.log

            def _tee_dashboard_log(message: str):
                _orig_dashboard_log(message)
                _log_write(message)

            dashboard.log = _tee_dashboard_log
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
            print(f"  归档目录: {archive_dir}")
            if proxy_pool is not None:
                print(f"  代理池: {len(proxy_pool)} 个代理")
            elif config.registration.proxy:
                print(f"  代理: {config.registration.proxy}")
            else:
                print(f"  代理: 直连（未配置代理）")
            print(f"{'#'*60}\n")

            with ThreadPoolExecutor(max_workers=actual_workers) as executor:
                futures = {}
                for idx in range(1, total_accounts + 1):
                    future = executor.submit(
                        _register_one, idx, total_accounts, config, output_file, _print_lock, _file_lock, dashboard, proxy_pool
                    )
                    futures[future] = idx
                    # 错开启动：第一个立即启动，后续 worker 间隔 2-8s（正态分布）
                    if idx < total_accounts:
                        stagger = max(2.0, min(8.0, random.gauss(5.0, 1.5)))
                        print(f"  ◆ Worker {idx} 已提交，等待 {stagger:.1f}s 后提交下一个...")
                        time.sleep(stagger)

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
            print(f"  归档目录: {archive_dir}")
        print(f"{'#'*60}")

        if log_file:
            builtins.print = original_print
            _close_log_file()
            original_print(f"  日志已保存到: {log_file}")
