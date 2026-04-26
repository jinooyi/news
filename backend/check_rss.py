"""
여러 RSS 소스가 작동하는지 확인
"""
import feedparser
import requests
from datetime import datetime

# 테스트할 RSS 소스들
RSS_SOURCES = {
    # 한국 메이저 (진보)
    "한겨레": "https://www.hani.co.kr/rss/",
    "경향신문": "https://www.khan.co.kr/rss/rssdata/total_news.xml",
    "오마이뉴스": "https://rss.ohmynews.com/rss/ohmynews.xml",
    
    # 한국 메이저 (보수)
    "동아일보": "https://rss.donga.com/total.xml",
    
    # 한국 경제지
    "매일경제": "https://www.mk.co.kr/rss/30000001/",
    "한국경제": "https://www.hankyung.com/feed/all-news",

    
    # Google News (가장 강력)
    "Google News 한국": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "Google News 미국이민": "https://news.google.com/rss/search?q=미국+이민+한인&hl=ko&gl=KR&ceid=KR:ko",
    "Google News 한미외교": "https://news.google.com/rss/search?q=한미+외교&hl=ko&gl=KR&ceid=KR:ko",
    "Google News 달라스한인": "https://news.google.com/rss/search?q=달라스+한인&hl=ko&gl=KR&ceid=KR:ko",
    "Google News H1B": "https://news.google.com/rss/search?q=H1B+비자+이민&hl=ko&gl=KR&ceid=KR:ko",
    
    # 영문 한국어판 (번역 불필요!)
    "VOA 한국어": "https://www.voakorea.com/api/zovieqyiyq",
    "BBC 코리아": "https://feeds.bbci.co.uk/korean/rss.xml",
    
    # 영문 메이저 (필요시 번역)
    "CNN Top": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    
    # 미국 정부
    "USCIS 뉴스룸": "https://www.uscis.gov/news/rss-feed/13947",
}


def check_rss(name: str, url: str) -> dict:
    """RSS 작동 여부 확인"""
    result = {
        "name": name,
        "url": url,
        "status": "❌ 실패",
        "count": 0,
        "first_title": "",
        "error": None
    }
    
    try:
        # User-Agent 헤더 (일부 사이트 차단 회피)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # requests로 먼저 가져와서 feedparser에 전달 (더 안정적)
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}"
            return result
        
        feed = feedparser.parse(response.content)
        
        if feed.bozo and not feed.entries:
            result["error"] = "RSS 파싱 실패"
            return result
        
        if len(feed.entries) == 0:
            result["error"] = "기사 없음"
            return result
        
        result["status"] = "✅ 성공"
        result["count"] = len(feed.entries)
        result["first_title"] = feed.entries[0].title[:50] + "..."
        
    except requests.Timeout:
        result["error"] = "타임아웃"
    except Exception as e:
        result["error"] = str(e)[:100]
    
    return result


def main():
    print(f"\n{'='*70}")
    print(f"  RSS 소스 작동 확인  ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"{'='*70}\n")
    
    working = []
    failing = []
    
    for name, url in RSS_SOURCES.items():
        print(f"확인 중: {name}...", end=" ", flush=True)
        result = check_rss(name, url)
        
        if result["status"] == "✅ 성공":
            print(f"✅ ({result['count']}개)")
            working.append(result)
        else:
            print(f"❌ {result['error']}")
            failing.append(result)
    
    # 결과 요약
    print(f"\n{'='*70}")
    print(f"  결과 요약")
    print(f"{'='*70}")
    print(f"\n✅ 작동 ({len(working)}개):")
    for r in working:
        print(f"   • {r['name']}: {r['count']}개 기사")
        print(f"     첫 기사: {r['first_title']}")
    
    print(f"\n❌ 실패 ({len(failing)}개):")
    for r in failing:
        print(f"   • {r['name']}: {r['error']}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()