# 📅 개발 진행 로그

## Phase 1: 수집 시스템

### 2026-04-24 (목) - Day 1

#### ✅ 완료
- [x] 프로젝트 구조 셋업 (backend, frontend, docs)
- [x] Python 가상환경 생성
- [x] 패키지 설치 (FastAPI, feedparser, trafilatura, anthropic 등)
- [x] Anthropic API 키 발급
- [x] 한겨레 RSS 수집 테스트
- [x] README + PROGRESS 문서 작성
#### ✅ 완료
- [x] 한겨레 RSS 수집 성공 (30개 기사 정상 추출)
#### ✅ 완료 (Day 1)
- [x] 한겨레 RSS 수집 (30개)
- [x] 12개 RSS 소스 검증 완료
- [x] 706개 기사 일괄 수집
- [x] Claude로 카테고리 자동 분류 성공
- [x] JSON + Markdown 출력 시스템
[Day 1 결과물]

수집:
- RSS 12개 소스 ✅
- 706개 기사

처리:
- Claude 카테고리 분류 ✅
- OpenAI 임베딩 클러스터링 ✅
- Top 기사 자동 선정 ✅

출력:
- backend/output/
  ├── 2026-04-24.json (원본)
  ├── 2026-04-24.md
  ├── 2026-04-24_categorized.json
  ├── 2026-04-24_categorized.md
  ├── 2026-04-24_clustered.json
  └── 2026-04-24_top_news.md ⭐ 메인

비용:
- Claude: $0.30
- OpenAI: $0.05
- 총: ~$0.35

비용: ~$0.30 (Claude Haiku)

#### 🔄 진행 중
- [ ] KTN 스크래핑
- [ ] 주간포커스 스크래핑
### Day 1 최종 결과 (2026-04-24)

#### 작동 확인된 시스템
1. `collector.py` - RSS 12개 소스 → 706개 기사
2. `categorizer.py` - Claude 분류 (8개 카테고리)
3. `clusterer.py` - OpenAI 임베딩 클러스터링

#### Top 5 토픽 (오늘)
1. 말레이시아 납치 사건 (3개 매체)
2. G20 러시아 대표단 (3개 매체)
3. 김창민 감독 사건 (3개 매체)
4. 장동혁 거짓말 논란 (2개 매체)
5. 방시혁 구속영장 (2개 매체)

#### 비용
- Claude Haiku: $0.30
- OpenAI Embedding: $0.05
- 총: $0.35

#### 개선 필요
- 미국이민 카테고리: 한국 매체 보도 적음
  → 미주 한인 매체 (KTN, Koreadaily) 추가 필요
- 기타 카테고리 141개 → 분류 정밀화 필요

### Day 2 계획 (내일)
- [ ] 미주 한인 매체 스크래핑
  - KTN 코리아타운뉴스
  - 주간포커스 텍사스
  - Koreadaily, Koreatimes
- [ ] 본문/사진 추출
- [ ] WebApp UI 시작


#### 📝 메모
- Python 3.14, Node 24 환경
- 한겨레 RSS 정상 작동 확인
- 조선일보/중앙일보 RSS 종료/변경됨 → 재확인 필요
- 연합뉴스 RSS 차단됨 → 다른 방법 모색

#### 🐛 이슈
- (작업하면서 추가)

---

### 2026-04-25 (금) - Day 2 (예정)

#### 🎯 목표
- [ ] KTN 스크래퍼 작성
- [ ] 주간포커스 스크래퍼 작성
- [ ] 수집 데이터 SQLite 저장
- [ ] 카테고리 자동 분류 (Claude)

---

## 결정 사항

### 비주얼 정책
- ✅ Pexels/Pixabay 무료 영상/사진
- ✅ 한국 매체 사진 + 출처 표기 (회색지대 OK)
- ✅ 본인 그래픽
- ❌ AI 이미지 (가짜 느낌)
- ❌ SBS/JTBC 영상 클립

### 음성
- 본인 목소리 (Phase 2에서 ElevenLabs)

### 채널
- 비공개 또는 unlisted
- 엄마 + 가족 + 친한 사람들

### 광고
- 본인 제작 광고 영상 중간 삽입 (Phase 2)
- YouTube 광고 수익 X