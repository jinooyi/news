"""달사람 media 페이지 테스트"""
import requests
from bs4 import BeautifulSoup

URL = "https://dalsaram.com/media/index.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"📥 가져오는 중: {URL}\n")
response = requests.get(URL, headers=HEADERS, timeout=15, allow_redirects=True)
print(f"최종 URL: {response.url}")
print(f"상태 코드: {response.status_code}")
print(f"HTML 크기: {len(response.text):,} bytes\n")

if response.status_code != 200:
    print("❌ 페이지 못 가져옴")
    exit()

soup = BeautifulSoup(response.text, 'html.parser')

# 페이지 제목
title = soup.find('title')
print(f"페이지 제목: {title.text if title else 'N/A'}\n")

# 모든 한글 링크
all_links = soup.find_all('a', href=True)
print(f"전체 링크: {len(all_links)}\n")

print("=" * 60)
print("한글 텍스트 가진 모든 링크 (Top 30)")
print("=" * 60)

korean_links = []
seen = set()
for link in all_links:
    href = link.get('href', '').strip()
    text = link.get_text(strip=True)
    
    if len(text) < 10:
        continue
    if not any('\uac00' <= c <= '\ud7af' for c in text):
        continue
    
    if (text, href) in seen:
        continue
    seen.add((text, href))
    korean_links.append((text, href))

print(f"한글 링크: {len(korean_links)}개\n")
for i, (t, h) in enumerate(korean_links[:30], 1):
    print(f"{i}. {t[:60]}")
    print(f"   {h[:90]}")
    print()