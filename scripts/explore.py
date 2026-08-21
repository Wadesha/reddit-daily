#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reddit 版块探索器
- 从 Reddit 热门版块榜单抓取候选版块（含订阅数/简介）
- 排除已在 subreddits.json 中收录的
- 输出 scripts/explore.json，供 fetch.py 渲染到页面底部"探索推荐"区

用法：
    python3 scripts/explore.py [数量]      # 默认保留 15 个候选
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBS_FILE = os.path.join(BASE_DIR, "scripts", "subreddits.json")
EXPLORE_FILE = os.path.join(BASE_DIR, "scripts", "explore.json")
UA = "reddit-daily-digest/1.0 (personal non-commercial use)"
TIMEOUT = 20


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main():
    keep = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 15

    # 已收录版块（去重、小写）
    with open(SUBS_FILE, encoding="utf-8") as f:
        subs = json.load(f)
    known = set()
    for c in subs["categories"]:
        for s in c["subs"]:
            name = s["name"] if isinstance(s, dict) else s
            known.add(name.lower())

    # 抓热门版块榜单（两页）
    candidates = {}
    for page in (None, "?after=t5_2qrbh"):  # 第二页的 after 游标由接口返回，失败则只取第一页
        try:
            url = "https://www.reddit.com/subreddits/popular.json?limit=100" + (page or "")
            data = json.loads(http_get(url))
            for c in data["data"]["children"]:
                d = c["data"]
                name = d.get("display_name", "")
                if name.lower() in known or name in candidates:
                    continue
                candidates[name] = {
                    "name": name,
                    "title": (d.get("title") or d.get("public_description") or "")[:80],
                    "subscribers": d.get("subscribers", 0),
                }
        except Exception as e:
            print(f"[x] 榜单抓取失败: {str(e)[:100]}", file=sys.stderr)
        time.sleep(1.0)

    # 按订阅数排序取前 keep 个
    top = sorted(candidates.values(), key=lambda x: -x["subscribers"])[:keep]
    out = {"updated": time.strftime("%Y-%m-%d %H:%M"), "candidates": top}
    with open(EXPLORE_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[✓] 探索完成：{len(top)} 个候选版块已写入 {EXPLORE_FILE}")
    for s in top:
        print(f"  r/{s['name']}  ({s['subscribers']/1000:.0f}k)  {s['title']}")


if __name__ == "__main__":
    main()
