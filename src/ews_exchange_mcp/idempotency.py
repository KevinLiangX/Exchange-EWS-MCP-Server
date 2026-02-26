import collections
import logging

logger = logging.getLogger("ews_mcp")

class IdempotencyManager:
    """Manages idempotency keys in memory with a fast LRU cache."""
    def __init__(self, max_size=500):
        self.cache = collections.OrderedDict()
        self.max_size = max_size

    def has(self, key: str) -> bool:
        return key in self.cache and self.cache[key] == "SUCCESS"

    def lock(self, key: str):
        if key in self.cache and self.cache[key] == "PENDING":
            raise ValueError(f"IDEMPOTENCY_CONFLICT: Key {key} is currently being processed.")
        if self.has(key):
            raise ValueError(f"IDEMPOTENCY_HIT: This email was already successfully processed. No action taken.")
            
        self.cache[key] = "PENDING"
        self._evict()

    def mark_success(self, key: str):
        self.cache[key] = "SUCCESS"

    def mark_failed(self, key: str):
        if key in self.cache:
            del self.cache[key]

    def _evict(self):
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
