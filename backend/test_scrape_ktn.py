"""
KTN 코리아타운뉴스 스크래핑 테스트
- HTML 구조 분석
- 기사 리스트 추출
"""
import requests
from bs4 import BeautifulSoup

URL = "https://koreatownnews.com/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_scrape():
    print(f"📥 가져오는 중: {URL}\n")
    
    response = requests.get(URL, headers=HEADERS, timeout=15)
    
    print(f"상태 코드: {response.status_code}")
    print(f"인코딩: {response.encoding}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"HTML 크기: {len(response.text):,} bytes\n")
    
    if response.status_code != 200:
        print("❌ 페이지 못 가져옴")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 페이지 제목
    title = soup.find('title')
    print(f"페이지 제목: {title.text if title else 'N/A'}\n")
    
    # 기사 링크 후보 찾기 - 흔한 패턴 시도
    print("=" * 60)
    print("🔍 기사 링크 패턴 탐색")
    print("=" * 60)
    
    # 패턴 1: <article> 태그
    articles = soup.find_all('article')
    print(f"\n[패턴 1] <article> 태그: {len(articles)}개")
    
    # 패턴 2: 클래스에 'post' 또는 'article' 포함
    posts = soup.find_all(class_=lambda x: x and ('post' in x.lower() or 'article' in x.lower()))
    print(f"[패턴 2] class에 'post'/'article': {len(posts)}개")
    
    # 패턴 3: 모든 링크
    all_links = soup.find_all('a', href=True)
    print(f"[패턴 3] 전체 <a> 링크: {len(all_links)}개")
    
    # 기사 같은 링크 (한글 제목 + URL에 숫자)
    article_links = []
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # 한글 제목 있고, URL에 article/news/post 같은 패턴
        if (len(text) > 10 
            and any('\uac00' <= c <= '\ud7af' for c in text)  # 한글 포함
            and any(p in href.lower() for p in ['article', 'news', 'post', 'view', 'bbs'])):
            article_links.append((text, href))
    
    print(f"\n📰 기사 추정 링크: {len(article_links)}개\n")
    
    # 처음 10개 출력
    for i, (text, href) in enumerate(article_links[:10], 1):
        # 상대 URL → 절대 URL
        if href.startswith('/'):
            href = "https://koreatownnews.com" + href
        elif not href.startswith('http'):
            href = "https://koreatownnews.com/" + href
        
        print(f"{i}. {text[:60]}")
        print(f"   {href}")
        print()
    
    # HTML 일부 저장 (구조 분석용)
    with open("ktn_sample.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify()[:50000])  # 처음 50KB만
    print(f"\n💾 HTML 샘플 저장: ktn_sample.html (구조 확인용)")


if __name__ == "__main__":
    test_scrape()