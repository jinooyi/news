# 📰 News Collector & WebApp

미주 한인을 위한 뉴스 수집 및 시청 시스템

## 🎯 프로젝트 목적

- 한국/한인/미국 뉴스 자동 수집
- 카테고리별 정리 + 중복 제거
- WebApp에서 본인과 가족이 함께 시청
- SBS/JTBC 영상 자막 분석 (참고용)

## 📋 Phase 1 스코프 (현재)

- ✅ 뉴스 수집 시스템
- ✅ 카테고리 자동 분류 (Claude)
- ✅ 중복 감지
- ✅ 사진 출처 표기
- ✅ WebApp UI (기사 리스트)
- ✅ SBS 영상 자막 분석

## 🚫 Phase 2 (나중)

- 영상 자동 생성
- 본인 음성 (ElevenLabs)
- 자동 업로드
- 광고 삽입

## 📰 수집 소스

### 한국 메이저
- 한겨레 (hani.co.kr) ✅ RSS 작동
- Google News 한국어 RSS
- 조선/중앙/연합 (RSS 재확인 필요)

### 한인 로컬 (달라스/텍사스)
- KTN 코리아타운뉴스 (koreatownnews.com)
- 주간포커스 텍사스 (weeklyfocustx.com)
- 달사람닷컴 (dalsaram.com)
- 달코라 (dalkora.com)

### 미주 전체 한인
- 미주중앙일보 (Koreadaily)
- 미주한국일보 (Koreatimes)
- Radio Korea

### 미국 영문 (번역 후 사용)
- CNN, NYT, AP, Reuters
- Dallas Morning News (로컬)

## 🛠 기술 스택

### Backend
- Python 3.14
- FastAPI
- SQLAlchemy + SQLite
- feedparser, trafilatura, BeautifulSoup
- Anthropic Claude API

### Frontend
- Next.js 14
- TypeScript
- Tailwind CSS

## 📂 프로젝트 구조