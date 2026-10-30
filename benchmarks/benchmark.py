# benchmarks/benchmark.py

import time
import threading
from cache.cache import ThreadSafeCache
from cache.lfu_policy import LFUEvictionPolicy
from cache.lru_policy import LRUEvictionPolicy

def benchmark_policy(policy_class, ops_per_thread=10000, num_threads=5):
    cache = ThreadSafeCache(capacity=500, eviction_policy=policy_class())

    def worker():
        for i in range(ops_per_thread):
            key = i % 1000
            cache.put(key, i)
            cache.get(key)

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]

    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    end = time.perf_counter()

    duration = end - start
    return f"{policy_class.__name__}: {duration:.4f} seconds"

if __name__ == "__main__":
    results = []
    results.append(benchmark_policy(LRUEvictionPolicy))
    results.append(benchmark_policy(LFUEvictionPolicy))

    for result in results:
        print(result)
    with open("benchmark_output.txt", "w") as f:
        for result in results:
            f.write(result + "\n")