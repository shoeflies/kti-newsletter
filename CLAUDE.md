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
  ├─ Gemini Flash로 0-10점 관련성 배치 평가 (회사당 1회 API 호출)
  ├─ 평가 기준: "이 회사가 기사의 주인공인가?" (주인공 vs 단순 언급 구분)
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
| `utils/data_loader.py` | CSV/JSON 로더 (경로 자동 처리), 특별 회사 통합 관리 |

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
  "beta_test_mode": false,
  "enable_keyword_prefilter": true,
  "send_test_copy": false,
  "relevance_criteria": "- 10점: 이 회사가 기사의 핵심 주인공이고, 회사의 핵심 사업과 직접 관련된 뉴스\n    - 7-9점: ..."
}
```

- 환경변수로 덮어쓰기 가능: `ENABLE_RELEVANCE_FILTER`, `RELEVANCE_THRESHOLD`, `BETA_TEST_MODE`
- `relevance_criteria`: 관련성 평가 기준 커스터마이징 (없으면 코드 내 `DEFAULT_CRITERIA` 사용)
- `enable_keyword_prefilter`: 키워드 미포함 기사를 API 호출 없이 0점 처리 (기본 `true`)
- `send_test_copy`: `true`이면 정식 발송 외에 `TEST_EMAIL`로 복사본 추가 발송

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

### 빠른 이메일 테스트 (test_email_quick.py)

**API 호출 없이 HTML 디자인만 빠르게 테스트**하는 스크립트입니다.

```bash
# .env 파일에 설정이 있으면 바로 실행
python3 test_email_quick.py
```

**특징**:
- ⚡ API 호출 없음 (Gemini, Playwright 등)
- 🎯 더미 데이터로 HTML만 생성
- 📧 SMTP로 즉시 발송
- 🔄 수정 → 실행 → 확인 사이클이 빠름

**사용 시나리오**:
- 이메일 디자인(CSS, HTML) 수정 후 빠른 확인
- 다크모드 대응 테스트
- 레이아웃 변경 검증

**필수 환경변수** (.env):
- `TEST_EMAIL`: 수신 이메일 주소
- `SMTP_SERVER`, `SMTP_PORT`: SMTP 서버 정보
- `EMAIL_LOGIN`, `EMAIL_PASSWORD`: 인증 정보

### GitHub Actions

- `.github/workflows/daily-news.yml` - 정식 자동 실행 (월-금 오전 8시 KST)
- `.github/workflows/test-news.yml` - 테스트 워크플로우
- **필수 Secrets**: `GEMINI_API_KEY`, `SMTP_SERVER`, `SMTP_PORT`, `EMAIL_LOGIN`, `EMAIL_PASSWORD`

---

## 중요한 제약사항

### Gemini API Rate Limiting

```python
# 429 에러 방지를 위한 대기 시간 (배치 처리 후 1회만)
time.sleep(1.0)  # Embedding 배치 후
time.sleep(1.0)  # Flash 배치 후
```

- **자동 재시도**: 2s → 5s → 15s → 30s 백오프
- **임베딩 모델**: `gemini-embedding-001`
- **생성 모델**: `gemini-3-flash-preview`

### Gemini Flash 구조화 출력

`gemini-3-flash-preview`는 **프롬프트만으로 커스텀 텍스트 포맷을 지키지 않음** ("1:8 2:3", 쉼표 구분 등 모두 불안정).
배치 스코어링 시 JSON schema 강제 출력만 신뢰할 수 있음:

```python
response = client.models.generate_content(
    model=GENERATION_MODEL_NAME,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 10},
        },
        temperature=0.1,
    )
)
# 응답 예: "[8, 3, 0, 7]"
```

### AI 관련성 평가 기준 (주인공 vs 언급)

이전 기준("키워드 명시 여부")은 단순 언급 기사도 고점을 받는 문제가 있었음.
현재 기준은 "이 회사가 기사의 **주인공**인가?"로 변경:

- **10점**: 이 회사가 핵심 주인공 + 핵심 사업 직접 관련
- **7-9점**: 이 회사가 주인공이며 IPO/투자/M&A/임원/파트너십 등
- **4-6점**: 이 회사가 기사에 직접 등장하지만 주인공 아님 (비교, 시장 동향 내 언급)
- **1-3점**: 이 회사가 짧게 언급되거나 업계 동향만
- **0점**: 완전히 무관 (동음이의어, 업종 무관)

평가 프롬프트에는 반드시 `회사명`과 `핵심 사업` 모두 포함해야 함.

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

1. 필터링 전 기사 개수가 가장 많은 회사 찾기 (핫토픽) — 특별 회사(`KT`, `LP 출자 동향`) 제외
2. 해당 회사의 뉴스 중 가장 큰 클러스터 선택
3. 제목 형식: `KTI Portfolio Daily News(MM/DD: {대표 뉴스 30자})`

**날짜/연도 기준**: KST (UTC+9) — `datetime.now(timezone(timedelta(hours=9)))`

**예시:**
```
KTI Portfolio Daily News(02/19: AI 스타트업 투자 급증...)
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

### 특별 모니터링 회사 추가/수정 (CSV 외 관리)

CSV에 없는 회사(KT, LP 출자 동향 등)는 `utils/data_loader.py`의 `get_special_companies()` 함수에서 통합 관리합니다.

```python
def get_special_companies():
    return {
        "KT": { ... },
        "LP 출자 동향": { ... },
    }
```

- 이 함수만 수정하면 `main.py`, `test.py`, `email_sender.py` 전체에 자동 반영
- 특별 회사는 이메일 제목 생성 대상에서 자동 제외 (`SPECIAL_COMPANIES` 상수)
- 이메일 섹션 순서: 담당 포트폴리오 → 기타 포트폴리오 → 📡 KT 관련 기사 → 💰 LP 출자 동향

### 필터링 파라미터 조정

1. `filter_config.json` 수정
   - `relevance_threshold`: 점수 조정 (0-10)
   - `beta_test_mode`: 낮은 점수 기사 포함 여부
   - `enable_keyword_prefilter`: 키워드 없는 기사 사전 제거 (기본 `true`)
   - `relevance_criteria`: 평가 기준 커스터마이징 (없으면 DEFAULT_CRITERIA 사용)
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

### 배치 스코어링 결과가 모두 0점

- `gemini-3-flash-preview`가 응답 형식을 지키지 않아 파싱 실패하는 경우
- `utils/filter_similar_news.py`의 `check_news_relevance_batch()`에서 `response_mime_type="application/json"` + `response_schema` 설정 확인
- 텍스트 형식 프롬프트만으로는 신뢰할 수 없음 — JSON schema 강제 출력 필수

---

## Gmail iOS 다크모드 대응

### 문제점

아이폰 Gmail 앱의 다크모드는 **강제 색상 반전(Forced Color Inversion)** 알고리즘을 사용합니다:
- 어두운 배경색 → 밝은 색으로 반전
- 밝은 텍스트(흰색) → 어두운 색으로 반전
- CSS 미디어 쿼리(`@media (prefers-color-scheme: dark)`) 무시

이로 인해 의도한 브랜드 컬러가 변하거나 텍스트가 읽을 수 없게 됩니다.

### 적용된 해결책

**1. 배경색 반전 방지 - linear-gradient 핵**
```css
background-color: #090B43;
background-image: linear-gradient(#090B43, #090B43);
```
- Gmail은 그라디언트 배경을 "사용자 디자인"으로 인식하여 반전하지 않음
- 적용 위치: `.email-header` (헤더 배경)

**2. Gmail 전용 색상 지정 - data-ogsc**
```html
<td style="background-color: #090B43;" data-ogsc="#1C419A">
```
- `data-ogsc` = Original Gmail Skin Color
- Gmail 다크모드에서 지정한 색상 사용 (자동 변환 방지)
- 적용 위치: 헤더 `<td>` 태그

**3. 텍스트 색상 반전 방지 - mix-blend-mode 핵**
```html
<div class="gmail-blend-screen">
  <div class="gmail-blend-difference">
    <h1 style="color: #ffffff; text-shadow: 0 1px 0 #090B43;">
      Portfolio Daily News
    </h1>
  </div>
</div>
```

CSS:
```css
u + .body .gmail-blend-screen {
  background: #000;
  mix-blend-mode: screen;
}

u + .body .gmail-blend-difference {
  background: #000;
  mix-blend-mode: difference;
  color: #ffffff;
}
```

- `mix-blend-mode: screen`과 `difference`를 겹쳐서 Gmail의 반전 필터를 **수학적으로 상쇄**
- `u + .body` 선택자로 Gmail만 타겟팅
- `text-shadow` 추가로 Gmail이 텍스트를 "디자인 요소"로 인식하도록 유도

**4. 테이블 간격 제거**
```html
<table style="border-collapse: collapse; border-spacing: 0;
              background-color: #090B43;">
```
- 헤더와 본문 사이의 흰색 선(gap) 제거
- `vertical-align: bottom; line-height: 100%`로 셀 하단 공백 제거
- 부모 테이블 배경색을 헤더와 동일하게 설정하여 틈이 보이지 않도록

### 테스트 방법

1. `test_email_quick.py`로 테스트 이메일 발송
2. 아이폰 Gmail 앱에서 확인:
   - **라이트모드**: 진한 남색 헤더 (`#090B43`), 흰색 텍스트
   - **다크모드**: 파란색 헤더 (`#1C419A`), 흰색 텍스트 유지 (반전 안 됨)

### 참고 자료

이 방법들은 이메일 마케팅 업계에서 검증된 기법입니다:
- linear-gradient 핵: 가장 널리 사용되는 배경 보호 방법
- mix-blend-mode: 고급 기법으로 텍스트 반전 방지
- data-ogsc: Gmail 공식 지원 속성 (비공식 문서)

### 코드 위치

- `utils/email_sender.py`:
  - `get_email_styles()`: CSS 블렌드 모드 정의
  - `get_header_html()`: 헤더 HTML (이중 래퍼, data-ogsc)
  - `format_email_content()`: `<body class="body">` 추가
  - `get_footer_html()`: 푸터 (연도 KST 기준 자동 업데이트)

---

## 추가 참고사항

- **상세 문서**: `README.md` 참고
- **이메일 디자인 수정**: `utils/email_sender.py`의 HTML 템플릿 수정
- **스크래핑 로직 수정**: `utils/fetch_news.py` (Playwright 셀렉터 주의)
- **GitHub Actions 로그**: Actions 탭에서 실행 기록 확인
