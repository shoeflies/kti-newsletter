"""
빠른 이메일 테스트 스크립트
- API 호출 없이 더미 데이터로 HTML 이메일만 생성하고 발송
- .env 파일에서 모든 설정 자동 로드

사용법:
    python3 test_email_quick.py
"""

from utils.email_sender import format_email_content, send_email
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 필수 환경변수 확인
required_vars = ["TEST_EMAIL", "SMTP_SERVER", "SMTP_PORT", "EMAIL_LOGIN", "EMAIL_PASSWORD"]
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"❌ ERROR: .env 파일에 다음 환경변수가 설정되지 않았습니다:")
    for var in missing_vars:
        print(f"   - {var}")
    exit(1)

# 더미 뉴스 데이터
dummy_news_data = {
    "힐링페이퍼": {
        "news_list": [
            ("힐링페이퍼, 반려동물 헬스케어 서비스 출시", "반려동물의 건강을 관리하는 새로운 서비스를 출시했다", "https://example.com/1"),
            ("펫케어 시장 성장세 지속", "반려동물 케어 시장이 급성장하고 있다", "https://example.com/2", 8),
            ("힐링페이퍼 신규 투자 유치", "시리즈 A 투자 유치 성공", "https://example.com/3", 9),
        ],
        "keyword": ["힐링페이퍼 / 펫케어 / 반려동물"],
        "pre_filter_count": 5,
        "cluster_sizes": {"힐링페이퍼, 반려동물 헬스케어 서비스 출시": 3}
    },
    "클래스101": {
        "news_list": [
            ("클래스101, 신규 클래스 100개 오픈", "새로운 취미 클래스 대거 공개", "https://example.com/4"),
            ("온라인 교육 시장 호황", "클래스101 등 온라인 교육 플랫폼 성장", "https://example.com/5", 6),
        ],
        "keyword": ["클래스101"],
        "pre_filter_count": 3,
        "cluster_sizes": {"클래스101, 신규 클래스 100개 오픈": 2}
    },
    "뉴로메카": {
        "news_list": [
            ("뉴로메카, 협동로봇 신제품 출시", "산업용 협동로봇 신제품 발표", "https://example.com/6", 10),
        ],
        "keyword": ["뉴로메카"],
        "pre_filter_count": 2,
        "cluster_sizes": {}
    },
    "KT": {
        "news_list": [
            ("KT, AI 기반 통신 서비스 확대", "KT가 AI 기술을 활용한 신규 통신 서비스를 발표했다", "https://example.com/7"),
            ("케이티, 데이터센터 투자 확대", "KT가 대규모 데이터센터 투자 계획을 밝혔다", "https://example.com/8"),
        ],
        "keyword": ["KT / 케이티"],
        "pre_filter_count": 4,
        "cluster_sizes": {}
    },
    "LP 출자 동향": {
        "news_list": [
            ("모태펀드, 2026년 1분기 출자 계획 발표", "중소벤처기업부 모태펀드가 1분기 출자 사업 공고를 냈다", "https://example.com/9"),
            ("성장금융, 스케일업 펀드 출자사 선정", "한국성장금융이 스케일업 펀드 운용사를 선정했다", "https://example.com/10"),
            ("연기금, 벤처펀드 출자 확대 검토", "국민연금 등 주요 연기금이 벤처펀드 출자 비중 확대를 검토 중이다", "https://example.com/11"),
        ],
        "keyword": ["모태펀드 / 벤처 출자 / 성장금융 / LP 출자"],
        "pre_filter_count": 6,
        "cluster_sizes": {}
    }
}

# 테스트 설정
user_name = "테스트 사용자"
user_companies = ["힐링페이퍼", "클래스101"]  # 담당 회사
test_email = os.environ.get("TEST_EMAIL")

print("=" * 60)
print("📧 빠른 이메일 테스트")
print("=" * 60)
print(f"수신자: {test_email}")
print(f"SMTP: {os.environ.get('SMTP_SERVER')}:{os.environ.get('SMTP_PORT')}")
print("=" * 60 + "\n")

# HTML 이메일 생성
print("📧 Generating email HTML...")
email_body = format_email_content(dummy_news_data, user_name, user_companies)
email_subject = "Portfolio Daily News - Quick Test"

# 이메일 발송
print(f"📤 Sending test email to {test_email}...")
try:
    send_email(email_body, [test_email], email_subject)
    print(f"✅ Test email sent successfully!")
    print("\n💡 Tip: 라이트모드와 다크모드 모두 확인해보세요!")
except Exception as e:
    print(f"❌ Failed to send email: {str(e)}")
