# 로컬 테스트 가이드

GitHub Actions 없이 로컬에서 빠르게 테스트하는 방법입니다.

## 사전 준비

### 1. 의존성 설치

```bash
cd /Users/woo-seokchoi/desktop/01.\ codes/kti-newsletter

# google-genai 패키지 설치 (최신 SDK)
pip install google-genai

# 또는 전체 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일이 이미 있다면 그대로 사용하면 됩니다.

```bash
# .env 파일 확인
cat .env

# 필요한 환경변수:
# GEMINI_API_KEY=your_api_key_here
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# EMAIL_LOGIN=your_email@gmail.com
# EMAIL_PASSWORD=your_app_password
```

## 테스트 실행

### 방법 1: test.py (6개 회사만 테스트)

```bash
# 이메일 주소 설정
export TEST_EMAIL="your-email@example.com"

# 실행
python3 test.py
```

**장점:**
- 빠름 (6개 회사만)
- 본인 이메일로만 발송
- AI 필터 설정 확인 가능

### 방법 2: main.py (전체 74개 회사)

```bash
# 테스트 모드로 실행 (본인 이메일로만 발송)
export TEST_EMAIL="your-email@example.com"

# 실행
python3 main.py
```

**주의:** TEST_EMAIL 설정 시 모든 담당자의 이메일이 무시되고 TEST_EMAIL로만 발송됩니다!

## 디버깅 팁

### 1. AI 필터 끄기

빠른 테스트를 위해 AI 필터를 비활성화:

```json
// filter_config.json
{
  "enable_relevance_filter": false,  // ← AI 필터 끄기
  "relevance_threshold": 7,
  "beta_test_mode": false
}
```

### 2. Beta 모드 (모든 뉴스 포함)

점수가 낮아도 모든 뉴스 확인:

```json
{
  "enable_relevance_filter": true,
  "relevance_threshold": 7,
  "beta_test_mode": true  // ← 낮은 점수도 포함
}
```

### 3. 이메일 없이 HTML만 생성

```bash
python3 generate_preview.py
open preview_email.html
```

## 트러블슈팅

### "ModuleNotFoundError: No module named 'google.genai'"

```bash
pip install google-genai
```

### "GEMINI_API_KEY environment variable is not set"

```bash
# .env 파일 확인
cat .env

# 또는 직접 설정
export GEMINI_API_KEY="your_api_key_here"
```

### 이메일 발송 실패

```bash
# SMTP 설정 확인
echo $SMTP_SERVER
echo $EMAIL_LOGIN

# 앱 비밀번호 생성 (Gmail)
# https://myaccount.google.com/apppasswords
```

## 주의사항

⚠️ **TEST_EMAIL 설정 시 프로덕션 이메일 덮어쓰기**
- `TEST_EMAIL` 환경변수가 설정되면 user_info.json 무시
- 모든 이메일이 TEST_EMAIL로만 발송
- 프로덕션 배포 전 반드시 TEST_EMAIL 제거

⚠️ **API 비용**
- AI 필터 활성화 시 Gemini API 호출 발생
- 테스트 시 비용 발생 가능
- 필요 없으면 `enable_relevance_filter: false`

⚠️ **로컬 변경사항 커밋 주의**
- filter_config.json 변경 후 커밋하지 않도록 주의
- 또는 .gitignore에 추가
