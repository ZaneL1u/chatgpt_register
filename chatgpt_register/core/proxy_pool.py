"""线程安全的代理池 — 按负载均衡分配代理给并发 worker。

每个 worker 启动时调用 acquire() 获取当前负载最小的代理，
任务完成或异常退出时调用 release() 释放。
worker 全程绑定同一代理，不在任务中途切换。
"""

from __future__ import annotations

import threading


class ProxyPool:
    """线程安全的代理池，按负载均衡分配代理。"""

    def __init__(self, proxies: list[str]) -> None:
        if not proxies:
            raise ValueError("代理列表不能为空")
        self._lock = threading.Lock()
        self._usage: dict[str, int] = {p: 0 for p in proxies}

    def acquire(self) -> str:
        """获取当前负载最小的代理，线程安全。"""
        with self._lock:
            proxy = min(self._usage, key=self._usage.get)  # type: ignore[arg-type]
            self._usage[proxy] += 1
            return proxy

    def release(self, proxy: str) -> None:
        """释放代理（worker 任务结束后调用）。"""
        with self._lock:
            if proxy in self._usage:
                self._usage[proxy] = max(0, self._usage[proxy] - 1)

    @property
    def snapshot(self) -> dict[str, int]:
        """Dashboard 展示用：返回当前各代理负载快照。"""
        with self._lock:
            return dict(self._usage)

    def __len__(self) -> int:
        return len(self._usage)
