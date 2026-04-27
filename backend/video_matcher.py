"""
video_matcher.py
선택한 기사들을 4대 방송사(JTBC, SBS, KBS, MBC) 유튜브 영상과 매칭

워크플로:
1. yt-dlp로 4개 채널의 최근 영상 메타데이터 수집
2. 4일 필터 적용
3. 각 기사에 대해 Claude로 매칭 영상 후보 추출 (핵심 키워드만 겹쳐도 매칭)
4. JSON으로 저장 (UI에서 읽음)

선결조건:
    pip install yt-dlp

실행:
    python video_matcher.py selected_articles.json
    python video_matcher.py selected_articles.json --debug
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yt_dlp
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ─── 설정 ──────────────────────────────────────────────
CHANNELS = {
    "JTBC": "UCsU-I-vHLiaMfV_ceaYz5rQ",
    "SBS":  "UCkinYTS9IHqOEwR1Sze2JTw",
    "KBS":  "UCcQTRi69dsVYHN3exePtZ1A",
    "MBC":  "UCF4Wxdo3inmxP-Y59wXDsFw",
}

DAYS_FILTER = 4
MAX_VIDEOS_PER_CHANNEL = 50      # yt-dlp로 채널당 최근 N개
MAX_CANDIDATES_PER_ARTICLE = 3
ANTHROPIC_MODEL = "claude-opus-4-5"  # 본인 프로젝트 모델로 수정


# ─── 1. yt-dlp로 영상 수집 ────────────────────────────
def fetch_channel_videos(channel_name: str, channel_id: str) -> list[dict]:
    """yt-dlp로 채널의 최근 영상 메타데이터 추출"""
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",      # 메타데이터만, 빠름
        "playlistend": MAX_VIDEOS_PER_CHANNEL,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"  ⚠ {channel_name} 가져오기 실패: {e}")
        return []

    entries = info.get("entries", []) if info else []
    videos = []
    for entry in entries:
        if not entry:
            continue
        try:
            video_id = entry.get("id")
            title    = entry.get("title")
            if not video_id or not title:
                continue

            # 업로드 시점: timestamp 또는 release_timestamp 중 있는 것
            ts = entry.get("timestamp") or entry.get("release_timestamp")
            published = (datetime.fromtimestamp(ts, tz=timezone.utc)
                         if ts else None)

            # 썸네일: thumbnails 리스트에서 가장 큰 거, 없으면 fallback URL
            thumbnails = entry.get("thumbnails") or []
            thumbnail = (thumbnails[-1]["url"] if thumbnails
                         else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")

            videos.append({
                "channel": channel_name,
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": thumbnail,
                "published": published.isoformat() if published else None,
            })
        except Exception as e:
            print(f"  ⚠ {channel_name} 항목 1개 스킵: {e}")
            continue

    return videos


def collect_all_videos(debug: bool = False) -> list[dict]:
    """4개 채널 영상 다 모으고 4일 필터"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_FILTER)
    all_videos = []

    for name, cid in CHANNELS.items():
        print(f"  → {name} 가져오는 중... (yt-dlp, 시간 좀 걸림)")
        videos = fetch_channel_videos(name, cid)

        # 4일 필터: published가 있고 cutoff 이내인 것만.
        # published가 None이면 일단 통과 (yt-dlp는 최신순이라 대체로 OK)
        recent = []
        unknown_date_count = 0
        for v in videos:
            if v["published"] is None:
                recent.append(v)
                unknown_date_count += 1
            else:
                pub_dt = datetime.fromisoformat(v["published"])
                if pub_dt >= cutoff:
                    recent.append(v)

        suffix = (f" (날짜 미상 {unknown_date_count}개 포함)"
                  if unknown_date_count else "")
        print(f"    {len(videos)}개 중 {len(recent)}개 (최근 {DAYS_FILTER}일{suffix})")
        all_videos.extend(recent)

    if debug:
        print("\n──── DEBUG: 수집된 영상 전체 목록 ────")
        for i, v in enumerate(all_videos):
            date_str = v["published"][:10] if v["published"] else "????-??-??"
            print(f"[{i:3d}] ({v['channel']}, {date_str}) {v['title']}")
        print("──── DEBUG 끝 ────\n")

    return all_videos


# ─── 2. Claude로 매칭 ─────────────────────────────────
def match_articles_to_videos(articles: list[dict],
                              videos: list[dict]) -> dict:
    """
    각 기사에 대해 가장 적합한 영상 후보 N개를 Claude가 골라줌
    매칭 기준: 핵심 인물/사건/장소 키워드가 1개라도 겹치면 매칭
    """
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    results = {}

    video_list_str = "\n".join(
        f"[{i}] ({v['channel']}) {v['title']}"
        for i, v in enumerate(videos)
    )

    for art in articles:
        art_id = art.get("id") or art["title"]
        prompt = f"""다음 신문 기사와 관련된 방송사 영상 후보를 최대 {MAX_CANDIDATES_PER_ARTICLE}개 골라주세요.

기사 제목: {art['title']}
기사 카테고리: {art.get('category', '미분류')}

영상 풀:
{video_list_str}

매칭 기준 (느슨하게):
- 기사의 핵심 인물(예: 트럼프, 이재용), 사건(예: 총격, 파업), 장소, 핵심 키워드 중
  하나라도 영상 제목에 등장하면 매칭으로 간주
- 영상 제목에 여러 토픽이 합쳐져 있을 수 있음 (예: "A // B" 형태). 부분만 겹쳐도 매칭
- 한국 방송사라 미국 지역 뉴스(달라스 등)는 매칭 안 될 수 있음 - 그 경우만 빈 리스트
- 의심스러우면 매칭하는 쪽으로 (false positive가 false negative보다 나음)

반환 형식 (JSON만, 다른 설명 금지):
{{"indices": [0, 5, 12]}}

매칭되는 영상이 정말 하나도 없으면:
{{"indices": []}}"""

        try:
            resp = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(text)
            indices = parsed.get("indices", [])
            matched = [videos[i] for i in indices if 0 <= i < len(videos)]
            results[art_id] = matched
            print(f"  ✓ {art['title'][:40]}... → {len(matched)}개 매칭")
            for m in matched:
                print(f"      • ({m['channel']}) {m['title'][:60]}")
        except Exception as e:
            print(f"  ⚠ 매칭 실패 ({art['title'][:40]}): {e}")
            results[art_id] = []

        time.sleep(0.3)

    return results


# ─── 3. 메인 ──────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("사용법: python video_matcher.py <selected_articles.json> [--debug]")
        sys.exit(1)

    debug = "--debug" in sys.argv
    articles_path = Path(sys.argv[1])
    articles = json.loads(articles_path.read_text(encoding="utf-8"))
    print(f"기사 {len(articles)}개 로드됨\n")

    print("[1/2] 방송사 영상 수집 (yt-dlp)")
    videos = collect_all_videos(debug=debug)
    print(f"\n총 영상 {len(videos)}개 수집됨\n")

    if not videos:
        print("영상이 없습니다. 종료.")
        return

    print("[2/2] Claude 매칭 중")
    results = match_articles_to_videos(articles, videos)

    output_path = articles_path.parent / "video_matches.json"
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n✓ 결과 저장: {output_path}")

    # UI가 읽을 수 있도록 ui_data 폴더에도 복사 (있으면)
    # 프로젝트 구조: backend/video_matcher.py, ui_data/는 backend의 형제
    ui_data_dir = articles_path.parent.parent / "ui_data"
    if ui_data_dir.exists():
        ui_path = ui_data_dir / "video_matches.json"
        ui_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"✓ UI에도 저장: {ui_path}")
    else:
        print(f"ⓘ UI 폴더 못 찾음 ({ui_data_dir}). 수동 복사 필요.")

    total = len(articles)
    matched = sum(1 for r in results.values() if r)
    print(f"\n매칭 결과: {matched}/{total} ({100*matched/total:.0f}%)")


if __name__ == "__main__":
    main()
