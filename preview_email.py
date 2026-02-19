"""
이메일 HTML 미리보기 생성 스크립트
브라우저에서 확인할 수 있도록 preview_email.html 파일 생성
"""

from utils.email_sender import format_email_content

# 테스트용 더미 데이터
dummy_news_data = {
    "힐링페이퍼": {
        "news_list": [
            ("힐링페이퍼, AI 기반 디지털 플래너 서비스 출시", "힐링페이퍼가 인공지능 기술을 활용한 스마트 플래너를 선보였다.", "https://example.com/news1", 8),
            ("힐링페이퍼 매출 전년 대비 150% 증가", "힐링페이퍼의 올해 매출이 급증하며 성장세를 이어가고 있다.", "https://example.com/news2", 7),
        ],
        "keyword": ["힐링페이퍼"],
        "pre_filter_count": 15,
        "cluster_sizes": {}
    },
    "클래스101": {
        "news_list": [
            ("클래스101, 해외 시장 진출 본격화", "클래스101이 동남아시아 시장 공략에 나섰다.", "https://example.com/news3"),
            ("클래스101 창작자 생태계 확대", "클래스101의 크리에이터 수가 10만명을 돌파했다.", "https://example.com/news4"),
        ],
        "keyword": ["클래스101"],
        "pre_filter_count": 12,
        "cluster_sizes": {}
    },
    "뉴로메카": {
        "news_list": [
            ("뉴로메카, 협동로봇 신제품 공개", "뉴로메카가 차세대 협동로봇을 CES 2026에서 공개했다.", "https://example.com/news5", 9),
        ],
        "keyword": ["뉴로메카"],
        "pre_filter_count": 8,
        "cluster_sizes": {}
    },
    "KT": {
        "news_list": [
            ("KT, 6G 기술 개발 가속화", "KT가 6G 이동통신 기술 개발에 박차를 가하고 있다.", "https://example.com/news6"),
            ("KT, AI 데이터센터 구축 완료", "KT가 경기도에 대규모 AI 데이터센터를 준공했다.", "https://example.com/news7", 8),
            ("KT클라우드, 클라우드 서비스 확대", "KT클라우드가 기업용 클라우드 솔루션을 강화한다.", "https://example.com/news8", 7),
        ],
        "keyword": ["KT / 케이티"],
        "pre_filter_count": 25,
        "cluster_sizes": {}
    }
}

# 담당 회사 설정 (힐링페이퍼만 담당)
user_companies = ["힐링페이퍼"]

# HTML 생성
html_content = format_email_content(dummy_news_data, "테스트 사용자", user_companies)

# 파일로 저장
output_file = "preview_email.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ HTML 파일 생성 완료: {output_file}")
print(f"📂 파일 경로: /Users/woo-seokchoi/desktop/01. codes/kti-newsletter/{output_file}")
print("\n브라우저에서 열어보세요:")
print(f"  open {output_file}")
print("\n예상 구조:")
print("  1. 📌 담당 포트폴리오 (힐링페이퍼)")
print("  2. 📋 기타 포트폴리오 (클래스101, 뉴로메카)")
print("  3. 📡 KT 관련 기사 (KT)")
print("\n✨ '참고' 박스의 margin이 제거되었는지 확인하세요!")
