from collections import OrderedDict, defaultdict

from .eviction_policy import EvictionPolicy


class LFUEvictionPolicy(EvictionPolicy):
    """Least Frequently Used with O(1) access, insert and eviction.

    * ``key_freq`` maps each key to its access count.
    * ``freq_keys`` maps a count to the keys that have it, kept in an
      ``OrderedDict`` so ties are broken by least-recent use.
    * ``min_freq`` is the smallest count currently present, so the victim is
      always ``next(iter(freq_keys[min_freq]))``.
    """

    def __init__(self):
        self.key_freq = {}
        self.freq_keys = defaultdict(OrderedDict)
        self.min_freq = 0

    def _unlink(self, key, freq):
        bucket = self.freq_keys[freq]
        del bucket[key]
        if not bucket:
            del self.freq_keys[freq]

    def key_accessed(self, key):
        freq = self.key_freq.get(key)
        if freq is None:
            return
        self._unlink(key, freq)
        if freq == self.min_freq and freq not in self.freq_keys:
            self.min_freq = freq + 1
        self.key_freq[key] = freq + 1
        self.freq_keys[freq + 1][key] = None

    def key_added(self, key):
        if key in self.key_freq:
            self.key_accessed(key)
            return
        self.key_freq[key] = 1
        self.freq_keys[1][key] = None
        self.min_freq = 1

    def evict(self):
        if not self.key_freq:
            return None
        if self.min_freq not in self.freq_keys:
            # Only reachable after an explicit remove() emptied the lowest
            # bucket; recompute once (O(number of distinct counts)).
            self.min_freq = min(self.freq_keys)
        return next(iter(self.freq_keys[self.min_freq]))

    def key_removed(self, key):
        freq = self.key_freq.pop(key, None)
        if freq is not None:
            self._unlink(key, freq)

    def __len__(self):
        return len(self.key_freq)
