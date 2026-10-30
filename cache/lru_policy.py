from collections import OrderedDict

from .eviction_policy import EvictionPolicy


class LRUEvictionPolicy(EvictionPolicy):
    """Least Recently Used: every operation is O(1) via ``OrderedDict``."""

    def __init__(self):
        self.order = OrderedDict()

    def key_accessed(self, key):
        if key in self.order:
            self.order.move_to_end(key)

    def key_added(self, key):
        self.order[key] = None
        self.order.move_to_end(key)

    def evict(self):
        return next(iter(self.order)) if self.order else None

    def key_removed(self, key):
        self.order.pop(key, None)

    def __len__(self):
        return len(self.order)
