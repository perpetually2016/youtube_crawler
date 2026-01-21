# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@File: mysql_db.py
@Desc: MySQL database operations for YouTube crawler
"""
from datetime import datetime
import pymysql
import config
import os
import time
import logger
# 日志
log_path = os.path.abspath(os.path.dirname(__file__)) + "/log/db_%s.log" % time.strftime("%Y%m%d")
logging = logger.log_conf("youtube_db", log_path)


class YoutubeDB:
    def __init__(self):
        self.conn = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            passwd=config.password,
            database=config.database,
            charset="utf8mb4",
            autocommit=True,
        )

    def close(self):
        self.conn.close()

    # =========================
    # 获取 channel 列表
    # =========================
    def get_channels_by_status(self, status=None, limit=1000):
        """
        获取 channel 列表
        """
        with self.conn.cursor(pymysql.cursors.DictCursor) as cursor:
            if status is None:
                sql = """
                      SELECT id, channel_id, keyword
                      FROM youtube_channel
                      WHERE status IS NULL
                      ORDER BY id ASC
                          LIMIT %s \
                      """
                cursor.execute(sql, (limit,))
            else:
                sql = """
                      SELECT id, channel_id, keyword
                      FROM youtube_channel
                      WHERE status = %s
                      ORDER BY id ASC
                          LIMIT %s \
                      """
                cursor.execute(sql, (status, limit))

            return cursor.fetchall()

    # =========================
    # 更新 channel 状态
    # =========================
    def update_channel_status(self, channel_id: str, status: int):
        """
        更新指定 channel 的状态
        """
        sql = """
              UPDATE youtube_channel
              SET status=%s, \
                  update_time=%s
              WHERE channel_id = %s \
              """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (status, datetime.now(), channel_id))
            self.conn.commit()
            print(f"[UPDATE] channel_id={channel_id} status={status}")
        except Exception as e:
            self.conn.rollback()
            print(f"[ERROR] update_channel_status failed for {channel_id}: {e}")

    # =========================
    # Channel 写入
    # =========================
    def save_channel(self,  channel: dict):
        """
        保存单条 channel
        """
        cursor = self.db.cursor()

        sql = """
        INSERT INTO youtube_channel
            (keyword, uploader, channel_id, channel_url, custom_channel_url)
        VALUES
            (%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            keyword = VALUES(keyword),
            uploader = VALUES(uploader),
            channel_id = VALUES(channel_id),
            channel_url = VALUES(channel_url),
            custom_channel_url = VALUES(custom_channel_url),
            update_time = CURRENT_TIMESTAMP
        """

        print('写入成功:{}'.format(channel))
        try:
            cursor.execute(
                sql,
                (
                    channel.get("keyword"),
                    channel.get("uploader"),
                    channel.get("channel_id"),
                    channel.get("channel_url"),
                    channel.get("custom_channel_url"),
                ),
            )
        except Exception as e:
            logging.error(f"Channel 写入失败: {e}, data={channel}")
        finally:
            cursor.close()

    def save_channels(self, keyword: str, channel_records: list[dict]):
        """
        批量保存 channel
        """
        for ch in channel_records:
            self.save_channel(ch)

    # =========================
    # Video（search 阶段）写入
    # =========================
    def save_search_video(self,  video: dict):
        """
        保存单条 search video
        """
        cursor = self.db.cursor()

        sql = """
        INSERT INTO youtube_videos
            (keyword, video_id, url, title, duration, uploader)
        VALUES
            (%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            keyword = VALUES(keyword),
            video_id = VALUES(video_id),
            url = VALUES(url),
            title = VALUES(title),
            duration = VALUES(duration),
            uploader = VALUES(uploader),
            update_time = CURRENT_TIMESTAMP
        """
        try:
            cursor.execute(
                sql,
                (
                    video.get("keyword"),
                    video.get("video_id"),
                    video.get("url"),
                    video.get("title"),
                    video.get("duration"),
                    video.get("uploader"),

                ),
            )
            print('写入成功:{}'.format(video))
        except Exception as e:
            logging.error(f"Video 写入失败: {e}, data={video}")
        finally:
            cursor.close()

    def save_search_videos(self, keyword: str, video_records: list[dict]):
        """
        批量保存 search videos
        """
        for v in video_records:
            self.save_search_video(v)

    # =========================
    # 统一入口（search 阶段）
    # =========================
    def save_search_result(
        self,
        keyword: str,
        video_records: list[dict],
        channel_records: list[dict],
    ):
        """
        search 阶段统一入库
        """
        self.save_channels(keyword, channel_records)
        self.save_search_videos(keyword, video_records)

