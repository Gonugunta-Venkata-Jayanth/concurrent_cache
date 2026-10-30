import random
import threading

import pytest

from cache.cache import ThreadSafeCache
from cache.lfu_policy import LFUEvictionPolicy
from cache.lru_policy import LRUEvictionPolicy

POLICIES = [LRUEvictionPolicy, LFUEvictionPolicy]


# ------------------------------------------------------------------ basics
@pytest.mark.parametrize("policy", POLICIES)
def test_put_get_update_remove(policy):
    cache = ThreadSafeCache(2, policy())
    assert cache.get("missing") is None
    assert cache.get("missing", "dflt") == "dflt"
    cache.put("a", 1)
    cache.put("a", 2)  # overwrite must not grow the cache
    assert cache.get("a") == 2 and len(cache) == 1
    cache.remove("a")
    assert "a" not in cache and len(cache) == 0
    assert len(cache.eviction_policy) == 0
    cache.remove("a")  # removing twice is a no-op


@pytest.mark.parametrize("policy", POLICIES)
def test_capacity_is_never_exceeded(policy):
    cache = ThreadSafeCache(3, policy())
    for i in range(50):
        cache.put(i, i)
        assert len(cache) <= 3
    assert len(cache.eviction_policy) == len(cache)


def test_invalid_capacity():
    with pytest.raises(ValueError):
        ThreadSafeCache(0, LRUEvictionPolicy())


# --------------------------------------------------------------------- LRU
def test_lru_evicts_least_recently_used():
    cache = ThreadSafeCache(2, LRUEvictionPolicy())
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1  # "a" is now most recent
    cache.put("c", 3)           # evicts "b"
    assert cache.get("b") is None
    assert cache.get("a") == 1 and cache.get("c") == 3


def test_lru_overwrite_counts_as_use():
    cache = ThreadSafeCache(2, LRUEvictionPolicy())
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 10)  # touch "a"
    cache.put("c", 3)   # evicts "b"
    assert "b" not in cache and cache.get("a") == 10


# --------------------------------------------------------------------- LFU
def test_lfu_evicts_least_frequently_used():
    cache = ThreadSafeCache(2, LFUEvictionPolicy())
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    cache.get("a")
    cache.get("b")
    cache.put("c", 3)  # a=3, b=2 -> evict b
    assert "b" not in cache and "a" in cache and "c" in cache


def test_lfu_ties_broken_by_least_recent():
    cache = ThreadSafeCache(3, LFUEvictionPolicy())
    for k in "abc":
        cache.put(k, k)
    cache.get("a"); cache.get("b"); cache.get("c")  # all freq 2, "a" oldest at that freq
    cache.put("d", "d")
    assert "a" not in cache
    assert all(k in cache for k in "bcd")


def test_lfu_new_key_is_first_victim():
    cache = ThreadSafeCache(2, LFUEvictionPolicy())
    cache.put("hot", 1)
    for _ in range(5):
        cache.get("hot")
    cache.put("x", 1)
    cache.put("y", 1)  # x (freq 1) goes, hot survives
    assert "hot" in cache and "x" not in cache and "y" in cache


def test_lfu_min_freq_recovers_after_remove():
    policy = LFUEvictionPolicy()
    cache = ThreadSafeCache(3, policy)
    cache.put("a", 1); cache.put("b", 1); cache.put("c", 1)
    cache.get("b"); cache.get("b"); cache.get("c")
    cache.remove("a")             # empties the freq-1 bucket
    assert policy.evict() == "c"  # c=2 is now the minimum
    cache.put("d", 1); cache.put("e", 1)  # full again -> evict d (freq 1)
    assert "d" not in cache and {"b", "c", "e"} <= set(cache.store)


def test_lfu_internal_maps_stay_consistent():
    policy = LFUEvictionPolicy()
    cache = ThreadSafeCache(10, policy)
    rng = random.Random(0)
    for _ in range(5000):
        k = rng.randrange(30)
        op = rng.random()
        if op < 0.5:
            cache.put(k, k)
        elif op < 0.9:
            cache.get(k)
        else:
            cache.remove(k)
        assert set(policy.key_freq) == set(cache.store)
        bucket_keys = [k for b in policy.freq_keys.values() for k in b]
        assert sorted(bucket_keys) == sorted(policy.key_freq)
        assert all(b for b in policy.freq_keys.values())  # no empty buckets


# ------------------------------------------------------------ concurrency
@pytest.mark.parametrize("policy", POLICIES)
def test_thread_safety_under_contention(policy):
    capacity = 50
    cache = ThreadSafeCache(capacity, policy())
    errors = []
    barrier = threading.Barrier(8)

    def worker(seed):
        rng = random.Random(seed)
        barrier.wait()
        try:
            for _ in range(5000):
                k = rng.randrange(200)
                r = rng.random()
                if r < 0.5:
                    cache.put(k, k * 2)
                elif r < 0.95:
                    v = cache.get(k)
                    if v is not None and v != k * 2:
                        errors.append((k, v))
                else:
                    cache.remove(k)
        except Exception as exc:  # pragma: no cover - surfaced by assert below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(cache) <= capacity
    tracked = cache.eviction_policy.order if policy is LRUEvictionPolicy else cache.eviction_policy.key_freq
    assert set(tracked) == set(cache.store)


def test_concurrent_writers_distinct_keys_all_land_when_capacity_allows():
    cache = ThreadSafeCache(1000, LRUEvictionPolicy())

    def writer(base):
        for i in range(100):
            cache.put(base + i, base + i)

    threads = [threading.Thread(target=writer, args=(n * 100,)) for n in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(cache) == 1000
    assert all(cache.get(i) == i for i in range(1000))
