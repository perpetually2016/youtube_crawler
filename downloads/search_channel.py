from yt_dlp import YoutubeDL
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import get_proxy

from config import (
    SEARCH_MAX_RESULTS,
    VIDEO_TODO,
    CHANEL_KEY,
)
from output.redis_db import get_default_redis

def search_and_save(keyword: str):
    redis_client = get_default_redis()

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "cachedir": False,
        "ignoreerrors": True,
    }
    PROXY = get_proxy()
    if PROXY:
        ydl_opts["proxy"] = PROXY

    search_query = f"ytsearch{SEARCH_MAX_RESULTS}:{keyword}"

    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(search_query, download=False)

    entries = result.get("entries", [])[:SEARCH_MAX_RESULTS]

    video_urls = set()
    channel_ids = set()

    for entry in entries:
        vid = entry.get("id")
        cid = entry.get("channel_id")
        if not vid or not cid:
            continue

        video_urls.add(f"https://www.youtube.com/watch?v={vid}")
        channel_ids.add(cid)

    pipe = redis_client.pipeline(transaction=False)

    if video_urls:
        pipe.sadd(VIDEO_TODO, *video_urls)

    if channel_ids:
        pipe.sadd(CHANEL_KEY, *channel_ids)

    pipe.execute()
    redis_client.close()

    print(
        f"[DONE] keyword={keyword} "
        f"video+{len(video_urls)} "
        f"channel+{len(channel_ids)}"
    )


def search_keywords_multithread(keywords, thread_num=8):
    with ThreadPoolExecutor(max_workers=thread_num) as executor:
        futures = [
            executor.submit(search_and_save, kw)
            for kw in keywords
        ]
        for f in as_completed(futures):
            f.result()


if __name__ == "__main__":
    keywords =first_person_verbs = [
    # 观察与感知
    "看", "看见", "注视", "观察",
        "发现", "注意", "认出", "查看", "寻找", "环顾",
    "瞥见", "扫视", "聚焦", "打量", "识别", "确认", "阅读", "检查", "欣赏", "仰望",
    "俯视", "远眺", "偷看", "监视", "见证", "察觉", "感知", "听见", "聆听", "倾听",
    "闻到", "品尝", "触摸", "感觉", "感受", "体验",

    # 手部与物体交互 (核心)
    "拿", "取", "抓", "握", "提起", "举起", "抬起", "搬运", "携带", "放下",
    "放置", "摆放", "安放", "搁置", "移开", "移动", "推动", "拉动", "拖拽",
    "抬起", "按压", "按下", "点击", "敲击", "轻拍", "抚摸", "擦拭", "清洗",
    "揉搓", "搅拌", "折叠", "展开", "打开", "关闭", "拧开", "拧紧", "插入",
    "拔出", "连接", "断开", "组装", "拆卸", "包装", "解开", "系上", "切割",
    "剪开", "撕开", "粘贴", "涂抹", "倾倒", "盛出", "舀起", "夹起", "拨动",
    "翻转", "转动", "摇晃", "抖动", "撒", "倒", "接住", "抛", "扔", "投掷",
    "传递", "递给", "归还", "收集", "整理", "归位", "收起", "摆放", "堆叠",
    "排列", "挑选", "选择", "丢弃", "扔掉", "保存", "保护", "握住", "松开",

    # 位移与身体动作
    "走", "行走", "前进", "后退", "转身", "回头", "跨越", "穿过", "进入",
    "离开", "到达", "接近", "远离", "跟随", "追赶", "躲避", "站立", "坐下",
    "蹲下", "躺下", "趴下", "弯腰", "挺直", "伸手", "缩手", "抬手", "挥手",
    "招手", "指向", "伸出", "收回", "点头", "摇头", "抬头", "低头", "转身",
    "侧身", "跳跃", "踮脚", "爬", "攀登", "支撑", "倚靠", "平衡",

    # 日常任务与活动
    "做饭", "烹饪", "切菜", "炒菜", "煮饭", "烧水", "冲泡", "烘烤", "清洗",
    "打扫", "擦拭", "拖地", "扫地", "整理", "收拾", "洗涤", "晾晒", "熨烫",
    "缝补", "修理", "组装", "写作", "绘画", "书写", "记录", "计算", "思考",
    "计划", "决定", "尝试", "开始", "继续", "完成", "停止", "休息", "等待",
    "寻找", "购买", "支付", "交换", "学习", "练习", "工作", "创造", "帮助",
    "分享", "交流", "说话", "询问", "回答", "解释", "指导", "展示", "表演",
    "玩耍", "娱乐", "锻炼", "跑步", "拉伸", "训练", "驾驶", "骑行"
]

    search_keywords_multithread(
        keywords=keywords,
        thread_num=8,   # 👈 重点参数
    )
