"""달코라 모든 한글 링크 보기"""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

response = requests.get("https://www.dalkora.com/", headers=HEADERS, timeout=15)
soup = BeautifulSoup(response.text, 'html.parser')

print(f"전체 링크: {len(soup.find_all('a', href=True))}\n")

# 한글 텍스트 있는 모든 링크 출력 (URL 패턴 무관)
print("=" * 60)
print("한글 텍스트 가진 모든 링크 (Top 30)")
print("=" * 60)

korean_links = []
seen = set()
for link in soup.find_all('a', href=True):
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