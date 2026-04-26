"""
토픽 클러스터링 - 같은 사건 다룬 기사들 묶기
- OpenAI 임베딩으로 의미 유사도 계산
- 코사인 유사도 0.55 이상 = 같은 토픽
- Top 기사 자동 선정 (고유 매체 수 기준)
- 카테고리별 다른 처리:
  * 핵심 카테고리 (이민/경제/외교/정치): 중복 보도 위주
  * 로컬/스포츠/흥미: 모든 기사
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 같은 토픽 판정 임계값
SIMILARITY_THRESHOLD = 0.55

# 핵심 카테고리 - 중복 보도 위주로 보여줌
CORE_CATEGORIES = ["미국이민", "한미외교", "한국경제", "한국정치사회"]

# 로컬/기타 카테고리 - 모든 기사 보여줌
LOCAL_CATEGORIES = ["달라스텍사스한인", "한국스포츠", "흥미사건이벤트"]


def get_embeddings_batch(texts, batch_size=100):
    """텍스트들을 임베딩 벡터로 변환"""
    all_embeddings = []
    total_batches = (len(texts) + batch_size - 1) // batch_size
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        print(f"  [{batch_num}/{total_batches}] {len(batch)}개 임베딩 생성...", end=" ", flush=True)
        
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
            print("✅")
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ {e}")
            all_embeddings.extend([[0.0] * 1536] * len(batch))
    
    return np.array(all_embeddings)


def cluster_articles(articles):
    """기사들을 토픽별로 클러스터링"""
    print(f"\n📝 임베딩 생성 ({len(articles)}개 기사)\n")
    
    texts = []
    for art in articles:
        text = art["title"]
        if art.get("summary"):
            text += " " + art["summary"][:300]
        texts.append(text)
    
    embeddings = get_embeddings_batch(texts)
    
    print(f"\n🔍 유사도 계산 중...")
    similarity_matrix = cosine_similarity(embeddings)
    
    n = len(articles)
    parent = list(range(n))
    
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # 같은 카테고리 안에서만 클러스터링
    for i in range(n):
        for j in range(i+1, n):
            if (articles[i].get("category") == articles[j].get("category") 
                and similarity_matrix[i][j] >= SIMILARITY_THRESHOLD):
                union(i, j)
    
    clusters = {}
    for i in range(n):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(i)
    
    cluster_list = []
    for cluster_idx, (root, indices) in enumerate(clusters.items()):
        cluster_articles_data = [articles[i] for i in indices]
        
        priority_sources = ["한겨레", "경향신문", "동아일보", "오마이뉴스", 
                           "매일경제", "한국경제", "BBC 코리아",
                           "KTN 코리아타운뉴스", "주간포커스 텍사스"]
        
        representative = cluster_articles_data[0]
        for art in cluster_articles_data:
            if art["source"] in priority_sources:
                representative = art
                break
        
        unique_sources = list(set(a["source"] for a in cluster_articles_data))
        
        cluster_info = {
            "cluster_id": f"c_{cluster_idx:04d}",
            "article_count": len(cluster_articles_data),
            "source_count": len(unique_sources),
            "size": len(unique_sources),
            "category": cluster_articles_data[0].get("category", "기타"),
            "representative_title": representative["title"],
            "representative_link": representative["link"],
            "sources": unique_sources,
            "article_indices": indices,
            "all_titles": [a["title"] for a in cluster_articles_data],
            "all_articles": [{"title": a["title"], "source": a["source"], "link": a["link"]} 
                            for a in cluster_articles_data],
        }
        
        cluster_list.append(cluster_info)
        
        for art in cluster_articles_data:
            art["cluster_id"] = cluster_info["cluster_id"]
            art["cluster_size"] = len(unique_sources)
            art["cluster_article_count"] = len(cluster_articles_data)
    
    cluster_list.sort(key=lambda c: (-c["source_count"], -c["article_count"]))
    
    return articles, cluster_list


def save_results(articles, clusters, output_dir="output"):
    """결과 저장 - 카테고리별 다른 처리"""
    Path(output_dir).mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # JSON 저장
    json_path = f"{output_dir}/{today}_clustered.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": today,
            "total_articles": len(articles),
            "total_clusters": len(clusters),
            "articles": articles,
            "clusters": clusters,
        }, f, ensure_ascii=False, indent=2)
    
    # Markdown 저장
    md_path = f"{output_dir}/{today}_top_news.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🔥 오늘의 Top 뉴스 - {today}\n\n")
        f.write(f"전체 기사: {len(articles)}개 | 토픽: {len(clusters)}개\n\n")
        f.write("---\n\n")
        
        # 카테고리별 그룹화
        by_category = {}
        for c in clusters:
            cat = c["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(c)
        
        # 출력 순서: 핵심 → 로컬 → 기타
        category_order = CORE_CATEGORIES + LOCAL_CATEGORIES + ["한국일반", "국제", "기타"]
        
        for cat in category_order:
            if cat not in by_category:
                continue
            
            cat_clusters = by_category[cat]
            multi = [c for c in cat_clusters if c["source_count"] >= 2]
            single = [c for c in cat_clusters if c["source_count"] == 1]
            
            f.write(f"## {cat}\n\n")
            
            if cat in CORE_CATEGORIES:
                # 핵심 카테고리: 중복 보도 강조
                f.write(f"**중복 보도 토픽**: {len(multi)}개 | **단독 보도**: {len(single)}개\n\n")
                
                if multi:
                    f.write(f"### 🔥 Top 기사 (여러 매체가 같이 다룬 기사)\n\n")
                    for i, c in enumerate(multi[:15], 1):
                        f.write(f"#### {i}. [{c['source_count']}개 매체, {c['article_count']}개 기사] {c['representative_title']}\n")
                        f.write(f"- **출처**: {', '.join(c['sources'])}\n")
                        f.write(f"- **대표 링크**: {c['representative_link']}\n")
                        if len(c['all_titles']) > 1:
                            f.write(f"- **관련 기사**:\n")
                            for art in c['all_articles'][1:6]:
                                f.write(f"  - {art['title']} ({art['source']})\n")
                        f.write("\n")
                
                # 단독 보도는 간단히만
                if single:
                    f.write(f"### 📰 단독 보도 (참고용)\n\n")
                    for c in single[:10]:
                        f.write(f"- {c['representative_title']} ({c['sources'][0]})\n")
                    if len(single) > 10:
                        f.write(f"- _...외 {len(single) - 10}건_\n")
                    f.write("\n")
            
            elif cat in LOCAL_CATEGORIES:
                # 로컬/스포츠/흥미: 모든 기사 보여줌
                f.write(f"**전체 토픽**: {len(cat_clusters)}개\n\n")
                
                if multi:
                    f.write(f"### 🔥 중복 보도\n\n")
                    for i, c in enumerate(multi[:10], 1):
                        f.write(f"#### {i}. [{c['source_count']}개 매체] {c['representative_title']}\n")
                        f.write(f"- **출처**: {', '.join(c['sources'])}\n")
                        f.write(f"- **링크**: {c['representative_link']}\n\n")
                
                # 단독 보도도 다 보여줌 (로컬 뉴스는 단독이 대부분)
                if single:
                    f.write(f"### 📰 모든 기사\n\n")
                    for c in single:
                        f.write(f"- **{c['representative_title']}** ({c['sources'][0]})\n")
                        f.write(f"  - {c['representative_link']}\n")
                    f.write("\n")
            
            else:
                # 기타 카테고리: 간단히
                f.write(f"**전체 토픽**: {len(cat_clusters)}개 (참고용)\n\n")
                for c in cat_clusters[:5]:
                    f.write(f"- {c['representative_title']} ({c['sources'][0]})\n")
                if len(cat_clusters) > 5:
                    f.write(f"- _...외 {len(cat_clusters) - 5}건_\n")
                f.write("\n")
            
            f.write("---\n\n")
    
    return json_path, md_path


def main():
    print(f"\n{'='*70}")
    print(f"  🔍 토픽 클러스터링  ({datetime.now().strftime('%H:%M:%S')})")
    print(f"{'='*70}\n")
    
    today = datetime.now().strftime("%Y-%m-%d")
    input_path = f"output/{today}_categorized.json"
    
    if not os.path.exists(input_path):
        print(f"❌ {input_path} 없음. categorizer.py 먼저 실행.")
        return
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    articles = data["articles"]
    print(f"📂 로드: {len(articles)}개 기사")
    print(f"⚙️ 임계값: {SIMILARITY_THRESHOLD} (0.65 → 0.55, 더 적극적 묶기)\n")
    
    articles, clusters = cluster_articles(articles)
    
    multi_count = len([c for c in clusters if c["source_count"] >= 2])
    max_sources = clusters[0]["source_count"] if clusters else 0
    
    print(f"\n📊 클러스터링 결과")
    print(f"  - 전체 기사: {len(articles)}")
    print(f"  - 전체 토픽: {len(clusters)}")
    print(f"  - 중복 보도 토픽: {multi_count}")
    print(f"  - 최대 매체 수: {max_sources}")
    
    # 카테고리별 중복 보도 통계
    print(f"\n📂 카테고리별 중복 보도")
    cat_multi = {}
    for c in clusters:
        if c["source_count"] >= 2:
            cat = c["category"]
            cat_multi[cat] = cat_multi.get(cat, 0) + 1
    
    for cat in CORE_CATEGORIES:
        count = cat_multi.get(cat, 0)
        marker = "⭐" if count > 0 else "  "
        print(f"  {marker} {cat}: {count}개")
    
    for cat in LOCAL_CATEGORIES:
        count = cat_multi.get(cat, 0)
        print(f"     {cat}: {count}개")
    
    # Top 5 클러스터
    print(f"\n🔥 Top 5 토픽 (전체)")
    shown = 0
    for c in clusters:
        if c["source_count"] >= 2:
            shown += 1
            print(f"  {shown}. [{c['source_count']}개 매체, {c['article_count']}개 기사] [{c['category']}]")
            print(f"     {c['representative_title'][:60]}")
            print(f"     출처: {', '.join(c['sources'])}")
            if shown >= 5:
                break
    
    # 핵심 카테고리 Top 토픽
    print(f"\n⭐ 핵심 카테고리 Top 토픽")
    for cat in CORE_CATEGORIES:
        cat_clusters = [c for c in clusters if c["category"] == cat and c["source_count"] >= 2]
        if cat_clusters:
            top = cat_clusters[0]
            print(f"  [{cat}] [{top['source_count']}개 매체] {top['representative_title'][:55]}")
        else:
            print(f"  [{cat}] (중복 보도 없음)")
    
    json_path, md_path = save_results(articles, clusters)
    print(f"\n💾 저장 완료")
    print(f"  - JSON: {json_path}")
    print(f"  - Markdown: {md_path}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()