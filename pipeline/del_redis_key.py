#!/usr/bin/env python3
# 超简单清理脚本
import redis
from output.redis_db import get_default_redis

redis_client = get_default_redis()

# 删除所有 retry:* 和 heartbeat:* key
patterns = ["retry:*", "heartbeat:*", "lock:*", "download:retry_counts"]
total = 0

for pattern in patterns:
    keys = redis_client.keys(pattern)
    if keys:
        deleted = redis_client.delete(*keys)
        total += deleted
        print(f"删除 {pattern}: {deleted} 个key")

print(f"\n✅ 总共删除了 {total} 个临时key")