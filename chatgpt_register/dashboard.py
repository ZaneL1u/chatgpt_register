"""RuntimeDashboard — 基于 rich 的实时面板。"""

from __future__ import annotations

import builtins
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager

from chatgpt_register.core.utils import sanitize_status_text

try:
    from rich import box
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except Exception:
    RICH_AVAILABLE = False

_ORIGINAL_PRINT = builtins.print


def _truncate_proxy(proxy: str, max_len: int = 30) -> str:
    """脱敏截断代理地址用于 Dashboard 显示。"""
    if not proxy:
        return "直连"
    from urllib.parse import urlparse

    parsed = urlparse(proxy)
    if parsed.username:
        # 隐藏认证信息
        host_part = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
        display = f"{parsed.scheme}://***@{host_part}"
    else:
        display = proxy
    if len(display) > max_len:
        return display[:max_len] + "..."
    return display


class RuntimeDashboard:
    def __init__(self, total_accounts: int, max_workers: int, provider_name: str):
        self.total_accounts = max(1, int(total_accounts))
        self.max_workers = max(1, int(max_workers))
        self.provider_name = provider_name
        self.started_at = time.time()

        self.success_count = 0
        self.fail_count = 0
        self.worker_states: dict = {}
        self.logs: deque = deque(maxlen=400)

        self._lock = threading.RLock()
        self._last_refresh_at = 0.0
        self._live = None

    def start(self):
        if not RICH_AVAILABLE:
            return False
        with self._lock:
            self._live = Live(
                self._build_layout(),
                refresh_per_second=8,
                screen=True,
                transient=False,
            )
            self._live.start()
            self._refresh(force=True)
        return True

    def stop(self):
        with self._lock:
            if self._live:
                self._live.stop()
                self._live = None

    def register_worker(self, worker_id: int, tag: str = "", proxy: str = ""):
        with self._lock:
            item = self.worker_states.get(worker_id)
            if item is None:
                item = {
                    "tag": tag or f"任务-{worker_id}",
                    "status": "等待开始",
                    "done": False,
                    "result": "进行中",
                    "proxy": _truncate_proxy(proxy),
                }
                self.worker_states[worker_id] = item
            else:
                if tag:
                    item["tag"] = tag
                item["done"] = False
                item["result"] = "进行中"
                if proxy:
                    item["proxy"] = _truncate_proxy(proxy)
            self._refresh()

    def update_worker(self, worker_id: int, status: str, tag: str = ""):
        with self._lock:
            item = self.worker_states.get(worker_id)
            if item is None:
                self.worker_states[worker_id] = {
                    "tag": tag or f"任务-{worker_id}",
                    "status": sanitize_status_text(status),
                    "done": False,
                    "result": "进行中",
                }
            else:
                if tag:
                    item["tag"] = tag
                item["status"] = sanitize_status_text(status)
            self._refresh()

    def complete_worker(self, worker_id: int, ok: bool, status: str = ""):
        with self._lock:
            item = self.worker_states.get(worker_id)
            if item is None:
                item = {
                    "tag": f"任务-{worker_id}",
                    "status": "已完成",
                    "done": True,
                    "result": "成功" if ok else "失败",
                }
                self.worker_states[worker_id] = item
            else:
                item["done"] = True
                item["result"] = "成功" if ok else "失败"
                if status:
                    item["status"] = sanitize_status_text(status)
            self._refresh()

    def add_result(self, ok: bool):
        with self._lock:
            if ok:
                self.success_count += 1
            else:
                self.fail_count += 1
            self._refresh()

    def log(self, message: str):
        text = str(message or "")
        lines = text.splitlines() or [""]
        now_str = time.strftime("%H:%M:%S")
        with self._lock:
            for line in lines:
                self.logs.append(f"{now_str} {line}")
            self._refresh()

    def _render_progress_bar(self, width: int = 26):
        completed = self.success_count + self.fail_count
        ratio = min(1.0, max(0.0, completed / self.total_accounts))
        filled = int(width * ratio)
        return f"{'█' * filled}{'░' * (width - filled)}", ratio

    def _build_summary_panel(self):
        completed = self.success_count + self.fail_count
        elapsed = time.time() - self.started_at
        avg = elapsed / completed if completed else 0.0
        active_count = sum(1 for x in self.worker_states.values() if not x.get("done"))
        pending_count = max(0, self.total_accounts - completed - active_count)
        bar, ratio = self._render_progress_bar()

        rows = [
            f"邮箱提供者: {self.provider_name}",
            f"并发配置: {self.max_workers} | 活跃任务: {active_count}",
            f"成功/失败: {self.success_count}/{self.fail_count}",
            f"待开始任务: {pending_count}",
            f"平均耗时: {avg:.1f}s/个",
            f"总进度: {completed}/{self.total_accounts} ({ratio * 100:.1f}%)",
            f"[{bar}]",
        ]
        return Panel(Text("\n".join(rows), no_wrap=True), title="运行信息", border_style="green")

    def _build_workers_panel(self):
        table = Table(box=box.SIMPLE_HEAVY, expand=True, show_header=True)
        table.add_column("任务", no_wrap=True, width=12)
        table.add_column("代理", no_wrap=True, width=20)
        table.add_column("当前动作")
        table.add_column("结果", no_wrap=True, width=8, justify="center")

        items = sorted(
            self.worker_states.items(),
            key=lambda kv: (1 if kv[1].get("done") else 0, kv[0]),
        )
        if not items:
            table.add_row("-", "-", "等待任务启动", "-")
        else:
            display_items = items[:12]
            for worker_id, item in display_items:
                status = item.get("status") or "处理中"
                result = item.get("result") or "进行中"
                proxy_display = item.get("proxy") or "直连"
                style = "green" if result == "成功" else ("red" if result == "失败" else "yellow")
                tag = item.get("tag") or f"任务-{worker_id}"
                table.add_row(tag, proxy_display, status, f"[{style}]{result}[/{style}]")
        return Panel(table, title="并发任务状态", border_style="blue")

    def _build_logs_panel(self):
        lines = list(self.logs)[-50:]
        content = "\n".join(lines) if lines else "暂无执行日志"
        return Panel(Text(content), title="执行日志", border_style="cyan")

    def _build_layout(self):
        layout = Layout()
        layout.split_row(
            Layout(name="left", size=52),
            Layout(name="right"),
        )
        layout["left"].split_column(
            Layout(name="summary", size=11),
            Layout(name="workers"),
        )
        layout["left"]["summary"].update(self._build_summary_panel())
        layout["left"]["workers"].update(self._build_workers_panel())
        layout["right"].update(self._build_logs_panel())
        return layout

    def _refresh(self, force: bool = False):
        if not self._live:
            return
        now = time.time()
        if not force and now - self._last_refresh_at < 0.08:
            return
        self._live.update(self._build_layout(), refresh=True)
        self._last_refresh_at = now


@contextmanager
def route_print_to_dashboard(dashboard: RuntimeDashboard | None):
    """上下文管理器：将 builtins.print 重定向到 dashboard.log。"""
    if dashboard is None:
        yield
        return

    old_print = builtins.print

    def _dashboard_print(*args, **kwargs):
        target_file = kwargs.get("file")
        if target_file not in (None, sys.stdout, sys.stderr):
            return old_print(*args, **kwargs)
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        msg = sep.join(str(arg) for arg in args)
        if end and end != "\n":
            msg = f"{msg}{end.rstrip()}"
        dashboard.log(msg.rstrip("\n"))

    builtins.print = _dashboard_print
    try:
        yield
    finally:
        builtins.print = old_print
