from tqdm import tqdm
from utils.data_loader import load_json, load_company_info_from_csv, load_filter_config
from utils.email_sender import format_email_content, send_email
from utils.filter_similar_news import filter_similar_titles, filter_news_by_relevance
from utils.fetch_news import make_target_url, fetch_news
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify environment variables are loaded
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

# Load configuration files
news_dict = {}
company_info = load_company_info_from_csv()
user_info = load_json("user_info.json")

# KT 수동 추가 (CSV에 없는 회사)
company_info["KT"] = {
    "comment": ["국내 최대 통신사이자 디지털 플랫폼 기업으로 ICT, 금융사업, 위성방송서비스사업, 기타사업 등을 영위"],
    "keyword": ["KT / 케이티"],
    "manager": []  # 담당자 없음
}


def reorder_news_dict(news_dict, user_companies):
    reordered_dict = {}
    for company in user_companies:
        if company in news_dict.keys():
            reordered_dict[company] = news_dict[company]

    for company, _ in news_dict.items():
        if company not in reordered_dict:
            reordered_dict[company] = news_dict[company]

    return reordered_dict


def generate_email_subject(news_data, user_companies):
    """
    이메일 제목 생성: KTI Portfolio Daily News(MM/DD: {뉴스 요약})

    Args:
        news_data: 회사별 뉴스 데이터 (pre_filter_count, cluster_sizes 포함)
        user_companies: 담당 회사 리스트 (미사용)

    Returns:
        "KTI Portfolio Daily News(01/15: AI 스타트업 투자 급증)"
    """
    # 현재 날짜 (MM/DD)
    today = datetime.now()
    date_str = today.strftime("%m/%d")

    # 대표 뉴스 선택: 필터링 전 기사 개수가 가장 많은 회사 (가장 핫한 토픽)
    representative_news = None
    max_pre_filter_count = 0
    max_company = None

    # 필터링 전 기사 개수가 가장 많은 회사 찾기 (KT 제외)
    for company, data in news_data.items():
        if company == "KT":  # KT는 제목 생성 대상에서 제외
            continue
        pre_filter_count = data.get("pre_filter_count", 0)
        if pre_filter_count > max_pre_filter_count:
            max_pre_filter_count = pre_filter_count
            max_company = company

    # 해당 회사의 뉴스 중 가장 큰 클러스터를 대표하는 뉴스 선택
    if max_company and news_data[max_company]["news_list"]:
        news_list = news_data[max_company]["news_list"]
        cluster_sizes = news_data[max_company].get("cluster_sizes", {})

        if cluster_sizes:
            # 각 뉴스의 클러스터 크기를 확인하여 가장 큰 것 선택
            max_cluster_size = 0
            for news in news_list:
                # news는 (title, description, url) 또는 (title, description, url, score)
                news_title = news[0]
                cluster_size = cluster_sizes.get(news_title, 1)
                if cluster_size > max_cluster_size:
                    max_cluster_size = cluster_size
                    representative_news = news
        else:
            # 클러스터 정보가 없으면 첫 번째 뉴스 선택
            representative_news = news_list[0]

    # 뉴스 제목 요약 (30글자로 자르기)
    if representative_news:
        title = representative_news[0]
        summary = title[:30] + ("..." if len(title) > 30 else "")
    else:
        summary = "업데이트"

    return f"KTI Portfolio Daily News({date_str}: {summary})"


async def main():
    news_count = 0
    # 필터링 전 기사 개수 저장 (클러스터 크기 추정용)
    pre_filter_counts = {}
    # 각 뉴스의 클러스터 크기 저장
    cluster_sizes = {}

    # Step 1: 키워드로 뉴스 검색 및 중복 제거
    print("\n=== Step 1: Fetching news and removing duplicates ===")
    for company, detail in tqdm(company_info.items()):
        await asyncio.sleep(1.5)
        articles = []
        for keyword in detail["keyword"][0].split("/"):
            target_url = make_target_url(keyword)
            articles += await fetch_news(target_url)
            await asyncio.sleep(1.5)
            print(company, ":", keyword)

        # 필터링 전 기사 개수 저장 (많을수록 핫토픽)
        pre_filter_counts[company] = len(articles)

        titles = [i[0] for i in articles]
        # 클러스터 정보 포함해서 반환 {인덱스: 클러스터_크기}
        cluster_info = filter_similar_titles(titles, return_cluster_info=True)

        filtered_articles = [articles[i] for i in cluster_info.keys()]

        if len(filtered_articles) != 0:
            news_dict[company] = filtered_articles
            # 클러스터 크기 정보를 제목 기반으로 저장 (순서 변경에 안전)
            cluster_sizes[company] = {articles[idx][0]: size for idx, size in cluster_info.items()}
            news_count += len(filtered_articles)

    if news_count == 0:
        print("No news found")
        return

    print(f"\nTotal news after deduplication: {news_count}")

    # Step 2: AI 기반 관련성 필터링 (설정: filter_config.json)
    filter_cfg = load_filter_config()
    enable_relevance_filter = filter_cfg["enable_relevance_filter"]
    beta_test_mode = filter_cfg["beta_test_mode"]

    if enable_relevance_filter:
        print("\n=== Step 2: AI-based relevance filtering ===")
        relevance_threshold = filter_cfg["relevance_threshold"]
        enable_keyword_prefilter = filter_cfg.get("enable_keyword_prefilter", True)
        enable_keyword_in_prompt = filter_cfg.get("enable_keyword_in_prompt", True)

        print(f"Relevance threshold: {relevance_threshold}/10")
        print(f"Keyword prefilter: {'ON' if enable_keyword_prefilter else 'OFF'}")
        print(f"Keyword in prompt: {'ON' if enable_keyword_in_prompt else 'OFF'}")

        if beta_test_mode:
            print(
                "⚠️  BETA TEST MODE: Low relevance news will be included with warnings"
            )

        # AI 관련성 필터링 적용
        filtered_news_dict = filter_news_by_relevance(
            news_dict,
            company_info,
            threshold=relevance_threshold,
            beta_mode=beta_test_mode,
            enable_keyword_prefilter=enable_keyword_prefilter,
            enable_keyword_in_prompt=enable_keyword_in_prompt,
        )

        # 필터링된 결과로 업데이트
        news_dict.clear()
        news_dict.update(filtered_news_dict)

        final_news_count = sum(len(articles) for articles in news_dict.values())
        print(f"\nFinal news count after relevance filtering: {final_news_count}")

        if final_news_count == 0:
            print("No relevant news found after filtering")
            return
    else:
        print("\n=== Step 2: AI relevance filtering is DISABLED ===")
        print("Set enable_relevance_filter to true in filter_config.json to enable it")

    # 테스트 복사본 발송 설정 확인
    send_test_copy = filter_cfg.get("send_test_copy", False)
    test_email = os.environ.get("TEST_EMAIL")

    if send_test_copy and test_email:
        print(f"\n⚠️  Test copy mode: All emails will also be sent to {test_email}")
    elif send_test_copy and not test_email:
        print("\n⚠️  Warning: send_test_copy is enabled but TEST_EMAIL is not set")

    # 유저별 뉴스 정렬 후 이메일 발송
    print("\n=== Sending emails to users ===")
    for user_name, _ in user_info.items():
        # company_info에서 해당 manager가 담당하는 회사 목록 추출
        user_companies = [
            company
            for company, info in company_info.items()
            if user_name in info.get("manager", [])
        ]

        user_email = user_info.get(user_name, {}).get("email", [])

        if user_companies:
            reordered_news_dict = reorder_news_dict(news_dict, user_companies)
        else:
            reordered_news_dict = news_dict

        result_dict = {}
        for company, news_list in reordered_news_dict.items():
            result_dict[company] = {"news_list": [], "keyword": [], "pre_filter_count": 0, "cluster_sizes": {}}
            result_dict[company]["news_list"] = news_list
            result_dict[company]["keyword"] = company_info[company]["keyword"]
            result_dict[company]["pre_filter_count"] = pre_filter_counts.get(company, 0)
            result_dict[company]["cluster_sizes"] = cluster_sizes.get(company, {})

        email_body = format_email_content(result_dict, user_name, user_companies)
        email_subject = generate_email_subject(result_dict, user_companies)

        # 정식 발송
        print(f"Sending to {user_name}: {user_email}")
        send_email(email_body, user_email, email_subject)

        # 테스트 복사본 발송 (설정 활성화 시)
        if send_test_copy and test_email:
            print(f"  └─ Sending test copy to {test_email}")
            send_email(email_body, [test_email], f"[TEST: {user_name}] {email_subject}")


if __name__ == "__main__":
    asyncio.run(main())
