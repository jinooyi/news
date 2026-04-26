"""
주간 포커스 텍사스 스크래퍼
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://www.weeklyfocustx.com"
LIST_URL = f"{BASE_URL}/news/articleList.html?view_type=sm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def collect_focus():
    """주간포커스 메인 페이지에서 기사 수집"""
    print(f"  주간포커스 텍사스 수집 중...", end=" ", flush=True)
    
    try:
        response = requests.get(LIST_URL, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        seen = set()
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            text = link.get_text(strip=True)
            
            if len(text) < 10:
                continue
            if not any('\uac00' <= c <= '\ud7af' for c in text):
                continue
            if 'articleView' not in href:
                continue
            
            if href.startswith('/'):
                href = BASE_URL + href
            
            if href in seen:
                continue
            seen.add(href)
            
            articles.append({
                "source": "주간포커스 텍사스",
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
    articles = collect_focus()
    print(f"\n총 {len(articles)}개\n")
    for i, a in enumerate(articles[:5], 1):
        print(f"{i}. {a['title']}")