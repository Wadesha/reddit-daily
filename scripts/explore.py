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
import random
import sys
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBS_FILE = os.path.join(BASE_DIR, "scripts", "subreddits.json")
EXPLORE_FILE = os.path.join(BASE_DIR, "scripts", "explore.json")

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
]
TIMEOUT = 20
RETRIES = 3


def _make_headers():
    return {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
    }


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers=_make_headers())
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _reddit_urls(url: str):
    yield url
    if "www.reddit.com" in url:
        yield url.replace("www.reddit.com", "old.reddit.com")


def get_json(url: str):
    last_err = None
    for domain_url in _reddit_urls(url):
        for attempt in range(RETRIES):
            try:
                return json.loads(http_get(domain_url))
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code}"
                if e.code in (429, 503):
                    delay = 6 * (2 ** attempt) + random.uniform(0, 2)
                    time.sleep(delay)
                elif e.code == 403:
                    delay = 10 * (attempt + 1) + random.uniform(0, 3)
                    time.sleep(delay)
                    break
            except Exception as e:
                last_err = str(e)[:120]
                time.sleep(3)
    raise RuntimeError(f"请求失败: {last_err}")


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
    for page in (None, "?after=t5_2qrbh"):
        try:
            url = "https://www.reddit.com/subreddits/popular.json?limit=100" + (page or "")
            data = get_json(url)
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
