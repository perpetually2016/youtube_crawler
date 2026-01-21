#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import traceback
import threading
from yt_dlp import YoutubeDL
from output.redis_db import get_default_redis
from config import VIDEO_OUTPUT_DIR
from config import get_proxy
# ===== Redis SET key =====
TODO_KEY = "video:set:todo"
DOING_KEY = "video:set:doing"
DONE_KEY = "video:set:done"
FAILED_KEY = "video:set:failed"

# ===== yt-dlp 下载参数 =====
YDL_OPTS = {
    "outtmpl": f"{VIDEO_OUTPUT_DIR}/%(id)s.%(ext)s",
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
    "quiet": True,
    "retries": 5,
    "fragment_retries": 5,
    "concurrent_fragment_downloads": 8,
    "noprogress": True,
}
PROXY = get_proxy()
if PROXY:
    YDL_OPTS["proxy"] = PROXY

# ===== 确保目录存在 =====
os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)


def download_video(url: str):
    """
    使用 yt-dlp 下载视频
    """
    with YoutubeDL(YDL_OPTS) as ydl:
        ydl.download([url])


def worker(thread_id: int, redis_client):
    """
    多线程 worker
    """
    print(f"[Thread-{thread_id}] 启动")
    while True:
        url = redis_client.spop(TODO_KEY)
        if not url:
            time.sleep(2)
            continue

        redis_client.sadd(DOING_KEY, url)
        try:
            download_video(url)
            redis_client.srem(DOING_KEY, url)
            redis_client.sadd(DONE_KEY, url)
            print(f"[Thread-{thread_id}] ✅ 完成 {url}")
        except Exception as e:
            redis_client.srem(DOING_KEY, url)
            redis_client.sadd(TODO_KEY, url)  # 下载失败放回队列
            print(f"[Thread-{thread_id}] ❌ 下载失败 {url}, 错误: {e}")
            traceback.print_exc()


def run(num_threads: int = 4):
    redis_client = get_default_redis()
    threads = []

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i + 1, redis_client), daemon=True)
        t.start()
        threads.append(t)

    print(f"[主线程] 已启动 {num_threads} 个下载线程")
    # 主线程阻塞
    for t in threads:
        t.join()


if __name__ == "__main__":
    # 启动 4 个线程下载
    run(num_threads=4)
