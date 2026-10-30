from abc import ABC, abstractmethod


class EvictionPolicy(ABC):
    """Interface every eviction policy implements.

    Policies are *not* thread-safe on their own: ``ThreadSafeCache`` calls them
    only while holding its lock, so they need no locking of their own.
    """

    @abstractmethod
    def key_accessed(self, key):
        """Called when an existing key is read or overwritten."""

    @abstractmethod
    def key_added(self, key):
        """Called when a new key is inserted."""

    @abstractmethod
    def evict(self):
        """Return the key that should be evicted next (or ``None`` if empty).

        This only *chooses* the victim; the cache then calls ``key_removed``.
        """

    @abstractmethod
    def key_removed(self, key):
        """Called when a key leaves the cache (eviction or explicit remove)."""
