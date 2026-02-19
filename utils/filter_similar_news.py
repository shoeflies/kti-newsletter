from dotenv import load_dotenv
from google import genai
from google.genai import types
import numpy as np
import time
import os

# Load environment variables
load_dotenv()

# Configure Gemini API with new SDK
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    raise EnvironmentError("GEMINI_API_KEY environment variable is not set")

# Initialize client (new unified SDK)
client = genai.Client(api_key=gemini_api_key)

# Embedding model (Gemini)
EMBEDDING_MODEL = "gemini-embedding-001"
# Text generation model for relevance scoring
GENERATION_MODEL_NAME = "gemini-3-flash-preview"


def _is_rate_limit_error(e):
    s = str(e).lower()
    return (
        "429" in s or "rate_limit" in s or "too many" in s or "too many requests" in s
    )


def get_embedding(text, model=EMBEDDING_MODEL):
    max_retries = 4
    wait_times = [2, 5, 15, 30]
    for attempt in range(max_retries):
        try:
            # New API: client.models.embed_content with 'contents' parameter
            result = client.models.embed_content(
                model=model,
                contents=text
            )
            # New SDK returns Pydantic object with embeddings attribute
            return result.embeddings[0].values
        except Exception as e:
            if _is_rate_limit_error(e) and attempt < max_retries - 1:
                print(f"Rate limit (embedding), retrying in {wait_times[attempt]}s...")
                time.sleep(wait_times[attempt])
            else:
                raise
    return None  # unreachable


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def filter_similar_titles(titles, threshold=0.60, return_cluster_info=False):
    embeddings = []
    for title in titles:
        try:
            embedding = get_embedding(title)
            embeddings.append(embedding)
            time.sleep(1.0)  # Rate limiting: avoid 429
        except Exception as e:
            print(f"Error processing title '{title}': {str(e)}")
            continue

    if not embeddings:
        return [] if not return_cluster_info else {}

    # 각 유니크 제목과 그것이 대표하는 클러스터 크기 추적
    unique_titles = []  # [(title, embedding, idx, cluster_size), ...]

    for i, embedding in enumerate(embeddings):
        is_unique = True
        for j, unique_item in enumerate(unique_titles):
            if cosine_similarity(embedding, unique_item[1]) > threshold:
                # 유사한 제목 발견 → 기존 클러스터에 추가
                is_unique = False
                # 클러스터 크기 증가
                unique_titles[j] = (unique_item[0], unique_item[1], unique_item[2], unique_item[3] + 1)
                break
        if is_unique:
            # 새로운 클러스터 시작 (초기 크기 1)
            unique_titles.append((titles[i], embedding, i, 1))

    if return_cluster_info:
        # {인덱스: 클러스터 크기} 형태로 반환
        return {idx: cluster_size for _, _, idx, cluster_size in unique_titles}
    else:
        # 기존 방식: 인덱스 리스트만 반환
        return [idx for _, _, idx, _ in unique_titles]


def check_news_relevance(news_title, news_description, business_content,
                         company_name="", keywords=None,
                         enable_keyword_prefilter=True, enable_keyword_in_prompt=True):
    """
    뉴스 기사가 회사 사업 내용과 얼마나 관련이 있는지 0-10 점수로 평가

    Args:
        news_title: 뉴스 제목
        news_description: 뉴스 내용
        business_content: 회사 사업 내용
        company_name: 회사명
        keywords: 키워드 리스트 (예: ["힐링페이퍼", "강남언니", "UNNI"])
        enable_keyword_prefilter: 사전 키워드 필터링 활성화
        enable_keyword_in_prompt: 프롬프트에 키워드 정보 포함
    """
    max_retries = 4
    wait_times = [5, 15, 30, 60]  # 429 시 대기 (초)

    # 키워드 리스트 준비
    if keywords is None:
        keywords = []

    # A. 사전 키워드 필터링
    if enable_keyword_prefilter and (company_name or keywords):
        news_text = f"{news_title} {news_description}".lower()
        all_keywords = [company_name] + keywords if company_name else keywords

        # 키워드 중 하나라도 뉴스에 포함되어 있는지 확인
        has_keyword = any(kw.lower() in news_text for kw in all_keywords if kw)

        if not has_keyword:
            # print(f"    [Prefilter] No keyword found in news - returning 0")
            return 0

    # B. 프롬프트에 키워드 정보 포함
    system_instruction = "당신은 뉴스 기사와 회사 사업의 관련성을 평가하는 전문가입니다. 0-10 사이의 숫자로만 답변하세요."

    # 키워드 정보 추가
    keyword_info = ""
    if enable_keyword_in_prompt and (company_name or keywords):
        keyword_info = f"""
    회사명: {company_name}
    관련 키워드: {', '.join(keywords)}

    ⚠️ 중요: 뉴스 제목이나 내용에 회사명 또는 관련 키워드가 명시적으로 언급되어야 높은 점수를 받을 수 있습니다.
    키워드가 전혀 포함되지 않았지만 사업 분야만 유사한 경우 최대 3점까지만 부여하세요.
    """

    prompt = f"""다음 뉴스 기사가 회사의 사업 내용과 얼마나 관련이 있는지 0-10 점수로 평가해주세요.

    뉴스 제목: {news_title}
    뉴스 내용: {news_description}

    회사 사업 내용: {business_content}{keyword_info}

    평가 기준:
    - 10점: 회사명/키워드가 명시되고 핵심 사업에 직접 관련된 뉴스
    - 7-9점: 회사명/키워드가 명시되고 다음 중 하나에 해당하는 뉴스
        * 사업 분야와 밀접하게 관련된 내용
        * IPO, 상장, 투자 유치, M&A, 인수합병 등 기업 재무/경영 이벤트
        * 임원 선임, 조직 변화, 파트너십 등 주요 기업 동향
    - 4-6점: 회사명/키워드가 명시되고 산업/시장과 간접적으로 관련된 뉴스
    - 1-3점: 회사명만 언급되거나 키워드 없이 산업만 유사한 뉴스
    - 0점: 완전히 관련 없는 뉴스 (동음이의어, 오타, 키워드 없음)

    0-10 사이의 숫자만 답변해주세요."""

    for attempt in range(max_retries):
        try:
            # New API: client.models.generate_content with GenerateContentConfig
            response = client.models.generate_content(
                model=GENERATION_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=100,  # 충분한 토큰 할당
                    temperature=0.3,
                )
            )

            # New SDK: response.text directly accessible
            answer = response.text.strip() if response.text else ""

            try:
                score = int(answer) if answer else 0
                if 0 <= score <= 10:
                    return score
                else:
                    print(f"Warning: Score {score} out of range, defaulting to 0")
                    return 0
            except ValueError:
                print(f"Warning: Could not parse score '{answer}', defaulting to 0")
                return 0

        except Exception as e:
            if _is_rate_limit_error(e):
                if attempt < max_retries - 1:
                    print(f"Rate limit (429), retrying in {wait_times[attempt]}s...")
                    time.sleep(wait_times[attempt])
                else:
                    print(
                        f"Error checking relevance after {max_retries} attempts: {str(e)}"
                    )
                    return 0
            elif attempt == max_retries - 1:
                print(
                    f"Error checking relevance after {max_retries} attempts: {str(e)}"
                )
                return 0
            else:
                print(f"Error checking relevance: {str(e)}")
                return 0

    return 0


def filter_news_by_relevance(news_data, company_info, threshold=6, beta_mode=False,
                            enable_keyword_prefilter=True, enable_keyword_in_prompt=True):
    """
    AI 기반 관련성 점수로 뉴스 필터링

    Args:
        news_data: 뉴스 데이터
        company_info: 회사 정보
        threshold: 관련성 임계값
        beta_mode: 베타 모드
        enable_keyword_prefilter: 사전 키워드 필터링 활성화
        enable_keyword_in_prompt: 프롬프트에 키워드 정보 포함
    """
    from utils.data_loader import load_filter_config

    # 설정 로드 (함수 파라미터로 전달된 것 우선)
    config = load_filter_config()

    filtered_news_data = {}
    total_news = 0
    filtered_news_count = 0
    low_relevance_count = 0

    for company, news_list in news_data.items():
        # comment는 리스트이므로 첫 번째 요소 추출
        comments = company_info.get(company, {}).get("comment", [])
        business_content = comments[0] if comments else ""

        if not business_content:
            print(
                f"Warning: No business content for {company}, skipping relevance check"
            )
            filtered_news_data[company] = news_list
            continue

        # 키워드 추출 (예: "힐링페이퍼 / 강남언니 / UNNI" → ["힐링페이퍼", "강남언니", "UNNI"])
        keyword_raw = company_info.get(company, {}).get("keyword", [])
        if keyword_raw and keyword_raw[0]:
            keywords = [kw.strip() for kw in keyword_raw[0].split("/")]
        else:
            keywords = []

        filtered_news = []
        for news_item in news_list:
            total_news += 1
            title, description, link = news_item

            score = check_news_relevance(
                title, description, business_content,
                company_name=company,
                keywords=keywords,
                enable_keyword_prefilter=enable_keyword_prefilter,
                enable_keyword_in_prompt=enable_keyword_in_prompt
            )

            print(f"  [{company}] Score: {score}/10 - {title[:50]}...")

            if beta_mode:
                filtered_news.append((title, description, link, score))
                filtered_news_count += 1
                if score < threshold:
                    low_relevance_count += 1
                    print(
                        f"    → Low relevance (score {score} < threshold {threshold}) - Will be shown with warning"
                    )
            else:
                if score >= threshold:
                    filtered_news.append(news_item)
                    filtered_news_count += 1
                else:
                    print(f"    → Filtered out (score {score} < threshold {threshold})")

            time.sleep(1.0)  # 429 방지

        if filtered_news:
            filtered_news_data[company] = filtered_news

    print(f"\n=== Relevance Filtering Summary ===")
    print(f"Total news before filtering: {total_news}")
    if beta_mode:
        print(f"BETA MODE: All news included with relevance scores")
        print(
            f"News with high relevance (>= {threshold}): {filtered_news_count - low_relevance_count}"
        )
        print(f"News with low relevance (< {threshold}): {low_relevance_count}")
        print(f"  → These will be marked as '[관련성 낮음 - 필터링 예정]'")
    else:
        print(f"News after filtering: {filtered_news_count}")
        print(
            f"Filtered out: {total_news - filtered_news_count} ({(total_news - filtered_news_count) / total_news * 100:.1f}%)"
        )

    return filtered_news_data
