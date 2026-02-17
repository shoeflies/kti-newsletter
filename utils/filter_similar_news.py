from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np
import time
import os

# Load environment variables
load_dotenv()

# Configure Gemini API
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    raise EnvironmentError("GEMINI_API_KEY environment variable is not set")
genai.configure(api_key=gemini_api_key)

# Embedding model (Gemini). Do not use text-embedding-004 (deprecated, returns 404).
EMBEDDING_MODEL = "gemini-embedding-001"
# Text generation model for relevance scoring (gemini-1.5-flash deprecated)
# NOTE: gemini-3-flash-preview is currently in preview. Monitor for stability.
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
            result = genai.embed_content(model=model, content=text)
            return result["embedding"]
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


def filter_similar_titles(titles, threshold=0.60):
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
        return []

    unique_titles = []
    for i, embedding in enumerate(embeddings):
        is_unique = True
        for unique_embedding in unique_titles:
            if cosine_similarity(embedding, unique_embedding[1]) > threshold:
                is_unique = False
                break
        if is_unique:
            unique_titles.append((titles[i], embedding, i))
    return [idx for _, _, idx in unique_titles]


def check_news_relevance(news_title, news_description, business_content):
    """
    뉴스 기사가 회사 사업 내용과 얼마나 관련이 있는지 0-10 점수로 평가
    """
    max_retries = 4
    wait_times = [5, 15, 30, 60]  # 429 시 대기 (초)

    system_instruction = "당신은 뉴스 기사와 회사 사업의 관련성을 평가하는 전문가입니다. 0-10 사이의 숫자로만 답변하세요."
    prompt = f"""다음 뉴스 기사가 회사의 사업 내용과 얼마나 관련이 있는지 0-10 점수로 평가해주세요.

    뉴스 제목: {news_title}
    뉴스 내용: {news_description}

    회사 사업 내용: {business_content}

    평가 기준:
    - 10점: 회사의 핵심 사업/제품/서비스에 직접적으로 관련된 뉴스
    - 7-9점: 회사의 사업 분야와 밀접하게 관련된 뉴스
    - 4-6점: 회사가 속한 산업이나 시장과 간접적으로 관련된 뉴스
    - 1-3점: 회사명은 언급되지만 사업과 거의 관련 없는 뉴스
    - 0점: 완전히 관련 없는 뉴스 (동음이의어, 오타 등)

    0-10 사이의 숫자만 답변해주세요."""

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(
                GENERATION_MODEL_NAME,
                system_instruction=system_instruction,
            )
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=10,
                    temperature=0.3,
                ),
            )
            # response.text can raise if no valid Part (e.g. finish_reason=SAFETY/blocked)
            answer = ""
            if response.candidates:
                c = response.candidates[0]
                if c.content and c.content.parts:
                    answer = (c.content.parts[0].text or "").strip()

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


def filter_news_by_relevance(news_data, company_info, threshold=6, beta_mode=False):
    """
    AI 기반 관련성 점수로 뉴스 필터링
    """
    filtered_news_data = {}
    total_news = 0
    filtered_news_count = 0
    low_relevance_count = 0

    for company, news_list in news_data.items():
        business_content = company_info.get(company, {}).get("comment", "")

        if not business_content:
            print(
                f"Warning: No business content for {company}, skipping relevance check"
            )
            filtered_news_data[company] = news_list
            continue

        filtered_news = []
        for news_item in news_list:
            total_news += 1
            title, description, link = news_item

            score = check_news_relevance(title, description, business_content)

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
