"""
달코라 스크래퍼
- https://www.dalkora.com
- 기사: dalkora.com/%xxx (한글 인코딩 URL)
- 제외: /shows, /podcast, youtu.be
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://www.dalkora.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_article_link(text, href):
    """기사 링크인지 판별"""
    if not text or not href or len(text) < 10:
        return False
    
    # 한글 포함 확인
    if not any('\uac00' <= c <= '\ud7af' for c in text):
        return False
    
    # 외부 사이트 제외
    if 'youtu.be' in href or 'youtube.com' in href:
        return False
    
    # 라디오 쇼/팟캐스트 제외
    if any(p in href for p in ['/shows/', '/podcast/', '/category/', '/tag/']):
        return False
    
    # 외부 도메인 제외 (dalkora.com 아닌 것)
    if href.startswith('http') and 'dalkora.com' not in href:
        return False
    
    # 인코딩된 한글 URL 패턴 (% 5개 이상)
    if href.count('%') >= 5:
        return True
    
    return False


def collect_dalkora():
    """달코라 메인 페이지에서 기사 수집"""
    print(f"  달코라 수집 중...", end=" ", flush=True)
    
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        seen = set()
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            text = link.get_text(strip=True)
            
            if not is_article_link(text, href):
                continue
            
            # 절대 URL로
            if href.startswith('/'):
                href = BASE_URL + href
            
            if href in seen:
                continue
            seen.add(href)
            
            articles.append({
                "source": "달코라",
                "category_hint": "달라스텍사스한인",
                "lang": "ko",
                "title": text,
                "link": href,
                "summary": "",
                "published": "",
                "collected_at": datetime.now().isoformat(),
            })
        
        print(f"✅ {len(articles)}개")
        return articles
    
    except Exception as e:
        print(f"❌ {e}")
        return []


if __name__ == "__main__":
    articles = collect_dalkora()
    print(f"\n총 {len(articles)}개\n")
    for i, a in enumerate(articles[:10], 1):
        print(f"{i}. {a['title']}")