"""
Claude로 기사 카테고리 정확히 분류
- 706개 기사 일괄 처리
- 7개 카테고리로 자동 분류
- 결과를 categorized.json으로 저장
"""
import json
import os
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

# .env에서 API 키 로드
load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 7개 메인 카테고리 (본인 관심사)
CATEGORIES = [
    "미국이민",          # H-1B, 영주권, DACA, 비자 등
    "한국경제",          # 한국 주가, 부동산, 산업
    "한미외교",          # 한미 관계, 정상회담, 무역
    "한국정치사회",      # 한국 정치, 사회 이슈
    "한국스포츠",        # 축구, 야구, 김민재, 손흥민 등
    "달라스텍사스한인",  # 텍사스 로컬 한인 소식
    "흥미사건이벤트",    # 사건사고, 화제, 흥미
    "기타",              # 위에 안 맞는 것
]


def classify_batch(articles_batch: list) -> list:
    """
    기사 배치를 한 번에 분류 (효율성)
    - 한 번에 20개씩 묶어서 Claude한테 보냄
    - 토큰 절약 + 빠름
    """
    
    # 분류용 입력 만들기
    items_text = ""
    for i, art in enumerate(articles_batch):
        # 제목 + 출처만 (요약은 너무 김)
        items_text += f"[{i}] {art['title']} (출처: {art['source']})\n"
    
    prompt = f"""다음 뉴스 기사들을 정확한 카테고리로 분류해주세요.

카테고리 목록:
- 미국이민: H-1B, 영주권, DACA, 미국 비자, 이민 정책, 한인 미국 이민
- 한국경제: 한국 주가, 부동산, 기업, 금리, 산업, 무역
- 한미외교: 한미 정상회담, 무역협상, 관세, 동맹, 주한미군
- 한국정치사회: 한국 국내 정치, 정당, 선거, 사회 이슈, 사건
- 한국스포츠: 축구, 야구, 김민재, 손흥민, 류현진 등 한국 선수
- 달라스텍사스한인: 텍사스/달라스 한인 사회, 행사, 사업, 사건
- 흥미사건이벤트: 화제, 충격, 흥미로운 사건, 이벤트, 트렌드
- 기타: 위에 정확히 안 맞는 것

기사 목록:
{items_text}

각 기사 번호에 대해 가장 정확한 카테고리 1개만 선택해주세요.
JSON 배열로만 응답:
[{{"id": 0, "category": "미국이민"}}, {{"id": 1, "category": "한국경제"}}, ...]"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # 빠르고 저렴
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text
        
        # JSON 파싱 (가끔 ```json ``` 감싸서 옴)
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        classifications = json.loads(result_text)
        
        # 결과를 원본 기사에 적용
        for cls in classifications:
            idx = cls["id"]
            if 0 <= idx < len(articles_batch):
                articles_batch[idx]["category"] = cls["category"]
        
        # 분류 안 된 거는 "기타"
        for art in articles_batch:
            if "category" not in art:
                art["category"] = "기타"
        
        return articles_batch
    
    except Exception as e:
        print(f"  ⚠️ 배치 분류 실패: {e}")
        # 실패 시 카테고리 힌트 그대로 사용
        for art in articles_batch:
            art["category"] = art.get("category_hint", "기타")
        return articles_batch


def categorize_all(articles: list, batch_size: int = 20) -> list:
    """전체 기사를 배치로 나눠서 분류"""
    total = len(articles)
    batches = [articles[i:i+batch_size] for i in range(0, total, batch_size)]
    
    print(f"📦 {total}개 기사를 {len(batches)}개 배치로 처리\n")
    
    for i, batch in enumerate(batches, 1):
        print(f"  [{i}/{len(batches)}] {len(batch)}개 분류 중...", end=" ", flush=True)
        classify_batch(batch)
        print("✅")
    
    return articles


def save_results(articles: list, output_dir: str = "output"):
    """결과 저장"""
    Path(output_dir).mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # JSON 저장
    json_path = f"{output_dir}/{today}_categorized.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": today,
            "total": len(articles),
            "articles": articles
        }, f, ensure_ascii=False, indent=2)
    
    # Markdown 저장 (카테고리별 정리)
    md_path = f"{output_dir}/{today}_categorized.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 📰 카테고리별 뉴스 - {today}\n\n")
        
        # 카테고리별 그룹화
        by_category = {}
        for a in articles:
            cat = a.get("category", "기타")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(a)
        
        # 통계
        f.write("## 📊 카테고리별 통계\n\n")
        for cat in CATEGORIES:
            count = len(by_category.get(cat, []))
            if count > 0:
                f.write(f"- **{cat}**: {count}개\n")
        f.write("\n---\n\n")
        
        # 카테고리별 기사
        for cat in CATEGORIES:
            items = by_category.get(cat, [])
            if not items:
                continue
            
            f.write(f"## {cat} ({len(items)}개)\n\n")
            
            for i, a in enumerate(items, 1):
                f.write(f"### {i}. {a['title']}\n")
                f.write(f"- **출처**: {a['source']}\n")
                f.write(f"- **링크**: {a['link']}\n")
                f.write("\n")
    
    return json_path, md_path


def main():
    print(f"\n{'='*70}")
    print(f"  🤖 Claude 카테고리 분류  ({datetime.now().strftime('%H:%M:%S')})")
    print(f"{'='*70}\n")
    
    # 오늘 수집한 데이터 로드
    today = datetime.now().strftime("%Y-%m-%d")
    input_path = f"output/{today}.json"
    
    if not os.path.exists(input_path):
        print(f"❌ {input_path} 파일이 없어요. 먼저 collector.py 실행해주세요.")
        return
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    articles = data["articles"]
    print(f"📂 로드: {len(articles)}개 기사\n")
    
    # 분류 시작
    categorized = categorize_all(articles)
    
    # 통계
    by_category = {}
    for a in categorized:
        cat = a.get("category", "기타")
        by_category[cat] = by_category.get(cat, 0) + 1
    
    print(f"\n📊 분류 결과:")
    for cat in CATEGORIES:
        if cat in by_category:
            print(f"  - {cat}: {by_category[cat]}개")
    
    # 저장
    json_path, md_path = save_results(categorized)
    print(f"\n💾 저장 완료")
    print(f"  - JSON: {json_path}")
    print(f"  - Markdown: {md_path}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()