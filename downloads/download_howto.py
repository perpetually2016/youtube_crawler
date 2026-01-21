#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import signal
import hashlib
import gc
import multiprocessing
from typing import Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import redis

# 假设这些是你自己的模块
from output.redis_db import get_default_redis
from output.bloom_filter import BloomDeduper
from config import get_proxy
from config import (
    VIDEO_OUTPUT_DIR_HOWTO,
    VIDEO_TODO,
    VIDEO_DOING,
    VIDEO_DONE,
    VIDEO_FAILED,
    BLOOM_FILTER_KEY,
    RETRY_HASH_KEY
)

MAX_RETRY_COUNT = 5


def signal_handler(signum, frame):
    # 优雅退出
    exit(0)


class AtomicTaskManager:
    @staticmethod
    def fetch_task_atomic(redis_client: redis.Redis) -> Optional[str]:
        """
        极速领任务逻辑：使用 SPOP 代替 WATCH/MULTI
        SPOP 是原子操作，能彻底消除高并发下的竞争延迟
        """
        try:
            url_bytes = redis_client.spop(VIDEO_TODO)
            if not url_bytes:
                return None
            url = url_bytes.decode() if isinstance(url_bytes, bytes) else str(url_bytes)
            # 记录到正在处理队列
            redis_client.sadd(VIDEO_DOING, url)
            return url
        except Exception:
            return None

    @staticmethod
    def move_to_done(redis_client: redis.Redis, url: str, vid: str):
        pipe = redis_client.pipeline()
        pipe.srem(VIDEO_DOING, url)
        pipe.sadd(VIDEO_DONE, vid)
        pipe.execute()

    @staticmethod
    def move_to_failed(redis_client: redis.Redis, url: str):
        pipe = redis_client.pipeline()
        pipe.srem(VIDEO_DOING, url)
        pipe.sadd(VIDEO_FAILED, url)
        pipe.execute()

    @staticmethod
    def move_doing_to_todo(redis_client: redis.Redis, url: str):
        pipe = redis_client.pipeline()
        pipe.srem(VIDEO_DOING, url)
        pipe.sadd(VIDEO_TODO, url)
        pipe.execute()


class RetryManager:
    @staticmethod
    def _key(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:12]

    @staticmethod
    def get(redis_client, url: str) -> int:
        v = redis_client.hget(RETRY_HASH_KEY, RetryManager._key(url))
        return int(v) if v else 0

    @staticmethod
    def incr(redis_client, url: str) -> int:
        v = redis_client.hincrby(RETRY_HASH_KEY, RetryManager._key(url), 1)
        redis_client.expire(RETRY_HASH_KEY, 86400)
        return v

    @staticmethod
    def clear(redis_client, url: str):
        redis_client.hdel(RETRY_HASH_KEY, RetryManager._key(url))


def is_retryable_error(msg: str) -> bool:
    msg = msg.lower()
    NON_RETRY = ["copyright", "account has been terminated", "no longer available"]
    RETRY = ["private video", "sign in", "403", "429", "timeout", "proxy", "connection reset"]
    if any(x in msg for x in NON_RETRY): return False
    return any(x in msg for x in RETRY)


def worker_process_logic(worker_id: int):
    signal.signal(signal.SIGINT, signal_handler)

    # 每个进程独立的连接池
    redis_client = get_default_redis()
    deduper = BloomDeduper(redis_client, BLOOM_FILTER_KEY)

    print(f"[Worker-{worker_id}] 启动 (PID: {os.getpid()})", flush=True)

    while True:
        url = None
        try:
            url = AtomicTaskManager.fetch_task_atomic(redis_client)
            if not url:
                time.sleep(2)  # 缩短等待时间
                continue

            ydl_opts = {
                "outtmpl": f"{VIDEO_OUTPUT_DIR_HOWTO}/%(id)s.%(ext)s",
                "format": "bestvideo[ext=mp4][height<=720]/best[ext=mp4]/best",
                "merge_output_format": "mp4",
                "quiet": True,
                "no_warnings": True,
                "proxy": get_proxy(),
                "cachedir": False,
                # --- 性能优化核心参数 ---
                "concurrent_fragment_downloads": 8,  # 进一步提升分片并发
                "buffersize": 1024 * 512,  # 提升至 512KB 缓冲区
                "http_chunk_size": 1024 * 1024 * 10,  # 每次请求 10MB，减少 TCP 握手次数
                "nocheckcertificate": True,  # 减少 SSL 校验耗时
                "logger": None,
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                vid = info.get("id")
                path = ydl.prepare_filename(info)
                if not path.endswith(".mp4"):
                    path = os.path.splitext(path)[0] + ".mp4"

                if os.path.exists(path):
                    AtomicTaskManager.move_to_done(redis_client, url, vid)
                    deduper.add_video(vid)
                    RetryManager.clear(redis_client, url)
                else:
                    raise FileNotFoundError("File save failed")

        except DownloadError as e:
            msg = str(e)
            if is_retryable_error(msg) and RetryManager.get(redis_client, url) < MAX_RETRY_COUNT:
                RetryManager.incr(redis_client, url)
                AtomicTaskManager.move_doing_to_todo(redis_client, url)
            else:
                AtomicTaskManager.move_to_failed(redis_client, url)
        except Exception:
            if url:
                AtomicTaskManager.move_doing_to_todo(redis_client, url)
            time.sleep(1)
        finally:
            gc.collect()


def start_pipeline(num_workers=20):
    os.makedirs(VIDEO_OUTPUT_DIR_HOWTO, exist_ok=True)
    r = get_default_redis()

    # 恢复逻辑保持不变
    doing = r.smembers(VIDEO_DOING)
    if doing:
        for t in doing:
            url = t.decode() if isinstance(t, bytes) else str(t)
            r.smove(VIDEO_DOING, VIDEO_TODO, url)

    print(f"🚀 冲刺 1G 带宽，Worker: {num_workers}")

    # 提高 maxtasksperchild 减少进程频繁重启的性能抖动
    with multiprocessing.Pool(processes=num_workers, maxtasksperchild=500) as pool:
        try:
            pool.map(worker_process_logic, range(num_workers))
        except KeyboardInterrupt:
            pool.terminate()
            pool.join()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=30)  # 建议增加到 30-40 进程
    args = parser.parse_args()

    # Linux 下优先使用 fork 提升进程创建和任务切换效率
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('fork', force=True)
        except RuntimeError:
            pass

    start_pipeline(args.threads)