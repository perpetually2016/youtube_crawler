from concurrent.futures import ThreadPoolExecutor
from yt_dlp import YoutubeDL
from config import get_proxy

from config import (
    VIDEO_TODO,
    CHANEL_KEY,
    CHANNEL_FETCHED_KEY,
    BLOOM_FILTER_KEY,
    CHANNEL_FETCH_THREAD_NUM,
)
from output.redis_db import get_default_redis
from output.bloom_filter import BloomDeduper


def fetch_channel_videos(ch_id: str, redis_client, deduper, limit_per_channel=None):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "ignoreerrors": True,
    }
    PROXY = get_proxy()
    if PROXY:
        ydl_opts["proxy"] = PROXY

    is_custom = ch_id.startswith("@")
    if is_custom:
        channel_url = f"https://www.youtube.com/{ch_id}/videos"
    else:
        channel_url = f"https://www.youtube.com/channel/{ch_id}/videos"

    print(f"[FETCH] {channel_url}")

    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(channel_url, download=False)

    entries = result.get("entries") or []
    new_count = 0

    for entry in entries:
        vid = entry.get("id") or entry.get("url")
        if not vid:
            continue

        if deduper.seen_video(vid):
            continue

        url = vid if vid.startswith("http") else f"https://www.youtube.com/watch?v={vid}"
        if redis_client.sadd(VIDEO_TODO, url):
            deduper.add_video(vid)
            new_count += 1
            print(f"[VIDEO] {url}")

        if limit_per_channel and new_count >= limit_per_channel:
            break

    print(f"[DONE] {ch_id} new_video={new_count}")


def worker(limit_per_channel=None):

    print("[REDIS] get_default_redis() returned")
    try:
        redis_client = get_default_redis()
        print("[REDIS] get_default_redis() returned")
        redis_client.ping()
        print("[REDIS] ping OK")
    except Exception as e:
        print(f"[REDIS] connection FAILED: {e}")
        return
    deduper = BloomDeduper(redis_client, BLOOM_FILTER_KEY)

    while True:
        ch_id = redis_client.spop(CHANEL_KEY)

        if not ch_id:
            break

        ch_id = ch_id.decode() if isinstance(ch_id, bytes) else ch_id

        try:
            fetch_channel_videos(ch_id, redis_client, deduper, limit_per_channel)
            redis_client.sadd(CHANNEL_FETCHED_KEY, ch_id)
        except Exception as e:
            print(f"[ERROR] {ch_id}: {e}")
            redis_client.sadd(f"{CHANNEL_FETCHED_KEY}:failed", ch_id)


def main():
    with ThreadPoolExecutor(max_workers=CHANNEL_FETCH_THREAD_NUM) as executor:
        for _ in range(CHANNEL_FETCH_THREAD_NUM):
            executor.submit(worker, None)


if __name__ == "__main__":
    main()
