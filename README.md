# Concurrent Cache

> A thread-safe, in-memory key-value cache in pure Python with pluggable eviction policies (LRU and LFU) and a multi-threaded benchmark to compare them.

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Dependencies-stdlib%20only-success" alt="Standard library only" />
  <img src="https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white" alt="pytest" />
  <img src="https://img.shields.io/badge/Concurrency-threading.RLock-blueviolet" alt="threading" />
</p>

---

## Features

- **Thread-safe core** – `ThreadSafeCache` guards every `get`, `put` and `remove` with a single `threading.RLock`, so multiple threads can share one cache safely.
- **Pluggable eviction (Strategy pattern)** – the cache takes any object implementing the abstract `EvictionPolicy` interface (`key_accessed`, `key_added`, `evict`, `key_removed`).
- **LRU policy** – backed by `collections.OrderedDict`; accessed keys move to the end, the oldest key is evicted.
- **LFU policy** – tracks per-key access counts and evicts the least frequently used key.
- **Capacity-bounded** – when the cache is full, the policy chooses which key to drop before the new key is inserted.
- **Benchmark harness** – runs N threads × M `put`/`get` operations against each policy and records the timings.
- **Zero runtime dependencies** – only the Python standard library (`pytest` for tests).

## Tech Stack

| Area | Tools |
|------|-------|
| Language | Python 3 |
| Concurrency | `threading` (`RLock`, `Thread`) |
| Data structures | `dict`, `collections.OrderedDict`, `collections.defaultdict` |
| Design | `abc.ABC` abstract base class (Strategy pattern) |
| Testing / benchmarking | `pytest`, `time.perf_counter` |

## Architecture

```mermaid
classDiagram
    class ThreadSafeCache {
        -int capacity
        -dict store
        -RLock lock
        -EvictionPolicy eviction_policy
        +get(key)
        +put(key, value)
        +remove(key)
    }
    class EvictionPolicy {
        <<abstract>>
        +key_accessed(key)
        +key_added(key)
        +evict()
        +key_removed(key)
    }
    class LRUEvictionPolicy {
        -OrderedDict order
    }
    class LFUEvictionPolicy {
        -dict freq
    }
    ThreadSafeCache --> EvictionPolicy : delegates eviction
    EvictionPolicy <|-- LRUEvictionPolicy
    EvictionPolicy <|-- LFUEvictionPolicy
```

`put` flow:

```mermaid
flowchart TD
    A[put key, value] --> L{acquire RLock}
    L --> B{key already cached?}
    B -- yes --> C[update value<br/>policy.key_accessed]
    B -- no --> D{size >= capacity?}
    D -- yes --> E[victim = policy.evict<br/>remove victim<br/>policy.key_removed]
    D -- no --> F
    E --> F[store value<br/>policy.key_added]
    C --> R[release lock]
    F --> R
```

## Project Structure

```
concurrent_cache/
├── cache/
│   ├── cache.py             # ThreadSafeCache
│   ├── eviction_policy.py   # EvictionPolicy ABC + LRU and LFU implementations
│   ├── lru_policy.py        # Alternative LRU with its own RLock (used by main.py and tests)
│   └── lfu_policy.py        # Alternative LFU with its own RLock
├── benchmarks/
│   └── benchmark.py         # LRU vs LFU multi-threaded benchmark
├── tests/
│   └── test_cache.py        # Concurrent reader/writer test
├── docs/
│   ├── design_summary.txt   # Design notes
│   └── performance_report.txt
├── benchmark_output.txt     # Last recorded benchmark run
├── main.py                  # Minimal usage example
├── run_benchmarks.bat       # Windows helper for the benchmark
└── requirements.txt
```

## Getting Started

```bash
git clone https://github.com/Gonugunta-Venkata-Jayanth/concurrent_cache.git
cd concurrent_cache
pip install -r requirements.txt   # only pytest; the cache itself needs no packages
```

Run the example:

```bash
python main.py
# 1
# None
```

Run the tests:

```bash
python -m pytest
```

Run the benchmark (writes `benchmark_output.txt`):

```bash
# macOS / Linux
PYTHONPATH=. python -m benchmarks.benchmark

# Windows
run_benchmarks.bat
```

## Usage

```python
from cache.cache import ThreadSafeCache
from cache.eviction_policy import LRUEvictionPolicy, LFUEvictionPolicy

cache = ThreadSafeCache(capacity=2, eviction_policy=LRUEvictionPolicy())
cache.put("a", 1)
cache.put("b", 2)
cache.get("a")        # -> 1  ("a" becomes most recently used)
cache.put("c", 3)     # evicts "b"
cache.get("b")        # -> None

lfu_cache = ThreadSafeCache(capacity=100, eviction_policy=LFUEvictionPolicy())
```

Writing your own policy only requires subclassing `EvictionPolicy` and implementing its four methods.

## Results

The benchmark (`benchmarks/benchmark.py`) uses a cache of capacity 500, 5 threads and 10,000 `put` + `get` operations per thread over 1,000 distinct keys. The run committed in [`benchmark_output.txt`](benchmark_output.txt) recorded:

| Policy | Time |
|--------|------|
| LRUEvictionPolicy | 0.0428 s |
| LFUEvictionPolicy | 0.6213 s |

LFU is slower here because its `evict()` scans all tracked keys with `min()` (O(n) per eviction), while LRU evicts from the front of an `OrderedDict` in O(1). Timings depend on the machine and Python version. See [`docs/performance_report.txt`](docs/performance_report.txt) for the qualitative analysis.

## Future Work

- O(1) LFU using a frequency → keys map (as described in the design notes)
- Merge the duplicate LRU/LFU implementations into one module
- Add assertion-based unit tests for eviction order, capacity limits and `remove`
- Finer-grained locking / lock striping to reduce contention
- TTL expiry, hit/miss statistics, and more policies (FIFO, ARC)
- Package for `pip install` and add CI

## Author

**GV Jayanth** – [GitHub @Gonugunta-Venkata-Jayanth](https://github.com/Gonugunta-Venkata-Jayanth)
