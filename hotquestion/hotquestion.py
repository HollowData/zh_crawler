#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
import sys
import time
import random
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ------------------------------------------------------------------------------
# 配置部分
# ------------------------------------------------------------------------------
# 日志配置
now = datetime.datetime.now()
LOG_DIR = os.path.join(os.path.dirname(sys.path[0]), 'log')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, f"{now.year}_{now.month}_{now.day}.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# User-Agent 池，可根据需要再补充
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    # "…… 其他 UA ……"
]

# 重试策略
retry_strategy = Retry(
    total=5,                      # 最多重试 5 次
    backoff_factor=1,             # 指数回退因子，第一次失败后 1s，再失败后 2s，再失败后 4s…
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)

# 创建带重试机制的 Session
sess = requests.Session()
sess.mount("https://", adapter)
sess.mount("http://", adapter)

# API 目标 URL
URL = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
PARAMS = {"limit": 50, "desktop": "true"}

# ------------------------------------------------------------------------------
# 抓取与容错
# ------------------------------------------------------------------------------
def fetch_hot_list(session, url, params, headers, timeout=10):
    """
    带超时、重试和异常捕获的请求函数，
    返回解析后的 data 列表，如果不可用则返回空列表。
    """
    try:
        resp = session.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"请求失败：{e}")
        return []

    try:
        j = resp.json()
    except ValueError as e:
        logging.error(f"JSON 解析失败：{e}")
        return []

    data = j.get("data")
    if not isinstance(data, list):
        logging.warning(f"未获取到有效的 data 字段，响应 keys: {list(j.keys())}")
        return []

    return data

def main():
    # 切换到脚本所在目录
    os.chdir(sys.path[0])

    # 选择随机 UA
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    data = fetch_hot_list(sess, URL, PARAMS, headers)
    if not data:
        logging.error("没有获取到热榜数据，退出。")
        return

    # 组织输出内容
    hot_list = []
    for item in data:
        try:
            tid = item["target"]["id"]
            title = item["target"]["title"]
            url = item["target"]["url"]
            hot_list.append(f"{tid}: {title} — {url}")
        except KeyError as e:
            logging.warning(f"跳过一条格式不符的记录：{e}")
            continue

    # 输出目录与文件
    year, month, day, hour = now.year, now.month, now.day, now.hour
    out_dir = os.path.join("hotquestion", f"{year}_{month}_{day}")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{year}_{month}_{day}_{hour}.txt")

    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(hot_list))
        logging.info(f"成功写入 {len(hot_list)} 条热榜到 {out_file}")
    except IOError as e:
        logging.error(f"写文件失败：{e}")

if __name__ == "__main__":
    main()
