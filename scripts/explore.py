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
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

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
OAUTH_TOKEN = None
OAUTH_TOKEN_EXPIRES = 0


def _get_oauth_token():
    global OAUTH_TOKEN, OAUTH_TOKEN_EXPIRES
    now = time.time()
    if OAUTH_TOKEN and now < OAUTH_TOKEN_EXPIRES:
        return OAUTH_TOKEN

    client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    try:
        if HAS_REQUESTS:
            resp = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(client_id, client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": "reddit-daily-digest/1.0"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            token_data = resp.json()
        else:
            cred = urllib.parse.quote(f"{client_id}:{client_secret}", safe="")
            req = urllib.request.Request(
                "https://www.reddit.com/api/v1/access_token",
                data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
                headers={
                    "Authorization": f"Basic {cred}",
                    "User-Agent": "reddit-daily-digest/1.0",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                token_data = json.loads(resp.read())

        OAUTH_TOKEN = token_data.get("access_token", "")
        expires_in = token_data.get("expires_in", 3600)
        OAUTH_TOKEN_EXPIRES = now + expires_in - 60
        if OAUTH_TOKEN:
            print("[✓] Reddit OAuth 认证成功", file=sys.stderr)
        return OAUTH_TOKEN
    except Exception as e:
        print(f"[!] Reddit OAuth 失败: {str(e)[:100]}", file=sys.stderr)
        OAUTH_TOKEN = None
        OAUTH_TOKEN_EXPIRES = 0
        return None


def _make_headers(use_auth=False):
    headers = {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if use_auth:
        token = _get_oauth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def http_get(url: str, use_auth=False) -> str:
    if HAS_REQUESTS:
        try:
            resp = requests.get(url, headers=_make_headers(use_auth=use_auth), timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.HTTPError as e:
            raise urllib.error.HTTPError(
                url, e.response.status_code, str(e),
                e.response.headers if e.response else None,
                None
            ) from None
        except requests.exceptions.RequestException as e:
            raise Exception(str(e)[:200]) from None
    else:
        req = urllib.request.Request(url, headers=_make_headers(use_auth=use_auth))
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")


def _reddit_urls(url: str):
    yield url
    if "www.reddit.com" in url:
        yield url.replace("www.reddit.com", "old.reddit.com")


def get_json(url: str):
    last_err = None
    has_oauth = bool(_get_oauth_token())
    for domain_url in _reddit_urls(url):
        for use_auth in ([True, False] if has_oauth else [False]):
            for attempt in range(RETRIES):
                try:
                    return json.loads(http_get(domain_url, use_auth=use_auth))
                except urllib.error.HTTPError as e:
                    last_err = f"HTTP {e.code}"
                    if e.code in (429, 503):
                        delay = 6 * (2 ** attempt) + random.uniform(0, 2)
                        time.sleep(delay)
                    elif e.code == 403:
                        if use_auth:
                            break
                        delay = 10 * (attempt + 1) + random.uniform(0, 3)
                        time.sleep(delay)
                        break
                    else:
                        break
                except Exception as e:
                    last_err = str(e)[:120]
                    time.sleep(3)
    raise RuntimeError(f"请求失败: {last_err}")


def fetch_popular_rss(known_subs):
    subs_count = {}
    rss_urls = [
        "https://www.reddit.com/r/popular/.rss?limit=100",
        "https://old.reddit.com/r/popular/.rss?limit=100",
    ]
    for rss_url in rss_urls:
        for attempt in range(RETRIES):
            try:
                xml_text = http_get(rss_url)
                root = ET.fromstring(xml_text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", ns):
                    link_el = entry.find("atom:link", ns)
                    if link_el is None:
                        continue
                    href = link_el.get("href", "")
                    m = re.search(r"/r/([^/]+)/comments/", href)
                    if not m:
                        continue
                    sub = urllib.parse.unquote(m.group(1))
                    if sub.lower() in known_subs:
                        continue
                    subs_count[sub] = subs_count.get(sub, 0) + 1
                print(f"  [✓] RSS 探索成功: {len(subs_count)} 个候选", file=sys.stderr)
                break
            except urllib.error.HTTPError as e:
                print(f"  [!] RSS 探索失败: HTTP {e.code} (attempt {attempt+1})", file=sys.stderr)
                if e.code in (429, 503):
                    time.sleep(3 * (attempt + 1))
                elif e.code == 403:
                    time.sleep(5 * (attempt + 1))
                    break
            except Exception as e:
                print(f"  [!] RSS 探索异常: {str(e)[:80]}", file=sys.stderr)
                time.sleep(2)
        if subs_count:
            break

    candidates = {}
    for sub, count in subs_count.items():
        candidates[sub] = {
            "name": sub,
            "title": "",
            "subscribers": count * 50000,
        }
    return candidates


def main():
    keep = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 15

    with open(SUBS_FILE, encoding="utf-8") as f:
        subs = json.load(f)
    known = set()
    for c in subs["categories"]:
        for s in c["subs"]:
            name = s["name"] if isinstance(s, dict) else s
            known.add(name.lower())

    candidates = {}
    json_ok = False
    for page in (None, "?after=t5_2qrbh"):
        try:
            url = "https://www.reddit.com/subreddits/popular.json?limit=100" + (page or "")
            data = get_json(url)
            json_ok = True
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
            print(f"[!] JSON 榜单抓取失败: {str(e)[:100]}", file=sys.stderr)
        time.sleep(1.0)

    if not json_ok:
        print("[!] JSON API 全部被封，降级 RSS 发现热门版块", file=sys.stderr)
        candidates = fetch_popular_rss(known)

    top = sorted(candidates.values(), key=lambda x: -x["subscribers"])[:keep]
    out = {"updated": time.strftime("%Y-%m-%d %H:%M"), "candidates": top}
    with open(EXPLORE_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[✓] 探索完成：{len(top)} 个候选版块已写入 {EXPLORE_FILE}")
    for s in top:
        print(f"  r/{s['name']}  ({s['subscribers']/1000:.0f}k)  {s['title']}")


if __name__ == "__main__":
    main()
