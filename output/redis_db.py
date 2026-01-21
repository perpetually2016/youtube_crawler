# output/redis_db.py
import redis
from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_DB,
    VIDEO_TODO
)

def get_default_redis() -> redis.Redis:
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )
    r.ping()
    return r


def push_video(r: redis.Redis, video_url: str):
    """
    video_url -> Redis List
    key 固定叫 video
    """
    r.lpush(VIDEO_TODO, video_url)


def pop_video(r: redis.Redis, timeout=5):
    """
    downloader 使用
    """
    res = r.brpop(VIDEO_TODO, timeout=timeout)
    if res:
        _, url = res
        return url
    return None
