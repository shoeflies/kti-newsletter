from dotenv import load_dotenv
from google import genai
from google.genai import types
import numpy as np
import time
import os
import re

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

# 한 번의 Flash API 호출로 평가할 기사 수
BATCH_SIZE = 10

# 관련성 평가 기준 (filter_config.json의 relevance_criteria로 오버라이드 가능)
DEFAULT_CRITERIA = """- 10점: 이 회사가 기사의 핵심 주인공이고, 회사의 핵심 사업과 직접 관련된 뉴스
    - 7-9점: 이 회사가 기사의 주인공이며 다음 중 하나에 해당:
        * 사업 분야와 밀접하게 관련된 내용
        * IPO, 상장, 투자 유치, M&A, 인수합병 등 기업 재무/경영 이벤트
        * 임원 선임, 조직 변화, 파트너십 등 주요 기업 동향
    - 4-6점: 이 회사가 기사에 직접 등장하지만 주인공은 아님 (타사와 비교, 시장 동향 내 언급 등)
    - 1-3점: 이 회사가 기사에서 짧게 언급되거나 관련 업계 동향만 다루는 뉴스
    - 0점: 이 회사와 완전히 무관한 뉴스 (동음이의어, 업종 무관)"""


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


def get_embedding_batch(titles, model=EMBEDDING_MODEL):
    """여러 제목을 한 번의 API 호출로 임베딩"""
    max_retries = 4
    wait_times = [2, 5, 15, 30]
    for attempt in range(max_retries):
        try:
            result = client.models.embed_content(model=model, contents=titles)
            return [emb.values for emb in result.embeddings]
        except Exception as e:
            if _is_rate_limit_error(e) and attempt < max_retries - 1:
                print(f"Rate limit (embedding batch), retrying in {wait_times[attempt]}s...")
                time.sleep(wait_times[attempt])
            else:
                raise
    return []


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def filter_similar_titles(titles, threshold=0.60, return_cluster_info=False):
    if not titles:
        return [] if not return_cluster_info else {}

    try:
        embeddings = get_embedding_batch(titles)  # 1회 호출
        time.sleep(1.0)                            # 배치 후 1회만 대기
    except Exception as e:
        print(f"Embedding batch error: {e}")
        return [] if not return_cluster_info else {}

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


def _parse_batch_scores(answer, expected_count):
    """JSON 배열, 쉼표 구분, '1:8 2:3' 형식 응답 파싱. 실패 시 0으로 채움"""
    import json as _json
    result = [0] * expected_count

    # 0순위: JSON 배열 "[8, 3, 7]"
    try:
        parsed = _json.loads(answer)
        if isinstance(parsed, list):
            for i, s in enumerate(parsed[:expected_count]):
                if isinstance(s, (int, float)):
                    result[i] = int(s) if 0 <= int(s) <= 10 else 0
            return result
    except Exception:
        pass

    # 1순위: "1:8 2:3 3:7" 형식 (번호:점수)
    numbered = re.findall(r'(\d+)\s*:\s*(\d+)', answer)
    if numbered:
        for num_str, score_str in numbered:
            idx = int(num_str) - 1
            if 0 <= idx < expected_count:
                score = int(score_str)
                result[idx] = score if 0 <= score <= 10 else 0
        return result

    # 2순위: 쉼표/줄바꿈 구분 숫자 목록 ("8, 2, 1, 0")
    parts = re.split(r'[,\n]+', answer.strip())
    nums = []
    for p in parts:
        p = p.strip()
        m = re.search(r'\b(\d+)\b\s*$', p)
        if m:
            nums.append(int(m.group(1)))
    if len(nums) >= 1:
        for i, s in enumerate(nums[:expected_count]):
            result[i] = s if 0 <= s <= 10 else 0
        return result

    # 3순위: 숫자 하나 (기사 1개 배치 전용)
    if expected_count == 1:
        bare = re.search(r'^\s*(\d+)\s*$', answer)
        if bare:
            score = int(bare.group(1))
            result[0] = score if 0 <= score <= 10 else 0

    return result


def check_news_relevance_batch(news_items, business_content, company_name="",
                                keywords=None, enable_keyword_prefilter=True):
    """
    여러 기사를 BATCH_SIZE 단위로 나눠 일괄 평가.
    반환: [score, score, ...] (news_items와 동일 순서)
    """
    from utils.data_loader import load_filter_config

    if not news_items:
        return []

    if keywords is None:
        keywords = []

    criteria = load_filter_config().get("relevance_criteria") or DEFAULT_CRITERIA

    # 사전 키워드 필터링 (API 호출 없이 0점 처리)
    scores = [None] * len(news_items)
    items_to_score = []  # (원본_인덱스, title, description)
    if enable_keyword_prefilter and (company_name or keywords):
        all_keywords = ([company_name] + keywords) if company_name else keywords
        for i, news_item in enumerate(news_items):
            title, description = news_item[0], news_item[1]
            news_text = f"{title} {description}".lower()
            if any(kw.lower() in news_text for kw in all_keywords if kw):
                items_to_score.append((i, title, description))
            else:
                scores[i] = 0
    else:
        items_to_score = [(i, item[0], item[1]) for i, item in enumerate(news_items)]

    if not items_to_score:
        return [s if s is not None else 0 for s in scores]

    system_instruction = "당신은 뉴스 기사와 회사 사업의 관련성을 평가하는 전문가입니다. 숫자만 쉼표로 구분하여 답변하세요."

    for batch_start in range(0, len(items_to_score), BATCH_SIZE):
        batch = items_to_score[batch_start:batch_start + BATCH_SIZE]

        n = len(batch)
        articles_lines = ""
        for seq, (_, title, description) in enumerate(batch, 1):
            articles_lines += f"{seq}. 제목: {title} | 내용: {description[:120]}\n"

        prompt = f"""다음 뉴스 기사들이 아래 회사의 핵심 사업과 얼마나 관련 있는지 각각 0-10으로 평가해주세요.

회사명: {company_name}
핵심 사업: {business_content}

뉴스 기사 ({n}개):
{articles_lines}
평가 기준:
{criteria}

기사 {n}개의 점수를 순서대로 쉼표로 구분하여 숫자만 답해주세요. (예: 8, 3, 0, 7)"""

        max_retries = 4
        wait_times = [5, 15, 30, 60]
        batch_scores = None

        json_schema = {
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 10},
            "minItems": n,
            "maxItems": n,
        }
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=GENERATION_MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=json_schema,
                        temperature=0.1,
                    )
                )
                answer = response.text.strip() if response.text else ""
                batch_scores = _parse_batch_scores(answer, len(batch))
                break
            except Exception as e:
                if _is_rate_limit_error(e) and attempt < max_retries - 1:
                    print(f"Rate limit (batch scoring), retrying in {wait_times[attempt]}s...")
                    time.sleep(wait_times[attempt])
                else:
                    print(f"Batch scoring error: {e}, defaulting to 0")
                    batch_scores = [0] * len(batch)
                    break

        if batch_scores is None:
            batch_scores = [0] * len(batch)

        for (orig_idx, _, _), score in zip(batch, batch_scores):
            scores[orig_idx] = score

        time.sleep(1.0)  # 배치 후 1회만 대기

    return [s if s is not None else 0 for s in scores]


def filter_news_by_relevance(news_data, company_info, threshold=6, beta_mode=False,
                            enable_keyword_prefilter=True):
    """
    AI 기반 관련성 점수로 뉴스 필터링

    Args:
        news_data: 뉴스 데이터
        company_info: 회사 정보
        threshold: 관련성 임계값
        beta_mode: 베타 모드
        enable_keyword_prefilter: 사전 키워드 필터링 활성화
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

        total_news += len(news_list)
        scores = check_news_relevance_batch(
            news_list, business_content,
            company_name=company,
            keywords=keywords,
            enable_keyword_prefilter=enable_keyword_prefilter,
        )

        filtered_news = []
        for news_item, score in zip(news_list, scores):
            title, description, link = news_item
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
