"""
KTN 코리아타운뉴스 스크래퍼
- https://koreatownnews.com
- 메인 페이지에서 기사 리스트 추출
- collector.py와 같은 형식으로 데이터 반환
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

BASE_URL = "https://koreatownnews.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_article_link(text: str, href: str) -> bool:
    """기사 링크인지 판별"""
    if not text or not href:
        return False
    
    # 너무 짧은 텍스트 제외
    if len(text) < 10:
        return False
    
    # 한글 포함 확인
    has_korean = any('\uac00' <= c <= '\ud7af' for c in text)
    if not has_korean:
        return False
    
    # 외부 사이트 제외
    if 'koreatownnews.com' not in href and href.startswith('http'):
        return False
    
    # KTN 기사 URL 패턴: 한글이 인코딩된 긴 슬러그
    # 예: koreatownnews.com/e자형-경제-돌입-...
    if 'koreatownnews.com' in href or href.startswith('/'):
        # URL에 % 인코딩 많이 있으면 한글 슬러그
        if '%' in href and href.count('%') >= 5:
            return True
        # 또는 명확한 패턴
        if any(p in href.lower() for p in ['/article', '/news', '/post', '?bo_table']):
            return True
    
    return False


def normalize_url(href: str) -> str:
    """상대 URL을 절대 URL로"""
    if href.startswith('http'):
        return href
    if href.startswith('/'):
        return BASE_URL + href
    return BASE_URL + '/' + href


def collect_ktn() -> list:
    """KTN 메인 페이지에서 기사 수집"""
    print(f"  KTN 코리아타운뉴스 수집 중...", end=" ", flush=True)
    
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 모든 링크 검사
        articles = []
        seen_urls = set()
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            text = link.get_text(strip=True)
            
            if not is_article_link(text, href):
                continue
            
            url = normalize_url(href)
            
            # 중복 제거
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            articles.append({
                "source": "KTN 코리아타운뉴스",
                "category_hint": "달라스텍사스한인",
                "lang": "ko",
                "title": text,
                "link": url,
                "summary": "",  # 본문은 나중에 추출
                "published": "",
                "collected_at": datetime.now().isoformat(),
            })
        
        print(f"✅ {len(articles)}개")
        return articles
    
    except Exception as e:
        print(f"❌ {e}")
        return []


if __name__ == "__main__":
    # 직접 실행 시 테스트
    print("=" * 60)
    print("KTN 스크래퍼 테스트")
    print("=" * 60)
    
    articles = collect_ktn()
    
    print(f"\n총 {len(articles)}개 수집\n")
    for i, art in enumerate(articles[:10], 1):
        print(f"{i}. {art['title'][:60]}")
        print(f"   {art['link'][:80]}")
        print()