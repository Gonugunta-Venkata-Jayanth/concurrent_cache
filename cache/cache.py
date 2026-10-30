from threading import RLock


class ThreadSafeCache:
    """Capacity-bounded key/value cache guarded by a single ``RLock``.

    All reads and writes, including the calls into the eviction policy, happen
    while holding the lock, so the store and the policy never disagree.
    """

    def __init__(self, capacity, eviction_policy):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self.store = dict()
        self.lock = RLock()
        self.eviction_policy = eviction_policy

    def get(self, key, default=None):
        with self.lock:
            if key in self.store:
                self.eviction_policy.key_accessed(key)
                return self.store[key]
            return default

    def put(self, key, value):
        with self.lock:
            if key in self.store:
                self.store[key] = value
                self.eviction_policy.key_accessed(key)
                return
            if len(self.store) >= self.capacity:
                evict_key = self.eviction_policy.evict()
                if evict_key is not None:
                    self.store.pop(evict_key, None)
                    self.eviction_policy.key_removed(evict_key)
            self.store[key] = value
            self.eviction_policy.key_added(key)

    def remove(self, key):
        with self.lock:
            if key in self.store:
                del self.store[key]
                self.eviction_policy.key_removed(key)

    def __contains__(self, key):
        with self.lock:
            return key in self.store

    def __len__(self):
        with self.lock:
            return len(self.store)
