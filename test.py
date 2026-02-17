"""
테스트용 뉴스봇: main.py와 동일한 흐름.
- 검색 회사 수 제한 (TEST_MAX_COMPANIES)
- 발신/수신: TEST_EMAIL로만 발송, TEST_USER_NAME으로 표시
- 테스트에서는 두 번째 로직(2.5-flash 관련성 필터)은 끄고, 첫 번째 로직(임베딩 유사도 중복 제거)만 실행
"""

from tqdm import tqdm
from utils.data_loader import load_company_info_from_csv
from utils.email_sender import format_email_content, send_email
from utils.filter_similar_news import filter_similar_titles
from utils.fetch_news import make_target_url, fetch_news
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

required_env_vars = [
    "GEMINI_API_KEY",
    "SMTP_SERVER",
    "SMTP_PORT",
    "EMAIL_LOGIN",
    "EMAIL_PASSWORD",
]

missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing_vars)}"
    )

# 테스트 제한
TEST_COMPANIES = ["뉴로메카", "리벨리온"]
TEST_EMAIL = os.environ.get("TEST_EMAIL")
TEST_USER_NAME = os.environ.get("TEST_USER_NAME", "테스트")

# 테스트용 회사만 사용
_all_company_info = load_company_info_from_csv()
company_info = {
    k: _all_company_info[k] for k in TEST_COMPANIES if k in _all_company_info
}

# 테스트용 user_info: 한 명만, TEST_EMAIL로
user_info = {TEST_USER_NAME: {"email": [TEST_EMAIL]}}

news_dict = {}

print("\n" + "=" * 60)
print("TEST MODE (main.py와 동일 흐름, 회사/수신 제한)")
print("=" * 60)
print(f"Companies: {list(company_info.keys())}")
print(f"Recipient: {TEST_EMAIL} ({TEST_USER_NAME})")
print("Relevance filter (2.5-flash): OFF → 임베딩 중복 제거만 실행")
print("=" * 60 + "\n")


def reorder_news_dict(news_dict, user_companies):
    reordered_dict = {}
    for company in user_companies:
        if company in news_dict.keys():
            reordered_dict[company] = news_dict[company]
    for company, _ in news_dict.items():
        if company not in reordered_dict:
            reordered_dict[company] = news_dict[company]
    return reordered_dict


async def main():
    news_count = 0

    # Step 1: 키워드로 뉴스 검색 + 임베딩 유사도 중복 제거 (첫 번째 로직)
    print("\n=== Step 1: Fetching news and removing duplicates (embedding) ===")
    for company, detail in tqdm(company_info.items()):
        await asyncio.sleep(1.5)
        articles = []
        for keyword in detail["keyword"][0].split("/"):
            target_url = make_target_url(keyword)
            articles += await fetch_news(target_url)
            await asyncio.sleep(1.5)
            print(company, ":", keyword)

        titles = [i[0] for i in articles]
        idx_list = filter_similar_titles(titles)
        filtered_articles = [articles[i] for i in idx_list]

        if len(filtered_articles) != 0:
            news_dict[company] = filtered_articles
            news_count += len(filtered_articles)

    if news_count == 0:
        print("No news found")
        return

    print(f"\nTotal news after deduplication: {news_count}")

    # Step 2: 테스트에서는 관련성 필터(2.5-flash) 끔 → 첫 번째 로직만 사용
    print("\n=== Step 2: AI relevance filtering is DISABLED (test mode) ===")

    # 유저별 뉴스 정렬 후 이메일 발송 (main과 동일 구조, 테스트는 1명만)
    for user_name, _ in user_info.items():
        user_companies = [
            company
            for company, info in company_info.items()
            if user_name in info.get("manager", [])
        ]
        if not user_companies:
            user_companies = list(company_info.keys())

        user_email = user_info.get(user_name, {}).get("email", [TEST_EMAIL])
        if not user_email:
            user_email = [TEST_EMAIL]

        reordered_news_dict = reorder_news_dict(news_dict, user_companies)

        result_dict = {}
        for company, news_list in reordered_news_dict.items():
            result_dict[company] = {"news_list": [], "keyword": []}
            result_dict[company]["news_list"] = news_list
            result_dict[company]["keyword"] = company_info[company]["keyword"]

        email_body = format_email_content(result_dict, user_name)
        print(f"Sending test email to {user_email[0]}...")
        send_email(email_body, user_email)

    print("\nTest completed. Email sent to:", TEST_EMAIL)


if __name__ == "__main__":
    asyncio.run(main())
