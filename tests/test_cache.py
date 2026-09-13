from __future__ import annotations

import time

from dave.cache.store import CacheStore


def test_cache_round_trip(tmp_path):
    cache = CacheStore(tmp_path, ttl_seconds=60)
    key = CacheStore.make_key("https://example.com", "prompt")

    cache.set("extract", key, {"value": 42})

    assert cache.get("extract", key) == {"value": 42}


def test_cache_expiration(tmp_path):
    cache = CacheStore(tmp_path, ttl_seconds=1)
    key = CacheStore.make_key("x")
    cache.set("fetch", key, {"value": True}, ttl_seconds=1)
    time.sleep(1.1)

    assert cache.get("fetch", key) is None
