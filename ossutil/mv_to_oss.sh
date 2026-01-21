#!/bin/bash

CONFIG="/root/xxxx/ossutil/xxxx"
LOCAL_DIR="/root/xxxx"
CHECKPOINT_DIR="/root/xxxx/ossutil/.ossutil_checkpoint"
mkdir -p $CHECKPOINT_DIR

echo "🚀 [增强监控版] 视频搬运工已启动..."

while true; do
    TODAY=$(date +%Y-%m-%d)
    OSS_DEST="oss://download/xxxx/$TODAY/"

    # 1. 检查是否有就绪文件
    READY_COUNT=$(find "$LOCAL_DIR" -name "*.mp4" -mmin +1 | wc -l)

    if [ "$READY_COUNT" -eq 0 ]; then
        echo "😴 $(date '+%H:%M:%S') 暂无就绪视频，等待中..."
        sleep 10
        continue
    fi

    echo "📦 $(date '+%H:%M:%S') 发现 $READY_COUNT 个就绪视频，准备上传..."

    # 2. 执行搬运并捕获输出
    # 注意：$LOCAL_DIR/ 结尾加了斜杠，确保同步内容而非文件夹本身
    OUTPUT=$(ossutil -c "$CONFIG" cp "$LOCAL_DIR/" "$OSS_DEST" \
      --recursive \
      --include "*.mp4" \
      --exclude "*.aria2" \
      --exclude "*.part" \
      --exclude "*.f*" \
      --jobs 50 \
      --parallel 50 \
      --checkpoint-dir "$CHECKPOINT_DIR" \
      --update \
      --force 2>&1)

    EXIT_CODE=$?

    # 3. 从输出中提取关键数据
    OK_NUM=$(echo "$OUTPUT" | grep -oP 'OK num: \K\d+')
    AVG_SPEED=$(echo "$OUTPUT" | grep -oP 'average speed \K\d+')

    # 转换速度单位为 MB/s (简单计算)
    if [ ! -z "$AVG_SPEED" ] && [ "$AVG_SPEED" -gt 0 ]; then
        SPEED_MB=$(echo "scale=2; $AVG_SPEED / 1024 / 1024" | bc)
    else
        SPEED_MB=0
    fi

    # 4. 安全清理与精细化日志
    if [ $EXIT_CODE -eq 0 ]; then
        if [ "$OK_NUM" -gt 0 ]; then
            echo "✅ 成功上传: $OK_NUM 个文件 | 平均速度: ${SPEED_MB} MB/s"

            # 只有确实上传成功了，才清理 5 分钟前的本地文件
            find "$LOCAL_DIR" -name "*.mp4" -mmin +5 -exec rm -f {} \;
            echo "🧹 本地旧文件已清理。"
        else
            echo "⚠️ 扫描到了文件但上传数为 0 (可能是 OSS 已存在相同文件)"
        fi

        # 定期清理断点文件 (保持 checkpoint 目录清爽)
        find "$CHECKPOINT_DIR" -mtime +1 -exec rm -rf {} \; 2>/dev/null
    else
        echo "❌ 上传出错，错误信息如下："
        echo "$OUTPUT" | tail -n 3
    fi

    echo "--------------------------------------"
    sleep 10
done