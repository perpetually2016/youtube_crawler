# bloom_filter.py
import mmh3
from config import  BLOOM_FILTER_KEY

# 支撑 1 亿数据，误差率 0.01% 方案# 228M
# def __init__(self, redis_client, key=BLOOM_FILTER_KEY, size=1_917_011_542, hash_count=14):

# 支撑 1 亿数据，误差率 0.1% 方案# 171M
# def __init__(self, redis_client, key=BLOOM_FILTER_KEY, size=1_440_000_000, hash_count=10):

# 支撑 1 亿数据，误差率 0.01% 方案
class BloomDeduper:
    def __init__(self, redis_client, key=BLOOM_FILTER_KEY, size=1_917_011_542, hash_count=14):

        self.redis = redis_client
        self.key = key
        self.size = size
        self.hash_count = hash_count

    def _hashes(self, value):
        # 记得加上 signed=False，保证跨平台索引一致
        return [mmh3.hash(value, i, signed=False) % self.size for i in range(self.hash_count)]

    def seen_video(self, value):
        """判断是否存在"""
        indexes = self._hashes(value)
        for idx in indexes:
            if self.redis.getbit(self.key, idx) == 0:
                return False
        return True

    def add_video(self, value):
        """添加到布隆过滤器"""
        indexes = self._hashes(value)
        for idx in indexes:
            self.redis.setbit(self.key, idx, 1)
