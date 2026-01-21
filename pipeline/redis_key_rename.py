#!/usr/bin/env python3
# -*- coding: utf-8 -*-



import redis

from  config import REDIS_HOST, REDIS_PORT, REDIS_DB,REDIS_PASSWORD

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=REDIS_DB,
    decode_responses=True,
    socket_timeout=5,
)

SRC_KEY = "{howto100m}:video:failed"
DST_KEY = "{howto100m}:video:todo"

# =========================
# 开始迁移
# =========================
def migrate():
    src_count = redis_client.scard(SRC_KEY)
    print(f"📦 source [{SRC_KEY}] count = {src_count}")

    if src_count == 0:
        print("⚠️ source key empty, nothing to do")
        return

    moved = 0

    for url in redis_client.sscan_iter(SRC_KEY, count=1000):
        redis_client.sadd(DST_KEY, url)
        moved += 1
        if moved % 1000 == 0:
            print(f"➡️ migrated {moved} urls")

    dst_count = redis_client.scard(DST_KEY)
    print(f"📦 dest [{DST_KEY}] count = {dst_count}")

    # =========================
    # 校验 + 删除源 key
    # =========================
    if dst_count >= src_count:
        redis_client.delete(SRC_KEY)
        print(f"✅ migration done, deleted [{SRC_KEY}]")
    else:
        print("❌ count mismatch, abort delete")

if __name__ == "__main__":
    migrate()
