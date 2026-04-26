"""
build_ui_data.py - UI용 데이터 빌더

extractor + clusterer 결과를 합쳐서 UI가 한 번에 읽을 JSON 생성.

선택 정책:
- 한국스포츠: 제외
- 4일 넘은 기사: 제외
- 미국이민, 달라스텍사스한인: 전체 노출 (단, 같은 클러스터는 대표 1개)
- 그 외 카테고리: 클러스터 크기 큰 순으로 50개 (단, 같은 클러스터는 대표 1개)

카테고리 순서 (Top news 바로 아래):
- 달라스텍사스한인 (1순위 - 달라스 한인 영상 타겟)
- 한미외교
- 한국경제
- 미국이민
- 한국정치사회
- 흥미사건이벤트
- 기타

추가 처리:
- Google News 출처는 제목/도메인에서 진짜 매체명 추출
- published 시간을 ISO 8601로 통일 (실패 시 collected_at 사용)
- 카테고리 내 같은 클러스터는 대표 기사 1개만 노출 (중복 제거)

실행: python build_ui_data.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

OUTPUT_DIR = Path("output")
UI_DIR = Path("../ui_data")
TOP_NEWS_MIN_OUTLETS = 2

EXCLUDED_CATEGORIES = {"한국스포츠"}
UNLIMITED_CATEGORIES = {"미국이민", "달라스텍사스한인"}
PER_CATEGORY_LIMIT = 50

MAX_AGE_DAYS = 4

# ★ 새 카테고리 순서: 달라스 한인 영상 타겟에 맞춰 재배치
CATEGORY_ORDER = [
    "달라스텍사스한인",
    "한미외교",
    "한국경제",
    "미국이민",
    "한국정치사회",
    "흥미사건이벤트",
    "기타",
]

SOURCE_PRIORITY = {
    "한겨레": 10, "경향신문": 10, "오마이뉴스": 10,
    "조선일보": 9, "중앙일보": 9, "동아일보": 9,
    "연합뉴스": 9, "뉴스1": 8, "뉴시스": 8,
    "매일경제": 8, "한국경제": 8,
    "KBS": 7, "MBC": 7, "SBS": 7, "JTBC": 7, "YTN": 7,
    "BBC": 7,
}

DOMAIN_TO_SOURCE = {
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",
    "ohmynews.com": "오마이뉴스",
    "mk.co.kr": "매일경제",
    "hankyung.com": "한국경제",
    "chosun.com": "조선일보",
    "joins.com": "중앙일보",
    "joongang.co.kr": "중앙일보",
    "donga.com": "동아일보",
    "yna.co.kr": "연합뉴스",
    "yonhapnews.co.kr": "연합뉴스",
    "ytn.co.kr": "YTN",
    "kbs.co.kr": "KBS",
    "imbc.com": "MBC",
    "sbs.co.kr": "SBS",
    "jtbc.co.kr": "JTBC",
    "newsis.com": "뉴시스",
    "news1.kr": "뉴스1",
    "mt.co.kr": "머니투데이",
    "edaily.co.kr": "이데일리",
    "hankookilbo.com": "한국일보",
    "munhwa.com": "문화일보",
    "kookje.co.kr": "국제신문",
    "busan.com": "부산일보",
    "kmib.co.kr": "국민일보",
    "segye.com": "세계일보",
    "naver.com": "네이버뉴스",
    "daum.net": "다음뉴스",
    "v.daum.net": "다음뉴스",
    "brunch.co.kr": "브런치",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "koreatimes.com": "한국일보 미주",
    "koreadaily.com": "미주중앙일보",
    "atlantajoongang.com": "애틀랜타 중앙일보",
    "worldkorean.net": "월드코리안뉴스",
    "dongponews.net": "재외동포신문",
    "radiokorea.com": "라디오코리아",
    "ajunews.com": "아주경제",
    "etoday.co.kr": "이투데이",
    "newspim.com": "뉴스핌",
    "sedaily.com": "서울경제",
    "asiae.co.kr": "아시아경제",
    "fnnews.com": "파이낸셜뉴스",
    "metroseoul.co.kr": "메트로신문",
    "newsen.com": "뉴스엔",
    "channela.com": "채널A",
    "tvchosun.com": "TV조선",
    "mbn.co.kr": "MBN",
    "newdaily.co.kr": "뉴데일리",
    "pressian.com": "프레시안",
}


def _parse_date_to_iso(date_str):
    if not date_str:
        return None
    s = str(date_str).strip()
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    return None


def _extract_source_from_title(title):
    if not title:
        return None
    if " - " in title:
        candidate = title.rsplit(" - ", 1)[1].strip()
        if 1 <= len(candidate) <= 30:
            return candidate
    return None


def _extract_source_from_url(url):
    if not url:
        return None
    try:
        host = urlparse(url).hostname or ""
        host = host.replace("www.", "").lower()
        if host in DOMAIN_TO_SOURCE:
            return DOMAIN_TO_SOURCE[host]
        for domain, name in DOMAIN_TO_SOURCE.items():
            if host.endswith(domain):
                return name
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2]
    except Exception:
        pass
    return None


def _resolve_source(orig_source, title, url):
    if not orig_source:
        return _extract_source_from_url(url) or "Unknown"
    if "Google News" in orig_source or "GoogleNews" in orig_source.replace(" ", ""):
        from_title = _extract_source_from_title(title)
        if from_title:
            return from_title
        from_url = _extract_source_from_url(url)
        if from_url:
            return from_url
    return orig_source


def _clean_title(title):
    if not title:
        return ""
    if " - " in title:
        head, tail = title.rsplit(" - ", 1)
        if 1 <= len(tail.strip()) <= 30:
            return head.strip()
    return title.strip()


def _ts_for_sort(iso_str):
    if not iso_str:
        return 0
    try:
        return int(datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def _representative_score(article):
    """클러스터 내 대표 기사 선정 점수. 본문 > 사진 > 매체 > 최신."""
    score = 0
    if article.get("has_body"):
        score += 1000
    if article.get("has_image"):
        score += 500
    src = article.get("source", "")
    score += SOURCE_PRIORITY.get(src, 0) * 10
    score += _ts_for_sort(article.get("published", "")) // 100000
    return score


def _dedupe_by_cluster(articles):
    """같은 cluster_id인 기사는 대표 1개만 남김."""
    by_cluster = {}
    no_cluster = []
    for a in articles:
        cid = a.get("cluster_id")
        if not cid:
            no_cluster.append(a)
            continue
        if cid not in by_cluster:
            by_cluster[cid] = a
        else:
            if _representative_score(a) > _representative_score(by_cluster[cid]):
                by_cluster[cid] = a
    return list(by_cluster.values()) + no_cluster


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_for_date(date_stem):
    extracted_path = OUTPUT_DIR / f"{date_stem}_extracted.json"
    clustered_path = OUTPUT_DIR / f"{date_stem}_clustered.json"

    if not extracted_path.exists():
        print(f"  ⚠️ 스킵: {extracted_path.name} 없음")
        return None
    if not clustered_path.exists():
        print(f"  ⚠️ 스킵: {clustered_path.name} 없음")
        return None

    extracted = load_json(extracted_path)
    clustered = load_json(clustered_path)

    body_by_url = {}
    for a in extracted.get("articles", []):
        body_by_url[a["url"]] = {
            "body": a.get("body", ""),
            "image_url": a.get("image_url"),
        }

    all_articles_full = []
    for art in clustered.get("articles", []):
        url = art.get("link") or art.get("url")
        body_data = body_by_url.get(url, {})

        raw_title = art.get("title", "")
        clean_title = _clean_title(raw_title)
        resolved_source = _resolve_source(art.get("source", ""), raw_title, url)

        published_iso = _parse_date_to_iso(art.get("published"))
        if not published_iso:
            published_iso = _parse_date_to_iso(art.get("collected_at"))
        if not published_iso:
            published_iso = datetime.now(timezone.utc).isoformat()

        all_articles_full.append({
            "id": url,
            "title": clean_title,
            "url": url,
            "source": resolved_source,
            "category": art.get("category", "기타"),
            "published": published_iso,
            "summary": art.get("summary", "")[:300],
            "body": body_data.get("body", ""),
            "image_url": body_data.get("image_url"),
            "cluster_id": art.get("cluster_id"),
            "cluster_size": art.get("cluster_size", 1),
            "has_body": bool(body_data.get("body")),
            "has_image": bool(body_data.get("image_url")),
        })

    print(f"  📊 원본 기사: {len(all_articles_full)}개")

    # 한국스포츠 제외
    excluded_count = sum(1 for a in all_articles_full if a["category"] in EXCLUDED_CATEGORIES)
    all_articles_full = [a for a in all_articles_full if a["category"] not in EXCLUDED_CATEGORIES]
    if excluded_count:
        print(f"  🚫 제외 ({', '.join(EXCLUDED_CATEGORIES)}): {excluded_count}개")

    # 4일 넘은 기사 제외
    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff_ts = now_ts - (MAX_AGE_DAYS * 86400)

    def is_recent(article):
        ts = _ts_for_sort(article.get("published", ""))
        return ts >= cutoff_ts

    old_count = sum(1 for a in all_articles_full if not is_recent(a))
    all_articles_full = [a for a in all_articles_full if is_recent(a)]
    if old_count:
        print(f"  ⏰ 제외 ({MAX_AGE_DAYS}일 초과): {old_count}개")

    # 클러스터 정보 (필터링 후의 기사로 계산)
    cluster_sources = {}
    for a in all_articles_full:
        cid = a["cluster_id"]
        if not cid:
            continue
        cluster_sources.setdefault(cid, set()).add(a["source"])

    # 카테고리별 노출 + 클러스터 중복 제거
    by_category_full = {}
    for a in all_articles_full:
        cat = a.get("category", "기타")
        by_category_full.setdefault(cat, []).append(a)

    final_articles = []
    print(f"  📂 카테고리별 적용:")
    for cat, articles in by_category_full.items():
        before_dedup = len(articles)
        deduped = _dedupe_by_cluster(articles)
        dedup_diff = before_dedup - len(deduped)

        deduped.sort(key=lambda a: (-a.get("cluster_size", 1), -_ts_for_sort(a.get("published", ""))))

        if cat in UNLIMITED_CATEGORIES:
            kept = deduped
            print(f"      └ {cat}: {len(kept)}개 (전체, 클러스터 중복 -{dedup_diff})")
        else:
            kept = deduped[:PER_CATEGORY_LIMIT]
            print(f"      └ {cat}: {len(kept)}개 (제한 {PER_CATEGORY_LIMIT}, 원본 {before_dedup}, 클러스터 중복 -{dedup_diff})")
        final_articles.extend(kept)

    print(f"  ✅ 최종 기사: {len(final_articles)}개")

    # Top news
    top_cluster_ids = [
        cid for cid, sources in cluster_sources.items()
        if len(sources) >= TOP_NEWS_MIN_OUTLETS
    ]
    top_cluster_ids.sort(key=lambda cid: -len(cluster_sources[cid]))

    top_news_ids = []
    for cid in top_cluster_ids:
        candidates = [a for a in final_articles if a["cluster_id"] == cid]
        if candidates:
            top_news_ids.append(candidates[0]["id"])

    # 카테고리별 정리
    by_category_final = {}
    for a in final_articles:
        cat = a.get("category", "기타")
        by_category_final.setdefault(cat, []).append(a["id"])

    ordered_categories = []
    for cat in CATEGORY_ORDER:
        if cat in by_category_final:
            ordered_categories.append({
                "name": cat,
                "count": len(by_category_final[cat]),
                "article_ids": by_category_final[cat],
            })
    for cat in by_category_final:
        if cat not in CATEGORY_ORDER:
            ordered_categories.append({
                "name": cat,
                "count": len(by_category_final[cat]),
                "article_ids": by_category_final[cat],
            })

    return {
        "date": date_stem,
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "total_articles": len(final_articles),
            "with_body": sum(1 for a in final_articles if a["has_body"]),
            "with_image": sum(1 for a in final_articles if a["has_image"]),
            "top_news_count": len(top_news_ids),
            "categories": len(ordered_categories),
        },
        "articles": final_articles,
        "top_news_ids": top_news_ids,
        "categories": ordered_categories,
        "cluster_info": {
            cid: {
                "size": len(cluster_sources.get(cid, [])),
                "sources": sorted(cluster_sources.get(cid, [])),
            }
            for cid in top_cluster_ids
        },
    }


def main():
    UI_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print(f"  🎨 UI 데이터 빌드  ({datetime.now().strftime('%H:%M:%S')})")
    print(f"  ⏰ {MAX_AGE_DAYS}일 넘은 기사 제외")
    print(f"  📂 카테고리 순서: {' > '.join(CATEGORY_ORDER)}")
    print("=" * 70)

    extracted_files = sorted(OUTPUT_DIR.glob("*_extracted.json"))
    dates = [f.stem.replace("_extracted", "") for f in extracted_files]

    if not dates:
        print("❌ output/ 에 *_extracted.json 파일이 없습니다.")
        return

    print(f"\n📅 처리할 날짜: {len(dates)}개")
    for d in dates:
        print(f"  - {d}")

    available_dates = []
    for date_stem in dates:
        print(f"\n📦 빌드: {date_stem}")
        data = build_for_date(date_stem)
        if data is None:
            continue
        out_path = UI_DIR / f"{date_stem}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        size_kb = out_path.stat().st_size / 1024
        print(f"  💾 {out_path.name} ({size_kb:.0f} KB)")
        print(f"     본문 {data['stats']['with_body']}개, "
              f"사진 {data['stats']['with_image']}개, "
              f"Top news {data['stats']['top_news_count']}개")
        available_dates.append({
            "date": date_stem,
            "total": data["stats"]["total_articles"],
            "with_body": data["stats"]["with_body"],
        })

    sorted_dates = sorted(available_dates, key=lambda x: x["date"], reverse=True)
    index = {
        "generated_at": datetime.now().isoformat(),
        "dates": sorted_dates,
        "latest": sorted_dates[0]["date"] if sorted_dates else None,
    }
    index_path = UI_DIR / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n💾 인덱스: {index_path}")
    print(f"  - 사용 가능 날짜: {len(available_dates)}개")
    print(f"  - 최신: {index['latest']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
