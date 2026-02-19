#!/usr/bin/env python3
"""
이메일 디자인 로컬 테스트 스크립트
브라우저에서 test_email.html을 열어서 디자인을 확인할 수 있습니다.
"""

from utils.email_sender import format_email_content

# 테스트 데이터
test_data = {
    "AI 헬스케어 스타트업": {
        "keyword": ["AI", "헬스케어", "의료", "진단"],
        "news_list": [
            (
                "AI 기반 암 진단 솔루션, FDA 승인 획득",
                "인공지능을 활용한 조기 암 진단 시스템이 미국 FDA의 최종 승인을 받았습니다. 이 시스템은 기존 진단 방식 대비 정확도가 25% 향상되었으며...",
                "https://example.com/news1",
                9
            ),
            (
                "병원 경영 컨설팅 시장 성장 전망",
                "국내 병원 경영 컨설팅 시장이 지속적으로 성장하고 있다. 의료 경영 효율화에 대한 수요가 증가하면서...",
                "https://example.com/news2",
                4
            ),
        ]
    },
    "핀테크 플랫폼": {
        "keyword": ["핀테크", "금융", "결제", "송금"],
        "news_list": [
            (
                "모바일 간편결제 시장 점유율 1위 달성",
                "올해 2분기 모바일 간편결제 시장에서 점유율 1위를 기록했습니다. 전년 동기 대비 거래액이 150% 증가하며...",
                "https://example.com/news3",
                10
            ),
            (
                "블록체인 기반 국제송금 서비스 출시",
                "블록체인 기술을 활용한 새로운 국제송금 서비스가 정식 출시되었습니다. 기존 송금 방식 대비 수수료가 70% 절감되며...",
                "https://example.com/news4",
                8
            ),
            (
                "금융위원회, 새로운 규제안 발표",
                "금융위원회가 핀테크 산업에 대한 새로운 규제안을 발표했습니다. 업계에서는 규제 완화를 요구하고 있으나...",
                "https://example.com/news5",
                5
            ),
        ]
    },
    "친환경 에너지": {
        "keyword": ["태양광", "신재생에너지", "ESG", "탄소중립"],
        "news_list": [
            (
                "대규모 태양광 발전단지 착공",
                "전남 지역에 국내 최대 규모의 태양광 발전단지 건설이 시작되었습니다. 총 사업비 2천억 원 규모로...",
                "https://example.com/news6",
                7
            ),
        ]
    }
}

# HTML 생성
html_content = format_email_content(test_data, "테스터")

# 파일로 저장
output_path = "test_email.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ 테스트 이메일 HTML이 생성되었습니다: {output_path}")
print(f"브라우저에서 파일을 열어 디자인을 확인하세요.")
print(f"\n다음 항목을 확인하세요:")
print("[ ] 헤더 KTI 네이비 배경 (#090B43)")
print("[ ] 공지 박스 스타일")
print("[ ] 회사 섹션 구분")
print("[ ] 뉴스 카드 그림자/보더")
print("[ ] 관련성 배지 색상 (초록: 높음, 주황: 낮음)")
print("[ ] KTI 레드 버튼 링크 (#D93931)")
print("[ ] 모바일 반응형 (브라우저 창 크기 조절)")
print("[ ] 다크모드 (시스템 설정 변경)")
