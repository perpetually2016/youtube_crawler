from pathlib import Path
BASE_DIR = Path(__file__).parent

# 搜索结果路径

# VIDEO_OUTPUT_DIR = Path("/root/xxxx/local_cache/video")
# VIDEO_OUTPUT_DIR_HOWTO = Path("/root/xxxx/local_cache/howto")

VIDEO_OUTPUT_DIR = BASE_DIR / "data" / "video"
VIDEO_OUTPUT_DIR_HOWTO = BASE_DIR / "data" / "howto"
RETRY_HASH_KEY = "download:retry_counts"

import datetime

import random
import string

def generate_session(length=12) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_proxy() -> str:
    session = generate_session()
    return f'http://xxxx_{session}_20:xxxx:1111'

print(get_proxy())

# 每个关键词最大搜索结果数量s
SEARCH_MAX_RESULTS = 100

# 多关键词并发数
MAX_KEYWORD_THREADS = 3

# OSS 上传配置（可选）
today = datetime.datetime.now().strftime("%Y-%m-%d")
oss_dest = f"oss://download/video/{today}/"
config_path = "/root/data/ossutil/xxxxx"

# mysql配置
host = "rm-xxxx.com"
port = 3306
user = "robo"
password = "Dding1107"
database='robosience'


# redis外网
REDIS_HOST = "r-xxxx.com"

# redis内网
REDIS_PORT = 6379
REDIS_PASSWORD = "xxxx"
REDIS_DB = 0   # ⚠️ redis 的 db 必须是 int

# ===== Redis key =====

VIDEO_HOWTO_TODO='video_id'
CHANEL_KEY = "chanel_id"
SEARCH_KEY = "keywords"
BLOOM_FILTER_KEY='bf_videos'

# DATASET = "howto100m"
DATASET = "video"

VIDEO_TODO    = f"{{{DATASET}}}:video:todo"
VIDEO_DOING   = f"{{{DATASET}}}:video:doing"
VIDEO_DONE    = f"{{{DATASET}}}:video:done"
VIDEO_FAILED  = f"{{{DATASET}}}:video:failed"

print(VIDEO_TODO)

# ===== 多线程配置 =====
NUM_DOWNLOAD_THREADS = 4
# config.py
CHANNEL_FETCH_THREAD_NUM = 16  # 你想用多少线程抓 channel，就改这里



