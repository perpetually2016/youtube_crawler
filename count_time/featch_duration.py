import random
import string
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# =============================
# 配置
# =============================
URLS_FILE = 'urls.txt'
OUTPUT_FILE = 'durations.txt'
BATCH_SIZE = 1000        # 每批处理多少条
MAX_WORKERS = 8          # 并发线程数
RETRY_COUNT = 2          # 失败重试次数

# =============================
# 生成随机 session 代理
# =============================
def generate_session(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_proxy():
    session = generate_session()
    return f'http://xxxx_{session}_20:xxxx:8828'

# =============================
# 单个视频抓取 duration
# =============================
def fetch_duration(url):
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'proxy': get_proxy(),
        'force_generic_extractor': True,
    }

    for attempt in range(RETRY_COUNT + 1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                duration = info.get('duration', 0)
                video_id = info.get('id')
                if video_id:
                    return video_id, duration
        except Exception as e:
            if attempt < RETRY_COUNT:
                time.sleep(1)  # 等待再试
            else:
                print(f"[ERROR] {url} -> {e}")
                return None, None

# =============================
# 分批执行
# =============================
def process_batch(batch_urls, batch_index):
    results = []
    total = len(batch_urls)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(fetch_duration, url): url for url in batch_urls}
        for i, future in enumerate(as_completed(future_to_url), 1):
            video_id, duration = future.result()
            if video_id:
                results.append((video_id, duration))
            if i % 100 == 0 or i == total:
                print(f"[Batch {batch_index}] Progress: {i}/{total}")
    return results

# =============================
# 主程序
# =============================
def main():
    with open(URLS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    total_urls = len(urls)
    print(f"Total URLs: {total_urls}")

    all_results = []
    for batch_index, start in enumerate(range(0, total_urls, BATCH_SIZE), 1):
        batch_urls = urls[start:start + BATCH_SIZE]
        print(f"[INFO] Processing batch {batch_index}, size {len(batch_urls)}")
        batch_results = process_batch(batch_urls, batch_index)
        all_results.extend(batch_results)

        # 写入文件，避免内存压力
        with open(OUTPUT_FILE, 'a') as f_out:
            for vid, dur in batch_results:
                f_out.write(f"{vid} {dur}\n")

    total_seconds = sum(dur for _, dur in all_results if dur)
    print(f"Total videos fetched: {len(all_results)}")
    print(f"Total duration: {total_seconds / 3600:.2f} hours")

if __name__ == "__main__":
    main()
