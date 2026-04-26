"""
extractor.py - 본문/사진 추출

선택 기준:
- 미국이민, 달라스텍사스한인: 전체
- 그 외 카테고리: cluster_size 큰 순 + 최신순으로 50개

실행: python extractor.py
입력: output/{date}_clustered.json
출력: output/{date}_extracted.json (50개마다 중간 저장)
"""

import json
import time
from datetime import datetime
from pathlib import Path
import trafilatura
import requests
from bs4 import BeautifulSoup

# ===== 설정 =====
PRIORITY_CATEGORIES = {"미국이민", "달라스텍사스한인"}
OTHER_LIMIT = 50
DELAY_SECONDS = 1.5
TIMEOUT_SECONDS = 15
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
MIN_BODY_LENGTH = 200  # 이미 본문 있으면 재추출 스킵
DEBUG_FIRST_N = 5      # 첫 N개는 상세 진단 출력

OUTPUT_DIR = Path("output")


def load_clustered():
    """가장 최근 clustered JSON 로드"""
    files = sorted(OUTPUT_DIR.glob("*_clustered.json"))
    if not files:
        raise FileNotFoundError("output/ 에 *_clustered.json 파일이 없습니다")
    latest = files[-1]
    print(f"📂 로드: {latest.name}")
    with open(latest, "r", encoding="utf-8") as f:
        return json.load(f), latest.stem.replace("_clustered", "")


def flatten_articles(clustered):
    """평탄한 articles 배열 + cluster_id 기반 topic_title 매핑"""
    articles = clustered.get("articles", [])

    # cluster_id → 대표 제목 매핑
    clusters = clustered.get("clusters", [])
    topic_title_by_cid = {}
    if clusters:
        for c in clusters:
            cid = c.get("cluster_id") or c.get("id")
            title = c.get("title") or c.get("representative_title")
            if cid and title:
                topic_title_by_cid[cid] = title

    # clusters 정보 부족하면 articles에서 첫 기사 제목을 대표로
    if not topic_title_by_cid:
        for art in articles:
            cid = art.get("cluster_id")
            if cid and cid not in topic_title_by_cid:
                topic_title_by_cid[cid] = art.get("title")

    flat = []
    for art in articles:
        cid = art.get("cluster_id")
        flat.append({
            **art,
            "url": art.get("link") or art.get("url"),
            "topic_id": cid,
            "topic_title": topic_title_by_cid.get(cid, art.get("title")),
        })
    return flat


def _parse_date(s):
    if not s:
        return 0
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def select_articles(all_articles):
    """한인/이민 전체 + 그 외 50개 (cluster_size 큰 순, 동률은 최신순)"""
    priority = [a for a in all_articles if a.get("category") in PRIORITY_CATEGORIES]
    others = [a for a in all_articles if a.get("category") not in PRIORITY_CATEGORIES]

    others.sort(key=lambda a: (
        -a.get("cluster_size", 1),
        -_parse_date(a.get("published") or a.get("collected_at") or ""),
    ))
    selected_others = others[:OTHER_LIMIT]

    print(f"\n📋 선택된 기사")
    print(f"  - 우선 카테고리 (전체): {len(priority)}개")
    by_cat = {}
    for a in priority:
        c = a.get("category", "?")
        by_cat[c] = by_cat.get(c, 0) + 1
    for cat, n in by_cat.items():
        print(f"      └ {cat}: {n}개")

    print(f"  - 그 외 (Top {OTHER_LIMIT}): {len(selected_others)}개")
    by_cat2 = {}
    for a in selected_others:
        c = a.get("category", "?")
        by_cat2[c] = by_cat2.get(c, 0) + 1
    for cat, n in sorted(by_cat2.items()):
        print(f"      └ {cat}: {n}개")
    print(f"  - 합계: {len(priority) + len(selected_others)}개")

    return priority + selected_others


def extract_image_url(html):
    """og:image → twitter:image → 본문 첫 이미지"""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for prop in ("og:image", "twitter:image", "twitter:image:src"):
            tag = (
                soup.find("meta", attrs={"property": prop})
                or soup.find("meta", attrs={"name": prop})
            )
            if tag and tag.get("content"):
                return tag["content"]
        article_tag = soup.find("article") or soup
        img = article_tag.find("img")
        if img and img.get("src"):
            return img["src"]
    except Exception:
        pass
    return None


def extract_one(article, session, debug=False):
    """한 기사 본문/사진 추출. (result_dict, error_str) 반환"""
    url = article.get("url") or article.get("link")
    if not url:
        return None, "URL 없음"

    existing_body = article.get("body") or article.get("content") or ""
    if len(existing_body) >= MIN_BODY_LENGTH:
        return {
            "body": existing_body,
            "image_url": article.get("image_url") or article.get("image"),
            "extracted_via": "existing",
        }, None

    try:
        resp = session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        if debug:
            print(f"      🔬 status={resp.status_code} html_len={len(resp.text)}")
            print(f"      🔬 final_url={str(resp.url)[:100]}")
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return None, f"fetch 실패: {type(e).__name__}: {str(e)[:80]}"

    body = trafilatura.extract(
        html,
        favor_recall=True,
        include_comments=False,
        include_tables=False,
    ) or ""

    if debug:
        print(f"      🔬 trafilatura 본문 길이: {len(body)}자")
        print(f"      🔬 html 미리보기: {html[:200]!r}")

    if len(body) < 100:
        return None, f"본문 너무 짧음 ({len(body)}자, html={len(html)}자)"

    return {
        "body": body,
        "image_url": extract_image_url(html),
        "extracted_via": "fetch",
    }, None


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print(f"  📰 본문/사진 추출  ({datetime.now().strftime('%H:%M:%S')})")
    print("=" * 70)

    clustered, date_stem = load_clustered()
    all_articles = flatten_articles(clustered)
    print(f"📊 전체 기사: {len(all_articles)}개")

    selected = select_articles(all_articles)

    print(f"\n🌐 추출 시작 (요청 간격 {DELAY_SECONDS}s, 타임아웃 {TIMEOUT_SECONDS}s)")
    print(f"    첫 {DEBUG_FIRST_N}개는 진단 모드 (status/length 표시)")
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    extracted = []
    failures = []
    total = len(selected)
    output_path = OUTPUT_DIR / f"{date_stem}_extracted.json"

    def save_progress():
        payload = {
            "extracted_at": datetime.now().isoformat(),
            "stats": {
                "selected": total,
                "success": len(extracted),
                "failed": len(failures),
                "with_image": sum(1 for a in extracted if a["image_url"]),
            },
            "articles": extracted,
            "failures": failures,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    for i, art in enumerate(selected, 1):
        title = (art.get("title") or "")[:50]
        debug = i <= DEBUG_FIRST_N

        if debug:
            print(f"\n  [{i}/{total}] 🔬 진단: {title}")
            print(f"      URL: {(art.get('url') or art.get('link') or '')[:100]}")

        result, err = extract_one(art, session, debug=debug)

        if result:
            extracted.append({
                "url": art.get("url") or art.get("link"),
                "title": art.get("title"),
                "source": art.get("source"),
                "category": art.get("category"),
                "topic_id": art.get("topic_id"),
                "topic_title": art.get("topic_title"),
                "cluster_size": art.get("cluster_size", 1),
                "published": art.get("published") or art.get("collected_at"),
                "body": result["body"],
                "image_url": result["image_url"],
                "extracted_via": result["extracted_via"],
                "extracted_at": datetime.now().isoformat(),
            })
            mark = "🖼️" if result["image_url"] else "📝"
            print(f"  [{i}/{total}] {mark} {title}")
        else:
            failures.append({
                "url": art.get("url") or art.get("link"),
                "title": art.get("title"),
                "source": art.get("source"),
                "reason": err,
            })
            print(f"  [{i}/{total}] ❌ {title} → {err}")

        # 50개마다 중간 저장
        if i % 50 == 0:
            save_progress()
            print(f"      💾 중간 저장 ({i}/{total}, 성공 {len(extracted)} / 실패 {len(failures)})")

        # 실제 fetch한 경우만 대기
        if i < total and result and result.get("extracted_via") == "fetch":
            time.sleep(DELAY_SECONDS)

    save_progress()

    print(f"\n📊 결과")
    print(f"  - 성공: {len(extracted)}개")
    print(f"  - 실패: {len(failures)}개")
    print(f"  - 사진 있음: {sum(1 for a in extracted if a['image_url'])}개")
    print(f"  - 카테고리별 성공:")
    by_cat = {}
    for a in extracted:
        c = a.get("category", "?")
        by_cat[c] = by_cat.get(c, 0) + 1
    for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"      └ {cat}: {n}개")

    # 실패 사유 통계
    if failures:
        print(f"\n  - 실패 사유 Top 5:")
        reason_count = {}
        for f in failures:
            key = f["reason"][:60]
            reason_count[key] = reason_count.get(key, 0) + 1
        for reason, n in sorted(reason_count.items(), key=lambda x: -x[1])[:5]:
            print(f"      └ [{n}회] {reason}")

    print(f"\n💾 저장: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()