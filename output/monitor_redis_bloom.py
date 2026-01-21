from output.redis_db import get_default_redis
def check_bloom_status():
    # 1. 连接 Redis
    try:
        r = get_default_redis()

        # 2. 获取关键指标
        # 如果你确认现在用的是 bf_videos，可以手动把这里的 KEY 改成 "bf_videos"
        target_key = "bf_videos"

        bit_count = r.bitcount(target_key)
        raw_size_bytes = r.strlen(target_key)

        # 3. 逻辑计算
        hash_count = 10  # 你设置的每个视频占用位数
        estimated_videos = bit_count / hash_count
        size_mb = raw_size_bytes / (1024 * 1024)

        # 4. 打印报告
        print("=" * 40)
        print(f"📊 布隆过滤器监控报告: {target_key}")
        print("-" * 40)
        print(f"✅ 已过滤视频数 (估算): {estimated_videos:,.0f} 条")
        print(f"🔹 已染黑位数 (Bitcount): {bit_count:,.0f}")
        print(f"💾 Redis 内存占用: {size_mb:.2f} MB")

        # 5. 健康度预警
        max_capacity = 100_000_000  # 你的 1 亿目标
        usage_pct = (estimated_videos / max_capacity) * 100
        print(f"📈 目标进度: {usage_pct:.4f}% (距离 1 亿条目标)")

        if usage_pct > 80:
            print("⚠️ 警告: 过滤器填充度超过 80%，误差率将开始上升！")
        else:
            print("🟢 状态: 运行良好，空间极其充裕。")
        print("=" * 40)

    except Exception as e:
        print(f"❌ 监控运行出错: {e}")


if __name__ == "__main__":
    check_bloom_status()