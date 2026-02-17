# KTI Portfolio News Bot

## 프로젝트 개요

74개 포트폴리오 회사의 뉴스를 자동으로 수집·필터링하여 담당자별로 이메일 발송하는 자동화 봇입니다.

- **자동 실행**: GitHub Actions (월-금 오전 8시 KST)
- **핵심 기능**: 키워드 검색 → 임베딩 중복 제거 → AI 관련성 필터 → 이메일 발송
- **처리량**: 74개 회사, 9명 담당자

---

## 핵심 아키텍처

### 3단계 처리 파이프라인

```
Step 1: 뉴스 수집 & 임베딩 기반 중복 제거
  ├─ portfolio_news_data.csv에서 회사 정보 로드
  ├─ 키워드로 Naver 뉴스 검색 (Playwright)
  ├─ Gemini Embedding으로 유사도 계산 (코사인 유사도)
  ├─ 임계값 0.60 초과 시 클러스터링으로 중복 제거
  └─ 클러스터 크기 추적 (이메일 제목 생성용)

Step 2: AI 관련성 필터링 (선택)
  ├─ filter_config.json의 enable_relevance_filter 확인
  ├─ Gemini 3-Flash로 0-10점 관련성 평가
  ├─ 임계값(기본 6점) 미만 필터링
  └─ Beta 모드: 낮은 점수도 [관련도 낮음] 태그와 함께 포함

Step 3: 담당자별 이메일 발송
  ├─ user_info.json에서 이메일 조회
  ├─ 담당 회사 뉴스를 상단 배치
  └─ HTML 이메일 생성 & SMTP 발송
```

### 핵심 모듈

| 파일 | 역할 |
|------|------|
| `main.py` | 메인 실행 (전체 74개 회사) |
| `test.py` | 테스트 실행 (6개 회사, AI 필터 비활성화) |
| `utils/fetch_news.py` | Playwright 기반 Naver 뉴스 스크래핑 |
| `utils/filter_similar_news.py` | Gemini Embedding & AI 필터링 |
| `utils/email_sender.py` | HTML 이메일 생성 & SMTP 발송 |
| `utils/data_loader.py` | CSV/JSON 로더 (경로 자동 처리) |

---

## 주요 설정 파일

### portfolio_news_data.csv (74개 회사)

```csv
기업명,회사소개,담당자,키워드
힐링페이퍼,반려동물 헬스케어,김진수/최우석,힐링페이퍼 / 펫케어 / 반려동물
```

- **담당자 복수**: `/` 구분 (예: `김진수/최우석`)
- **키워드 복수**: ` / ` 구분 (공백 포함 주의!)
- **단일 소스**: 모든 회사 정보를 이 파일에서만 로드

### filter_config.json

```json
{
  "enable_relevance_filter": true,
  "relevance_threshold": 6,
  "beta_test_mode": false
}
```

- 환경변수로 덮어쓰기 가능: `ENABLE_RELEVANCE_FILTER`, `RELEVANCE_THRESHOLD`, `BETA_TEST_MODE`

### user_info.json (9명 담당자)

```json
{
  "김진수": {"email": "jinsoo@example.com"},
  "최우석": {"email": "wooseok@example.com"}
}
```

- **중요**: CSV의 담당자명과 정확히 일치해야 함

---

## 개발 및 테스트

### 환경 설정

```bash
# 1. 의존성 설치
pip install -r requirements.txt
playwright install chromium

# 2. 환경변수 설정
cp .env.example .env
# GEMINI_API_KEY, SMTP_SERVER, EMAIL_LOGIN, EMAIL_PASSWORD 설정

# 3. 메인 실행 (전체 회사)
python3 main.py

# 4. 테스트 실행 (6개 회사, AI 필터 비활성화)
export TEST_EMAIL="your-email@example.com"
python3 test.py
```

### 테스트 모드

- `TEST_EMAIL` 설정 시 **모든 이메일을 해당 주소로만 발송** (주의!)
- `test.py`는 6개 회사만 대상:
  - 힐링페이퍼, 클래스101, 뉴로메카, 리벨리온, Bear Robotics, 한국신용데이터
- AI 관련성 필터 비활성화 (임베딩 중복 제거만 실행)

### GitHub Actions

- `.github/workflows/daily-news.yml` - 정식 자동 실행 (월-금 오전 8시 KST)
- `.github/workflows/test-news.yml` - 테스트 워크플로우
- **필수 Secrets**: `GEMINI_API_KEY`, `SMTP_SERVER`, `SMTP_PORT`, `EMAIL_LOGIN`, `EMAIL_PASSWORD`

---

## 중요한 제약사항

### Gemini API Rate Limiting

```python
# 429 에러 방지를 위한 대기 시간
time.sleep(1)  # Embedding 호출 후
time.sleep(1)  # AI 필터링 호출 후
```

- **자동 재시도**: 2s → 5s → 15s → 30s 백오프
- **임베딩 모델**: `gemini-embedding-001`
- **생성 모델**: `gemini-3-flash-preview`

### 경로 처리

- `utils/data_loader.py`가 프로젝트 루트 기준 상대경로 자동 처리
- CSV/JSON 파일은 항상 프로젝트 루트에 위치
- **수동 경로 조작 불필요**

### 데이터 일관성

- CSV의 담당자명 ↔ user_info.json의 키 **정확히 일치** 필수
- 키워드 구분자 주의: ` / ` (공백 포함)
- `TEST_EMAIL` 설정 시 모든 이메일이 해당 주소로만 발송됨 (주의!)

### 보안

- `.env` 파일 절대 커밋 금지 (`.gitignore`에 명시)
- API 키는 GitHub Secrets로만 관리
- `.env.example`을 템플릿으로 사용

---

## 이메일 제목 생성 로직

**클러스터 기반 대표 뉴스 선택:**

1. 필터링 전 기사 개수가 가장 많은 회사 찾기 (핫토픽)
2. 해당 회사의 뉴스 중 가장 큰 클러스터 선택
3. 제목 형식: `Portfolio Daily News(MM/DD: {대표 뉴스 20자})`

**예시:**
```
Portfolio Daily News(02/18: AI 스타트업 투자 급증...)
```

---

## 프로젝트 파일 구조

```
kti-newsletter/
├── main.py                      # 메인 실행 (74개 회사)
├── test.py                      # 테스트 실행 (6개 회사)
├── portfolio_news_data.csv      # 회사 정보 단일 소스
├── user_info.json               # 담당자 이메일
├── filter_config.json           # AI 필터 설정
├── requirements.txt             # Python 의존성
├── .env.example                 # 환경변수 템플릿
├── README.md                    # 상세 문서
├── .github/workflows/           # GitHub Actions
│   ├── daily-news.yml           # 정식 자동 실행
│   └── test-news.yml            # 테스트
└── utils/                       # 핵심 모듈
    ├── data_loader.py           # CSV/JSON 로더
    ├── fetch_news.py            # 뉴스 스크래핑
    ├── filter_similar_news.py   # 임베딩 & AI 필터
    └── email_sender.py          # 이메일 발송
```

---

## 일반적인 작업 흐름

### 새로운 회사 추가

1. `portfolio_news_data.csv`에 행 추가
2. 기업명, 회사소개, 담당자, 키워드 입력
3. 담당자가 신규라면 `user_info.json`에 이메일 추가
4. `python3 test.py`로 테스트 (TEST_EMAIL 설정)

### 필터링 파라미터 조정

1. `filter_config.json` 수정
   - `relevance_threshold`: 점수 조정 (0-10)
   - `beta_test_mode`: 낮은 점수 기사 포함 여부
2. 로컬에서 `python3 main.py` 테스트
3. GitHub Secrets의 환경변수로도 덮어쓰기 가능

### 디버깅

```bash
# 특정 회사만 테스트 (test.py의 TEST_COMPANIES 수정)
python3 test.py

# 이메일 미리보기 생성 (발송 없이)
python3 test_email_preview.py

# 로그 확인
# main.py와 test.py는 콘솔에 진행상황 출력
```

---

## 문제 해결

### 429 Too Many Requests

- Gemini API rate limit 초과
- **해결**: 코드에 이미 자동 재시도 로직 포함 (최대 4회)
- 필요시 `time.sleep()` 시간 증가

### 이메일이 발송되지 않음

1. `.env` 파일의 SMTP 설정 확인
2. `user_info.json`에 담당자 이메일 존재 확인
3. `TEST_EMAIL` 환경변수 설정 여부 확인

### 중복 제거가 너무 많음/적음

- `utils/filter_similar_news.py`의 임계값 조정
- 현재: `0.60` (코사인 유사도)
- 높일수록: 더 유사한 기사만 제거
- 낮출수록: 더 많은 기사 제거

### 관련성 필터가 너무 엄격함

1. `filter_config.json`의 `relevance_threshold` 낮추기
2. 또는 `beta_test_mode: true`로 설정하여 낮은 점수 기사도 포함

---

## 추가 참고사항

- **상세 문서**: `README.md` 참고
- **이메일 디자인 수정**: `utils/email_sender.py`의 HTML 템플릿 수정
- **스크래핑 로직 수정**: `utils/fetch_news.py` (Playwright 셀렉터 주의)
- **GitHub Actions 로그**: Actions 탭에서 실행 기록 확인
