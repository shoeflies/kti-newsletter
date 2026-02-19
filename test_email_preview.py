"""이메일 HTML 프리뷰 생성 스크립트"""
import sys
import os

# utils 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from utils.email_sender import format_email_content

# 테스트 데이터
test_news_data = {
    "포트폴리오 회사 A": {
        "news_list": [
            ("AI 스타트업 투자 급증, 벤처캐피탈 관심 집중", "인공지능 기술을 보유한 스타트업에 대한 투자가 급증하고 있습니다.", "https://example.com/news1", 9),
            ("블록체인 기술 발전으로 새로운 비즈니스 모델 등장", "블록체인 기술이 다양한 산업에 적용되고 있습니다.", "https://example.com/news2", 7),
            ("메타버스 시장 확대, 글로벌 기업들 투자 본격화", "메타버스 시장이 빠르게 성장하고 있습니다.", "https://example.com/news3", 8),
        ],
        "keyword": ["AI", "스타트업", "투자"],
        "pre_filter_count": 25,
        "cluster_sizes": {
            "AI 스타트업 투자 급증, 벤처캐피탈 관심 집중": 15,
            "블록체인 기술 발전으로 새로운 비즈니스 모델 등장": 6,
            "메타버스 시장 확대, 글로벌 기업들 투자 본격화": 4,
        }
    },
    "포트폴리오 회사 B": {
        "news_list": [
            ("클라우드 서비스 시장 성장세 지속", "클라우드 컴퓨팅 수요가 계속 증가하고 있습니다.", "https://example.com/news4", 8),
            ("사이버 보안 위협 증가, 보안 솔루션 수요 급증", "기업들의 보안 투자가 늘어나고 있습니다.", "https://example.com/news5", 6),
        ],
        "keyword": ["클라우드", "보안"],
        "pre_filter_count": 18,
        "cluster_sizes": {
            "클라우드 서비스 시장 성장세 지속": 12,
            "사이버 보안 위협 증가, 보안 솔루션 수요 급증": 6,
        }
    },
    "포트폴리오 회사 C": {
        "news_list": [
            ("전기차 배터리 기술 혁신 가속화", "차세대 배터리 기술 개발이 활발합니다.", "https://example.com/news6", 9),
        ],
        "keyword": ["전기차", "배터리"],
        "pre_filter_count": 12,
        "cluster_sizes": {
            "전기차 배터리 기술 혁신 가속화": 12,
        }
    },
}

# 담당 회사 (테스트용)
user_companies = ["포트폴리오 회사 A", "포트폴리오 회사 B"]

# HTML 생성
html_content = format_email_content(test_news_data, "테스트 사용자", user_companies)

# HTML 파일로 저장
output_path = "/Users/woo-seokchoi/Desktop/01. Codes/kti-newsletter/email_preview.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ 이메일 미리보기 생성 완료: {output_path}")
print(f"📧 담당 포트폴리오: {', '.join(user_companies)}")
print(f"📧 기타 포트폴리오: 포트폴리오 회사 C")
