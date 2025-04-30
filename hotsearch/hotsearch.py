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
# 确保在脚本文件夹运行
os.chdir(sys.path[0])

# 当前时间
now = datetime.datetime.now()
year, month, day, hour = now.year, now.month, now.day, now.hour

# 日志配置
LOG_DIR = os.path.join(os.path.dirname(sys.path[0]), 'log')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, f"{year}_{month}_{day}.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# User-Agent 池，可酌情增删
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    # … 如需可加更多 UA …
]

# Retry 策略（uriib3 >=1.26）
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]   # 注意allowed_methods而非method_whitelist
)
adapter = HTTPAdapter(max_retries=retry_strategy)

# 创建带重试机制的 Session
sess = requests.Session()
sess.mount("https://", adapter)
sess.mount("http://", adapter)

# API 配置
URL = "https://www.zhihu.com/api/v4/search/top_search"
HEADERS = {"User-Agent": random.choice(USER_AGENTS)}
TIMEOUT = 10  # 秒

# ------------------------------------------------------------------------------
# 抓取与容错函数
# ------------------------------------------------------------------------------
def fetch_top_search(session, url, headers, timeout=10):
    """
    请求并解析 top_search 数据，返回 list（元素为 dict），失败返回空列表。
    """
    try:
        resp = session.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"请求失败：{e}")
        return []

    try:
        j = resp.json()
    except ValueError as e:
        logging.error(f"JSON 解析失败：{e}")
        return []

    words = j.get("top_search", {}).get("words")
    if not isinstance(words, list):
        logging.warning(f"未获取到有效的 words 列表，响应 keys: {list(j.keys())}")
        return []

    return words

# ------------------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------------------
def main():
    data = fetch_top_search(sess, URL, HEADERS, TIMEOUT)
    if not data:
        logging.error("没有获取到热搜数据，退出。")
        return

    hot_list = []
    for item in data:
        try:
            query = item["query"]
            display = item.get("display_query", query)
            hot_list.append(f"{query}: {display}")
        except KeyError as e:
            logging.warning(f"跳过格式异常记录：{e}")
            continue

    # 输出目录与文件
    out_dir = os.path.join("hotresearch", f"{year}_{month}_{day}")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{year}_{month}_{day}_{hour}.txt")

    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(hot_list))
        logging.info(f"成功写入 {len(hot_list)} 条热搜到 {out_file}")
    except IOError as e:
        logging.error(f"写文件失败：{e}")

if __name__ == "__main__":
    main()
