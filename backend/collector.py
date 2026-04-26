"""
뉴스 RSS 수집기 + 스크래핑
- RSS: 13개 소스
- 스크래핑: KTN, 주간포커스, 달코라
- Google News URL은 병렬로 디코딩하여 원본 URL로 저장
"""
import feedparser
import requests
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from googlenewsdecoder import gnewsdecoder
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collectors.scraper_ktn import collect_ktn
from collectors.scraper_focus import collect_focus
from collectors.scraper_dalkora import collect_dalkora

RSS_SOURCES = {
    "한겨레": {
        "url": "https://www.hani.co.kr/rss/",
        "category_hint": "한국정치사회",
        "lang": "ko"
    },
    "경향신문": {
        "url": "https://www.khan.co.kr/rss/rssdata/total_news.xml",
        "category_hint": "한국정치사회",
        "lang": "ko"
    },
    "오마이뉴스": {
        "url": "https://rss.ohmynews.com/rss/ohmynews.xml",
        "category_hint": "한국정치사회",
        "lang": "ko"
    },
    "매일경제": {
        "url": "https://www.mk.co.kr/rss/30000001/",
        "category_hint": "한국경제",
        "lang": "ko"
    },
    "한국경제": {
        "url": "https://www.hankyung.com/feed/all-news",
        "category_hint": "한국경제",
        "lang": "ko"
    },
    "Google News 한국": {
        "url": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
        "category_hint": "한국일반",
        "lang": "ko"
    },
    "Google News 미국이민": {
        "url": "https://news.google.com/rss/search?q=미국+이민+한인&hl=ko&gl=KR&ceid=KR:ko",
        "category_hint": "미국이민",
        "lang": "ko"
    },
    "Google News 한미외교": {
        "url": "https://news.google.com/rss/search?q=한미+외교&hl=ko&gl=KR&ceid=KR:ko",
        "category_hint": "한미외교",
        "lang": "ko"
    },
    "Google News 달라스한인": {
        "url": "https://news.google.com/rss/search?q=달라스+한인&hl=ko&gl=KR&ceid=KR:ko",
        "category_hint": "달라스한인",
        "lang": "ko"
    },
    "Google News H1B": {
        "url": "https://news.google.com/rss/search?q=H1B+비자+이민&hl=ko&gl=KR&ceid=KR:ko",
        "category_hint": "미국이민",
        "lang": "ko"
    },
    "BBC 코리아": {
        "url": "https://feeds.bbci.co.uk/korean/rss.xml",
        "category_hint": "국제",
        "lang": "ko"
    },
    "CNN Top": {
        "url": "http://rss.cnn.com/rss/cnn_topstories.rss",
        "category_hint": "국제",
        "lang": "en"
    },
    "BBC News": {
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "category_hint": "국제",
        "lang": "en"
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Google News 디코딩 설정
GNEWS_DECODE_INTERVAL = 1    # 각 워커가 디코딩 사이 대기 (초)
GNEWS_PARALLEL_WORKERS = 10  # 동시 디코딩 개수


def decode_google_news_url(google_url):
    """Google News redirect URL을 원본 URL로 디코딩. 실패 시 None."""
    try:
        result = gnewsdecoder(google_url, interval=GNEWS_DECODE_INTERVAL)
        if result.get("status"):
            return result.get("decoded_url")
        return None
    except Exception:
        return None


def collect_from_source(name, source):
    articles = []
    is_google_news = "news.google.com" in source["url"]

    try:
        response = requests.get(source["url"], headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  ❌ {name}: HTTP {response.status_code}")
            return articles

        feed = feedparser.parse(response.content)
        entries = list(feed.entries)
        total_entries = len(entries)

        if is_google_news:
            # Google News: 병렬 디코딩
            print(f"  🔓 {name}: {total_entries}개 URL 병렬 디코딩 중... (워커 {GNEWS_PARALLEL_WORKERS}개)")
            start_time = time.time()

            def decode_task(link):
                return link, decode_google_news_url(link)

            links_to_decode = [e.get("link", "").strip() for e in entries if e.get("link")]
            decoded_links = {}

            with ThreadPoolExecutor(max_workers=GNEWS_PARALLEL_WORKERS) as executor:
                futures = [executor.submit(decode_task, link) for link in links_to_decode]
                for future in as_completed(futures):
                    orig, decoded = future.result()
                    decoded_links[orig] = decoded

            decoded_count = 0
            failed_count = 0
            for entry in entries:
                orig_link = entry.get("link", "").strip()
                decoded = decoded_links.get(orig_link)
                if not decoded:
                    failed_count += 1
                    continue
                decoded_count += 1
                article = {
                    "source": name,
                    "category_hint": source["category_hint"],
                    "lang": source["lang"],
                    "title": entry.get("title", "").strip(),
                    "link": decoded,
                    "summary": entry.get("summary", "").strip()[:500],
                    "published": entry.get("published", ""),
                    "collected_at": datetime.now().isoformat(),
                }
                if article["title"] and article["link"]:
                    articles.append(article)

            elapsed = time.time() - start_time
            print(f"  ✅ {name}: {len(articles)}개 (디코딩 성공 {decoded_count}, 실패 {failed_count}, {elapsed:.1f}초)")

        else:
            # 일반 RSS: 그대로
            for entry in entries:
                article = {
                    "source": name,
                    "category_hint": source["category_hint"],
                    "lang": source["lang"],
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", "").strip(),
                    "summary": entry.get("summary", "").strip()[:500],
                    "published": entry.get("published", ""),
                    "collected_at": datetime.now().isoformat(),
                }
                if article["title"] and article["link"]:
                    articles.append(article)
            print(f"  ✅ {name}: {len(articles)}개")

    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:80]}")
    return articles


def deduplicate(articles):
    seen = set()
    unique = []
    for article in articles:
        key = article["link"]
        if key not in seen:
            seen.add(key)
            unique.append(article)
    return unique


def save_articles(articles, output_dir="output"):
    Path(output_dir).mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    json_path = f"{output_dir}/{today}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": today,
            "collected_at": datetime.now().isoformat(),
            "total": len(articles),
            "articles": articles
        }, f, ensure_ascii=False, indent=2)

    md_path = f"{output_dir}/{today}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 📰 뉴스 수집 - {today}\n\n")
        f.write(f"**수집 시간**: {datetime.now().strftime('%H:%M:%S')}\n")
        f.write(f"**총 기사 수**: {len(articles)}개\n\n")

        by_category = {}
        for a in articles:
            cat = a["category_hint"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(a)

        f.write("## 📊 카테고리별 통계\n\n")
        for cat, items in sorted(by_category.items(), key=lambda x: -len(x[1])):
            f.write(f"- **{cat}**: {len(items)}개\n")
        f.write("\n---\n\n")

        for cat in sorted(by_category.keys(), key=lambda x: -len(by_category[x])):
            items = by_category[cat]
            f.write(f"## {cat} ({len(items)}개)\n\n")
            for i, a in enumerate(items, 1):
                f.write(f"### {i}. {a['title']}\n")
                f.write(f"- **출처**: {a['source']}\n")
                f.write(f"- **링크**: {a['link']}\n")
                if a["published"]:
                    f.write(f"- **발행**: {a['published']}\n")
                f.write("\n")

    return json_path, md_path


def main():
    print(f"\n{'='*70}")
    print(f"  📰 뉴스 수집 시작  ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"{'='*70}\n")

    overall_start = time.time()
    all_articles = []

    print("📡 RSS 소스")
    for name, source in RSS_SOURCES.items():
        articles = collect_from_source(name, source)
        all_articles.extend(articles)

    print("\n🕷️ 스크래핑")

    ktn_articles = collect_ktn()
    all_articles.extend(ktn_articles)

    focus_articles = collect_focus()
    all_articles.extend(focus_articles)

    dalkora_articles = collect_dalkora()
    all_articles.extend(dalkora_articles)

    print(f"\n📊 수집 결과")
    print(f"  - 전체: {len(all_articles)}개")

    unique_articles = deduplicate(all_articles)
    print(f"  - 중복 제거 후: {len(unique_articles)}개")

    json_path, md_path = save_articles(unique_articles)
    print(f"\n💾 저장 완료")
    print(f"  - JSON: {json_path}")
    print(f"  - Markdown: {md_path}")

    by_category = {}
    for a in unique_articles:
        cat = a["category_hint"]
        by_category[cat] = by_category.get(cat, 0) + 1

    print(f"\n📂 카테고리별:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  - {cat}: {count}개")

    elapsed = time.time() - overall_start
    print(f"\n⏱️ 총 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()