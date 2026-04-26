"""달사람닷컴 스크래핑 테스트"""
import requests
from bs4 import BeautifulSoup

URL = "https://www.dalsaram.com/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def test():
    print(f"📥 가져오는 중: {URL}\n")
    response = requests.get(URL, headers=HEADERS, timeout=15)
    print(f"상태 코드: {response.status_code}")
    print(f"HTML 크기: {len(response.text):,} bytes\n")
    
    if response.status_code != 200:
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    all_links = soup.find_all('a', href=True)
    print(f"전체 링크: {len(all_links)}")
    
    # 달사람은 게시판 형식: /m5/news.php?wr_id=XXX 같은 패턴
    article_links = []
    seen = set()
    for link in all_links:
        href = link.get('href', '').strip()
        text = link.get_text(strip=True)
        
        if len(text) < 10:
            continue
        if not any('\uac00' <= c <= '\ud7af' for c in text):
            continue
        
        # 게시판 패턴
        if 'wr_id=' not in href and 'bo_table' not in href:
            continue
        
        if href.startswith('/'):
            href = "https://www.dalsaram.com" + href
        elif not href.startswith('http'):
            href = "https://www.dalsaram.com/" + href
        
        if href in seen:
            continue
        seen.add(href)
        
        article_links.append((text, href))
    
    print(f"기사 추정: {len(article_links)}개\n")
    for i, (t, h) in enumerate(article_links[:10], 1):
        print(f"{i}. {t[:60]}")
        print(f"   {h[:80]}")
        print()

if __name__ == "__main__":
    test()