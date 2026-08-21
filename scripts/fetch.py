#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reddit 每日速览生成器（支持评论 + 动态调节 + 探索推荐 + 历史归档）
- 读取 scripts/subreddits.json：每个版块可配 enabled / limit / comments / comments_count
- 抓取 hot.json 最新热帖，可附带抓取高赞评论
- 可选 LLM 翻译（LLM_API_KEY）
- 历史归档：每天生成 archive/YYYY-MM-DD.html 快照，最新页顶部显示"历史归档"链接
- 生成 index.html
"""
import json
import os
import random
import re
import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBS_FILE = os.path.join(BASE_DIR, "scripts", "subreddits.json")
EXPLORE_FILE = os.path.join(BASE_DIR, "scripts", "explore.json")
OUT_FILE = os.path.join(BASE_DIR, "index.html")
CST = timezone(timedelta(hours=8))

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
]
TIMEOUT = 20
RETRIES = 3
JSON_AVAILABLE = True


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
    global JSON_AVAILABLE
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
    JSON_AVAILABLE = False
    print(f"  [x] 请求失败 {url[:80]}: {last_err}", file=sys.stderr)
    return None


def post_id_from_link(link: str) -> str:
    parts = link.rstrip("/").split("/")
    try:
        i = parts.index("comments")
        return parts[i + 1]
    except (ValueError, IndexError):
        return ""


def fetch_subreddit_rss(sub: str, limit: int = 4):
    url = f"https://www.reddit.com/r/{sub}/hot/.rss?limit={limit * 2}"
    try:
        xml_text = http_get(url)
        root = ET.fromstring(xml_text)
    except Exception:
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    posts = []

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = title_el.text.strip() if title_el is not None and title_el.text else ""

        link_el = entry.find("atom:link", ns)
        link = link_el.get("href", "") if link_el is not None else ""

        updated_el = entry.find("atom:updated", ns)
        created_utc = 0
        if updated_el is not None and updated_el.text:
            try:
                dt = datetime.fromisoformat(updated_el.text.replace("Z", "+00:00"))
                created_utc = dt.timestamp()
            except ValueError:
                pass

        content_el = entry.find("atom:content", ns)
        content_html = content_el.text if content_el is not None and content_el.text else ""

        score = 0
        m = re.search(r'(\d[\d,]*)\s*point', content_html)
        if m:
            score = int(m.group(1).replace(",", ""))

        comments = 0
        cm = re.search(r'(\d[\d,]*)\s*(?:comments|comment)', content_html)
        if cm:
            comments = int(cm.group(1).replace(",", ""))

        if not title:
            continue

        posts.append({
            "title": title,
            "score": score,
            "comments": comments,
            "link": link,
            "created": created_utc,
        })
        if len(posts) >= limit:
            break

    return posts


def fetch_subreddit(sub: str, limit: int = 4):
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit * 2}&raw_json=1"
    data = get_json(url)
    if not data:
        print(f"  [!] JSON API 不可用，降级 RSS 抓取 r/{sub}", file=sys.stderr)
        return fetch_subreddit_rss(sub, limit)
    posts = []
    for c in data["data"]["children"]:
        d = c["data"]
        if d.get("stickied"):
            continue
        posts.append({
            "title": d.get("title", "").strip(),
            "score": d.get("score", 0),
            "comments": d.get("num_comments", 0),
            "link": "https://www.reddit.com" + d.get("permalink", ""),
            "created": d.get("created_utc", 0),
        })
        if len(posts) >= limit:
            break
    return posts


def fetch_comments(post_id: str, limit: int = 5):
    if not JSON_AVAILABLE:
        return []
    url = f"https://www.reddit.com/comments/{post_id}.json?limit=100&sort=top&depth=1&raw_json=1"
    data = get_json(url)
    if not data or len(data) < 2:
        return []
    out = []
    for c in data[1]["data"]["children"]:
        if c.get("kind") != "t1":
            continue
        d = c.get("data", {})
        body = (d.get("body") or "").strip().replace("\n", " ")
        if not body:
            continue
        out.append({
            "author": d.get("author") or "[deleted]",
            "body": body[:220],
            "score": d.get("score", 0),
        })
        if len(out) >= limit:
            break
    return out


def translate_batch(titles, batch_size=30):
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        return {}
    base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    results = {}
    for i in range(0, len(titles), batch_size):
        batch = titles[i:i + batch_size]
        prompt = ("把下面的 Reddit 帖子标题逐条翻译成简体中文，保持原意，专有名词可保留英文。"
                  "用 JSON 数组输出，长度与输入一致，顺序相同，只输出 JSON：\n" +
                  json.dumps(batch, ensure_ascii=False))
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是专业翻译，输出严格 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            req = urllib.request.Request(
                base + "/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = json.loads(resp.read().decode())
            content = raw["choices"][0]["message"]["content"]
            arr = json.loads(content) if content.strip().startswith("[") else json.loads(content).get("translations", [])
            for t, zh in zip(batch, arr):
                if zh:
                    results[t] = str(zh).strip()
        except Exception as e:
            print(f"  [x] 翻译批次失败: {str(e)[:120]}", file=sys.stderr)
        time.sleep(1)
    return results


def render_html(categories, translated, stats, explore=None, archives=None):
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    nav = "".join(f'<a href="#{c["id"]}">{c["cn"]}</a>' for c in categories)
    if explore:
        nav += '<a href="#explore">探索</a>'

    archives_html = ""
    if archives:
        links = []
        for d in archives:
            links.append(f'<a href="archive/{d}.html" target="_blank">{d[5:]}</a>')
        archives_html = ('<div class="archives">📚 历史归档：' + " · ".join(links) + '</div>\n')

    blocks = []
    for c in categories:
        items = []
        for p in c.get("posts", []):
            zh = translated.get(p["title"], "")
            meta = f'<span class="meta">⬆{p["score"]} 💬{p["comments"]}</span>'
            zh_html = f'<span class="zh">{zh}</span>' if zh else ""
            cmts = ""
            for cm in p.get("comments_list", []):
                cmts += (f'<div class="cmt"><span class="cmt-a">u/{cm["author"]}</span> '
                         f'<span class="cmt-b">{cm["body"]}</span>'
                         f'<span class="cmt-s">▲{cm["score"]}</span></div>')
            items.append(
                f'<div class="item"><a href="{p["link"]}" target="_blank">{p["title"]}</a>'
                f'{meta}{zh_html}{cmts}</div>'
            )
        body = "\n".join(items) if items else '<div class="item"><span class="zh-tag">（今日无数据）</span></div>'
        blocks.append(
            f'<section class="cat" id="{c["id"]}">\n'
            f'  <h2><span class="cn">{c["cn"]}</span>'
            f'<span class="en">{c["en"]}</span></h2>\n{body}\n</section>'
        )
    cats_html = "\n\n".join(blocks)

    explore_html = ""
    if explore and explore.get("candidates"):
        cands = []
        for s in explore["candidates"][:12]:
            subs = s.get("subscribers", 0)
            sub_txt = f"{subs/1000:.0f}k" if subs >= 1000 else str(subs)
            cands.append(
                f'<div class="item"><span class="zh-tag">r/{s["name"]}</span> '
                f'<span class="meta">{sub_txt} 订阅 · {s.get("title", "")[:60]}</span></div>'
            )
        explore_html = (
            f'<section class="cat" id="explore">\n'
            f'  <h2><span class="cn">🔍 探索推荐（未收录的活跃版块）</span>'
            f'<span class="en">想加哪个，在 subreddits.json 里加一行即可</span></h2>\n'
            + "\n".join(cands) + f'\n</section>'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reddit 版块速览 · {now} · 中英双语</title>
<style>
  :root{{--ink:#1a1a1a;--sub:#666;--line:#e5e5e5;--accent:#ff4500;--bg:#fff}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;font-size:12.5px;line-height:1.4;color:var(--ink);background:var(--bg);padding:12px;max-width:1100px;margin:0 auto}}
  header{{border-bottom:2px solid var(--accent);padding-bottom:8px;margin-bottom:10px}}
  h1{{font-size:17px;font-weight:700}}
  .sub{{color:var(--sub);font-size:12px;margin-top:3px}}
  .stats{{display:inline-block;background:#fff3ec;color:var(--accent);font-weight:700;border-radius:4px;padding:1px 7px;margin-top:6px;font-size:12px}}
  .cat{{margin:0 0 6px;padding:8px 10px;border:1px solid var(--line);border-radius:6px}}
  .cat h2{{font-size:13px;margin-bottom:5px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
  .cat h2 .cn{{color:var(--accent)}}
  .cat h2 .en{{color:var(--sub);font-weight:400;font-size:11px}}
  .item{{padding:3px 0;border-bottom:1px dashed #f0f0f0}}
  .item:last-child{{border-bottom:none}}
  .item a{{color:var(--ink);text-decoration:none;font-size:12.5px}}
  .item a:hover{{color:var(--accent);text-decoration:underline}}
  .zh{{color:#333;font-size:12px;display:block;margin-top:1px}}
  .meta{{color:var(--sub);font-size:11px;margin-left:4px}}
  .zh-tag{{color:#888;font-size:11px}}
  .cmt{{font-size:11.5px;color:#444;padding:1px 0 1px 10px;border-left:2px solid #eee;margin:1px 0}}
  .cmt-a{{color:var(--accent);font-weight:600;margin-right:5px}}
  .cmt-s{{color:#aaa;margin-left:5px;font-size:10px}}
  .nav{{font-size:11px;color:var(--sub);margin-bottom:8px;line-height:1.9}}
  .nav a{{color:var(--accent);text-decoration:none;margin-right:6px}}
  .archives{{font-size:11.5px;color:var(--sub);background:#fff8f0;border:1px solid #f5e0c8;border-radius:4px;padding:4px 8px;margin-bottom:8px;line-height:1.8}}
  .archives a{{color:var(--accent);text-decoration:none;margin:0 2px}}
  .archives a:hover{{text-decoration:underline}}
  footer{{margin-top:10px;padding-top:8px;border-top:1px solid var(--line);color:var(--sub);font-size:11px}}
</style>
</head>
<body>
<header>
  <h1>Reddit 版块速览 · 中英对照</h1>
  <div class="sub">数据时间：{now}（GMT+8）· {stats["subs"]} 个版块 · 点击英文标题跳转原帖 · 自动更新</div>
  <span class="stats">{stats["subs"]} 版块 / {stats["posts"]} 帖子 / {stats["comments"]} 评论 / 中英双语同页</span>
</header>
{archives_html}<div class="nav">{nav}</div>
{cats_html}
{explore_html}
<footer>
  数据来自 Reddit 公开接口（自动抓取 · {now} GMT+8）· 标题为原文，中文为自动翻译仅供参考 · 链接均回原帖 · 仅供个人学习参考，版权归原作者所有
  · 调节方法：编辑 scripts/subreddits.json 中版块的 limit(条数)/comments(跟帖开关)/enabled(开关) 即可，次日生效
</footer>
</body>
</html>
"""


def main():
    skip_comments = "--no-comments" in sys.argv
    global_limit = None
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        global_limit = max(1, min(int(sys.argv[i + 1]), 10))

    with open(SUBS_FILE, encoding="utf-8") as f:
        subs = json.load(f)

    all_subs = []
    for c in subs["categories"]:
        for s in c["subs"]:
            cfg = s if isinstance(s, dict) else {"name": s}
            if cfg.get("enabled", True):
                all_subs.append(cfg)

    total_posts = total_comments = 0
    all_titles = []

    print(f"[*] 开始抓取 {len(all_subs)} 个版块...")
    for c in subs["categories"]:
        c["posts"] = []
        for s in c["subs"]:
            cfg = s if isinstance(s, dict) else {"name": s}
            if not cfg.get("enabled", True):
                print(f"  [-] r/{cfg['name']} 已停用，跳过")
                continue
            limit = global_limit or cfg.get("limit", 4)
            posts = fetch_subreddit(cfg["name"], limit)
            want_comments = (not skip_comments) and cfg.get("comments", False)
            cmt_n = cfg.get("comments_count", 5)
            for p in posts:
                if want_comments:
                    pid = post_id_from_link(p["link"])
                    cmts = fetch_comments(pid, cmt_n) if pid else []
                    p["comments_list"] = cmts
                    total_comments += len(cmts)
                    time.sleep(1.0)
                all_titles.append(p["title"])
            c["posts"].extend(posts)
            total_posts += len(posts)
            print(f"  [+] r/{cfg['name']}: {len(posts)} 帖" + (f", {sum(len(x.get('comments_list',[])) for x in posts)} 评论" if want_comments else ""))
            time.sleep(1.2)

    translated = translate_batch(all_titles)
    print(f"[*] 翻译: {len(translated)}/{len(all_titles)} 条")

    explore = None
    if os.path.exists(EXPLORE_FILE):
        with open(EXPLORE_FILE, encoding="utf-8") as f:
            explore = json.load(f)

    stats = {"subs": len(all_subs), "posts": total_posts, "comments": total_comments}

    # ---- 历史归档：每天新增 archive/YYYY-MM-DD.html，永不覆盖 ----
    ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    today = datetime.now(CST).strftime("%Y-%m-%d")
    archives = sorted(
        f[:-5] for f in os.listdir(ARCHIVE_DIR)
        if f.endswith(".html") and f[:-5] != today
    )

    html = render_html(subs["categories"], translated, stats, explore, archives)

    with open(os.path.join(ARCHIVE_DIR, today + ".html"), "w", encoding="utf-8") as f:
        f.write(html)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[✓] 已生成 index.html + archive/{today}.html"
          f"（{len(html)/1024:.0f} KB，{total_posts} 帖 / {total_comments} 评论，历史归档 {len(archives)} 天）")


if __name__ == "__main__":
    main()
