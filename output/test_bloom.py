import redis
import time
from bloom_filter import BloomDeduper
from config import  BLOOM_FILTER_KEY
from output.redis_db import get_default_redis

def run_test():
    # 1. 连接 Redis

    r = get_default_redis()

    # 2. 初始化布隆过滤器
    # 注意：运行测试前建议确认是否需要 DEL 旧的 key
    # r.delete(BLOOM_FILTER_KEY)
    bf = BloomDeduper(r)

    print(f"--- 开始布隆过滤器测试 (Size: {bf.size}, K: {bf.hash_count}) ---")

    # 3. 测试基础功能
    test_url = "https://www.youtube.com/watch?v=GESQS4IvTto"

    print(f"检查 URL 是否存在: {bf.seen_video(test_url)}")  # 应为 False

    print("正在添加 URL...")
    bf.add_video(test_url)

    print(f"再次检查是否存在: {bf.seen_video(test_url)}")  # 应为 True

    # 4. 模拟批量写入并计算耗时
    print("\n正在模拟写入 1000 条数据以测试速度...")
    start_time = time.time()
    for i in range(1000):
        bf.add_video(f"url_test_{i}")
    end_time = time.time()
    print(f"1000 条数据写入耗时: {end_time - start_time:.4f} 秒")

    # 5. 查看 Redis 内存变化情况
    # 这里的 BITCOUNT 反应了位图中有多少位被染黑了
    bit_count = r.bitcount(BLOOM_FILTER_KEY)
    # 计算理论上 1001 条数据应该染黑的位数 (可能会有极小重合)
    expected_bits = 1001 * bf.hash_count

    print(f"\n--- Redis 状态统计 ---")
    print(f"当前位图中 '1' 的数量 (Bitcount): {bit_count}")
    print(f"预期染黑位数: 约 {expected_bits}")

    # 获取 String 的字节长度
    # 注意：Redis 的 GETRANGE 或 STRLEN 对大位图非常高效
    content_length = r.strlen(BLOOM_FILTER_KEY)
    print(f"Redis String 实际长度: {content_length / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    run_test()