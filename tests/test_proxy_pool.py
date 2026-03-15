"""tests/test_proxy_pool.py — ProxyPool 线程安全代理池测试。"""

from __future__ import annotations

import threading

import pytest

from chatgpt_register.core.proxy_pool import ProxyPool


class TestProxyPoolBasic:
    def test_acquire_returns_proxy(self):
        pool = ProxyPool(["http://a:80"])
        assert pool.acquire() == "http://a:80"

    def test_acquire_load_balance_two_proxies(self):
        pool = ProxyPool(["http://a:80", "http://b:80"])
        first = pool.acquire()
        second = pool.acquire()
        assert {first, second} == {"http://a:80", "http://b:80"}

    def test_acquire_reuse_when_fewer_proxies(self):
        pool = ProxyPool(["http://a:80"])
        p1 = pool.acquire()
        p2 = pool.acquire()
        assert p1 == p2 == "http://a:80"

    def test_release_decrements_usage(self):
        pool = ProxyPool(["http://a:80", "http://b:80"])
        p = pool.acquire()
        pool.release(p)
        snap = pool.snapshot
        assert snap[p] == 0

    def test_snapshot_reflects_usage(self):
        pool = ProxyPool(["http://a:80", "http://b:80"])
        pool.acquire()  # 获取负载最小的
        snap = pool.snapshot
        assert sum(snap.values()) == 1

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="代理列表不能为空"):
            ProxyPool([])

    def test_len(self):
        pool = ProxyPool(["http://a:80", "http://b:80", "http://c:80"])
        assert len(pool) == 3

    def test_release_unknown_proxy_no_error(self):
        pool = ProxyPool(["http://a:80"])
        pool.release("http://unknown:80")  # should not raise

    def test_release_below_zero_stays_zero(self):
        pool = ProxyPool(["http://a:80"])
        pool.release("http://a:80")
        assert pool.snapshot["http://a:80"] == 0

    def test_load_balance_three_proxies(self):
        """3 proxies, 6 acquires -> each should be used 2 times."""
        pool = ProxyPool(["http://a:80", "http://b:80", "http://c:80"])
        for _ in range(6):
            pool.acquire()
        snap = pool.snapshot
        assert all(v == 2 for v in snap.values())


class TestProxyPoolConcurrency:
    def test_concurrent_acquire(self):
        """10 threads acquire from 3 proxies — no errors, all get valid proxies."""
        proxies = ["http://a:80", "http://b:80", "http://c:80"]
        pool = ProxyPool(proxies)
        results = []
        errors = []
        barrier = threading.Barrier(10)

        def worker():
            try:
                barrier.wait(timeout=5)
                p = pool.acquire()
                results.append(p)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        assert len(results) == 10
        assert all(p in proxies for p in results)

    def test_concurrent_acquire_release(self):
        """Concurrent acquire + release leaves pool in consistent state."""
        proxies = ["http://a:80", "http://b:80"]
        pool = ProxyPool(proxies)
        barrier = threading.Barrier(20)

        def worker():
            barrier.wait(timeout=5)
            p = pool.acquire()
            # simulate some work
            pool.release(p)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        snap = pool.snapshot
        assert all(v == 0 for v in snap.values())
