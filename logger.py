# !usr/bin/env python
# -*-coding:utf-8-*-
"""
@Author: mac
@email: perpetually2014@icloud.com
@Blog: https://github.com/perpetually

@File: logger.py
@Time: 2026/01/04 16:29
@Motto: stay hungry,stay foolish
"""

# 日志打印格式 以及日志存储位置
import logging


def log_conf(logger_name, log_path):
    # 创建Logger实例
    demo = logging.getLogger(logger_name)
    # 禁止向上一级传播
    demo.propagate = False

    # 日志输出样式
    # 2024 - 06 - 15 13: 39:01 qcc_wenshu.py[line:90] INFO请求列表页失败

    fmt = '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
    formatter = logging.Formatter(fmt=fmt, datefmt='%Y-%m-%d %H:%M:%S')

    # 设置日志输出级别
    demo.setLevel(logging.INFO)

    if not demo.handlers:
        # 文件输出配置
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        demo.addHandler(file_handler)

        # 屏幕输出配置
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        demo.addHandler(console_handler)

    return demo



