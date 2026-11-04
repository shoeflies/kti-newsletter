"""
국내 스타트업 투자 유치 딜 수집
- 네이버 검색 → AI 분류(투자 유치 기사만) → 회사명으로 묶기 → 대표 기사 본문에서 딜 정보 추출
"""

import asyncio
import json
import re
import time
from urllib.parse import quote, urlparse
from bs4 import BeautifulSoup
from google.genai import types
from playwright.async_api import async_playwright

from utils.fetch_news import fetch_news_for_company
from utils.filter_similar_news import client, GENERATION_MODEL_NAME, BATCH_SIZE, _is_rate_limit_error

# 네이버가 따옴표 정확 일치를 지키지 않아 한국시리즈 암표, 지자체 기업유치 기사가 섞인다 → 분류 단계에서 걸러냄
# "브릿지 투자", "투자를 유치했다"는 실측에서 결과가 전부 노이즈라 제외
FUNDING_KEYWORDS = ["시리즈A 투자", "시리즈B 투자", "시리즈C 투자", "프리A 투자", "시드 투자", "투자 유치"]

# 본문이 이보다 짧으면 추출 실패로 보고 스니펫만 사용
MIN_BODY_LENGTH = 200
MAX_BODY_LENGTH = 3000
# 대표 기사 본문 추출 시도 횟수 (묶음 내 기사 순서대로)
MAX_BODY_ATTEMPTS = 3

# 투자금액 정렬용 단위
AMOUNT_UNITS = {"조": 10**12, "억": 10**8, "만": 10**4}

# 공식 홈페이지가 될 수 없는 포털/SNS/기업정보/채용 사이트는 후보에서 제외 (그 외 오탐은 AI 검증에서 거름)
HOMEPAGE_SKIP_DOMAINS = (
    "naver.", "daum.", "kakao.", "google.", "youtube.", "facebook.", "instagram.", "linkedin.",
    "tistory.", "blog.", "wikipedia.", "namu.wiki", "thevc.kr", "innoforest.", "rocketpunch.",
    "wanted.co.kr", "jobkorea.", "saramin.", "bizno.net", "nicebizinfo.", "marketbz.",
)


def _generate_json(prompt, schema):
    """JSON schema 강제 출력으로 Gemini 호출. 실패 시 None"""
    max_retries = 4
    wait_times = [5, 15, 30, 60]
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GENERATION_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.1,
                )
            )
            answer = response.text
            time.sleep(1.0)  # 호출 후 1회만 대기
            return json.loads(answer) if answer else None
        except Exception as e:
            if _is_rate_limit_error(e) and attempt < max_retries - 1:
                print(f"Rate limit (funding), retrying in {wait_times[attempt]}s...")
                time.sleep(wait_times[attempt])
            else:
                print(f"Funding generation error: {e}")
                return None
    return None


def classify_funding_articles(articles):
    """
    기사마다 국내 비상장사 투자 유치 기사인지 BATCH_SIZE 단위로 판정.
    반환: [회사명 또는 None, ...] (articles와 동일 순서)
    """
    companies = [None] * len(articles)

    for batch_start in range(0, len(articles), BATCH_SIZE):
        batch = articles[batch_start:batch_start + BATCH_SIZE]
        n = len(batch)

        articles_lines = ""
        for seq, (title, description, _) in enumerate(batch, 1):
            articles_lines += f"{seq}. 제목: {title} | 내용: {description[:400]}\n"

        prompt = f"""다음 뉴스 기사 각각이 '국내 비상장 기업의 투자 유치 소식'인지 판정하고, 맞다면 투자를 받은 회사명을 적어주세요.

is_funding을 true로 하는 조건 (모두 만족):
1. 한국 기업이 시드, 프리A, 시리즈A/B/C 이상, 브릿지, 프리IPO, 전략적 투자 등 지분 투자 라운드를 유치(완료)했다는 소식
2. 그 투자 유치가 기사의 주제 (제목을 우선으로 판단하세요. 내용에 다음 라운드 계획이 함께 언급되어도 이번 투자 유치가 주제면 true)

다음은 false입니다:
- 지자체/정부의 기업 유치, 공장/설비 투자, 상장사 유상증자
- 펀드 결성, SPAC 합병, M&A/인수
- 투자 유치를 추진 중이거나 계획만 있고 아직 유치하지 않은 경우
- 과거 투자 이력만 언급하는 기사 (예: "2020년 시리즈A 55억원을 유치한 바 있다")
- 여러 회사의 투자 동향을 묶은 통계/분석 기사
- 해외 기업의 투자 유치
- 투자와 무관한 기사 (프로야구 한국시리즈, 제품 시리즈 등)

company: is_funding이 true면 투자를 받은 회사명을 제목에 나온 표기 그대로 적으세요 (괄호, 영문 병기, (주) 제외). false면 빈 문자열.

뉴스 기사 ({n}개):
{articles_lines}"""

        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "is_funding": {"type": "boolean"},
                    "company": {"type": "string"},
                },
                "required": ["is_funding", "company"],
            },
            "minItems": n,
            "maxItems": n,
        }
        result = _generate_json(prompt, schema)
        if not isinstance(result, list):
            continue

        for i, item in enumerate(result[:n]):
            if isinstance(item, dict) and item.get("is_funding") and item.get("company", "").strip():
                companies[batch_start + i] = item["company"].strip()

    return companies


def _amount_to_won(amount):
    """'152억5000만원' → 15250000000. 미공개/해석 불가면 0 (정렬 시 맨 뒤)"""
    amount = re.sub(r"\(.*?\)", "", amount)  # "100억원(누적 300억원)" 같은 괄호 부연은 제외
    return sum(
        float(num.replace(",", "")) * AMOUNT_UNITS[unit]
        for num, unit in re.findall(r"(\d[\d,.]*)\s*(조|억|만)", amount)
    )


def _normalize_company(name):
    """묶기용 키: 괄호 내용, ㈜/주식회사, 공백 제거 후 소문자 (예: "무빈(MOVIN)" → "무빈")"""
    name = re.sub(r"\(.*?\)|㈜|주식회사", "", name)
    return re.sub(r"\s+", "", name).lower()


async def _fetch_body(browser, url):
    """기사 본문 수집. 실패 시 빈 문자열"""
    page = await browser.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        soup = BeautifulSoup(await page.content(), "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        # 언론사마다 구조가 달라 <p> 문단만 모은다 (짧은 메뉴/캡션 제외)
        paragraphs = [para.get_text(" ", strip=True) for para in soup.find_all("p")]
        body = " ".join(text for text in paragraphs if len(text) > 30)
        return body[:MAX_BODY_LENGTH]
    except Exception as e:
        print(f"  Body fetch failed: {url} ({e})")
        return ""
    finally:
        await page.close()


async def fetch_representative_bodies(groups):
    """
    묶음마다 본문 추출에 성공한 첫 기사를 대표 기사로 선택.
    본문이 <p>가 아닌 언론사(한국경제 등)는 다른 기사 목록만 긁히므로, 본문에 회사명이 없으면 실패로 보고 다음 기사 시도.
    반환: [(대표 기사, 본문), ...] (모두 실패하면 (첫 기사, ""))
    """
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for company, group_articles in groups:
            key = _normalize_company(company)
            chosen = (group_articles[0], "")
            for article in group_articles[:MAX_BODY_ATTEMPTS]:
                body = await _fetch_body(browser, article[2])
                if len(body) >= MIN_BODY_LENGTH and key in re.sub(r"\s+", "", body).lower():
                    chosen = (article, body)
                    break
            results.append(chosen)
        await browser.close()
    return results


def extract_funding_details(company, text):
    """
    이번 라운드 딜 정보 추출.
    반환: {"business", "series", "amount", "valuation", "investors": [...]} 또는 None
    """
    prompt = f"""다음은 '{company}'의 투자 유치에 관한 기사입니다. 회사의 사업 개요와 이번 투자 라운드의 정보를 추출해주세요.

규칙:
- 기사에 명시된 값만 적고 추정하지 마세요. 기사에 없으면 "미공개"로 적으세요.
- business: 이 회사가 어떤 사업을 하는지 한 문장 (40자 내외, 예: 라이다 기반 3차원 모션 데이터 AI 기술 개발)
- series: 이번 라운드 단계 (예: 시드, 프리A, 시리즈A, 시리즈B, 브릿지, 프리IPO, 전략적 투자)
- amount: 이번 라운드 투자금액 (예: 100억원). 누적 투자금과 혼동하지 마세요.
- valuation: 이번 라운드에서 인정받은 기업가치 (예: 1000억원)
- investors: 이번 라운드에 참여한 투자사 전부 (신규 투자자와 후속 투자한 기존 투자자 포함). 기사에 리드/주도 투자사로 명시된 곳만 이름 뒤에 "(리드)"를 붙이세요. 과거 라운드에만 참여한 투자사는 제외하세요. 기사에 없으면 빈 배열.

기사:
{text}"""

    schema = {
        "type": "object",
        "properties": {
            "business": {"type": "string"},
            "series": {"type": "string"},
            "amount": {"type": "string"},
            "valuation": {"type": "string"},
            "investors": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["business", "series", "amount", "valuation", "investors"],
    }
    result = _generate_json(prompt, schema)
    return result if isinstance(result, dict) else None


async def _search_homepage_candidate(browser, company):
    """네이버 웹문서 검색 결과 중 첫 후보 사이트의 루트 주소. 없으면 빈 문자열"""
    page = await browser.new_page()
    try:
        url = f"https://search.naver.com/search.naver?where=web&query={quote(company + ' 공식 홈페이지')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_selector("div.fds-web-doc-root", timeout=10000)
        except Exception:
            pass  # 검색 결과 없음
        soup = BeautifulSoup(await page.content(), "html.parser")
        # 웹문서 결과 1건 = fds-web-doc-root 1개, 첫 링크가 해당 사이트 주소
        for doc in soup.select("div.fds-web-doc-root"):
            link = doc.select_one("a[href^='http']")
            if not link:
                continue
            parsed = urlparse(link["href"])
            if any(domain in parsed.netloc for domain in HOMEPAGE_SKIP_DOMAINS):
                continue
            return f"{parsed.scheme}://{parsed.netloc}/"
        return ""
    except Exception as e:
        print(f"  Homepage search failed: {company} ({e})")
        return ""
    finally:
        await page.close()


async def _fetch_page_summary(browser, url):
    """홈페이지 후보의 제목/설명/본문 앞부분. 실패 시 빈 문자열"""
    page = await browser.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1500)  # JS로 그리는 사이트 렌더링 대기
        soup = BeautifulSoup(await page.content(), "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        title = soup.title.get_text(strip=True) if soup.title else ""
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        description = meta.get("content", "") if meta else ""
        text = soup.get_text(" ", strip=True)
        return f"제목: {title} | 설명: {description} | 내용: {text[:300]}"
    except Exception as e:
        print(f"  Homepage fetch failed: {url} ({e})")
        return ""
    finally:
        await page.close()


async def find_homepage_candidates(deals):
    """
    딜마다 홈페이지 후보 주소와 페이지 요약 수집.
    반환: [(후보 주소, 페이지 요약), ...] (후보가 없으면 ("", ""))
    """
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for deal in deals:
            url = await _search_homepage_candidate(browser, deal["company"])
            summary = await _fetch_page_summary(browser, url) if url else ""
            results.append((url, summary))
            await asyncio.sleep(1.5)  # 네이버 연속 검색 간격 (fetch_news_for_company와 동일)
        await browser.close()
    return results


def verify_homepages(deals, candidates):
    """
    후보 페이지가 실제 공식 홈페이지인지 BATCH_SIZE 단위로 AI 판정.
    영문 전용 사이트(MOVIN, Ettifos 등)는 한글 사명 문자열 매칭으로는 확인되지 않아 회사명 표기와 사업 내용을 함께 대조한다.
    반환: [True/False, ...] (deals와 동일 순서)
    """
    verified = [False] * len(deals)
    targets = [(i, deal, summary) for i, (deal, (_, summary)) in enumerate(zip(deals, candidates)) if summary]

    for batch_start in range(0, len(targets), BATCH_SIZE):
        batch = targets[batch_start:batch_start + BATCH_SIZE]
        n = len(batch)

        lines = ""
        for seq, (_, deal, summary) in enumerate(batch, 1):
            lines += f"{seq}. 회사: {deal['company']} ({deal['business']}) | 웹페이지 {summary}\n"

        prompt = f"""각 웹페이지가 해당 회사의 공식 홈페이지인지 판정해주세요.

- 웹페이지에 회사명(한글, 영문 표기 또는 음차)이 드러나고 사업 내용이 일치해야 true입니다.
- 뉴스, 블로그, 기업정보/채용 사이트, 이름만 같은 다른 회사나 기관이면 false입니다.

항목 ({n}개):
{lines}"""

        schema = {"type": "array", "items": {"type": "boolean"}, "minItems": n, "maxItems": n}
        result = _generate_json(prompt, schema)
        if not isinstance(result, list):
            continue

        for (i, _, _), ok in zip(batch, result):
            verified[i] = ok is True

    return verified


async def collect_funding_deals():
    """
    국내 스타트업 투자 유치 딜 수집.
    반환: [{"company", "business", "series", "amount", "valuation", "investors", "title", "url", "homepage"}, ...] (투자금액 큰 순)
    """
    articles = await fetch_news_for_company(FUNDING_KEYWORDS)

    # 같은 기사가 여러 키워드에 걸리므로 링크 기준 중복 제거.
    # 네이버는 검색어마다 다른 문단을 스니펫으로 보여주므로 합친다 (첫 스니펫만 쓰면 "다음 라운드 추진" 문단만 남아 오분류된 사례 있음)
    merged = {}  # {링크: [제목, [스니펫, ...]]}
    for title, description, link in articles:
        if link not in merged:
            merged[link] = [title, []]
        if description and description not in merged[link][1]:
            merged[link][1].append(description)
    unique_articles = [(title, " ".join(descriptions), link) for link, (title, descriptions) in merged.items()]
    print(f"  Fetched {len(articles)} articles ({len(unique_articles)} unique)")

    companies = classify_funding_articles(unique_articles)

    # 서로 다른 회사의 펀딩 기사는 제목 형태가 같아 임베딩 중복 제거로는 섞인다 → 회사명으로 묶음
    groups = {}  # {정규화 회사명: (표시 회사명, [기사, ...])}
    for article, company in zip(unique_articles, companies):
        if not company:
            continue
        key = _normalize_company(company)
        # 투자 동향 기사 속 한 줄 언급(트리오어 사례)은 프롬프트로 걸러지지 않아, 제목에 사명이 있는 기사만 남긴다
        if key not in re.sub(r"\s+", "", article[0]).lower():
            continue
        if key not in groups:
            groups[key] = (company, [])
        groups[key][1].append(article)

    # 기사 수 많은 순 (아래 금액 정렬은 안정 정렬이라 금액이 같거나 미공개인 딜끼리는 이 순서가 유지됨)
    sorted_groups = sorted(groups.values(), key=lambda g: len(g[1]), reverse=True)
    representatives = await fetch_representative_bodies(sorted_groups)

    deals = []
    for (company, group_articles), (representative, body) in zip(sorted_groups, representatives):
        # 본문 추출에 실패해도 스니펫으로 추출할 수 있도록 묶음 내 스니펫을 함께 넘김
        snippets = "\n".join(f"- {title}: {description}" for title, description, _ in group_articles)
        text = f"{body}\n\n{snippets}" if body else snippets

        details = extract_funding_details(company, text)
        if not details:
            continue

        title, _, url = representative
        deals.append({"company": company, **details, "title": title, "url": url})

    # 투자금액 큰 순, 미공개는 맨 뒤
    deals.sort(key=lambda d: _amount_to_won(d["amount"]), reverse=True)

    # 홈페이지: 검색 첫 후보를 AI로 검증해 확인된 경우만 표시 ("팀이지"처럼 일반 단어인 사명은 엉뚱한 사이트가 잡힘)
    candidates = await find_homepage_candidates(deals)
    verified = verify_homepages(deals, candidates)
    for deal, (homepage, _), ok in zip(deals, candidates, verified):
        deal["homepage"] = homepage if ok else ""
        investors = ", ".join(deal["investors"]) or "미공개"
        print(f"  [Funding] {deal['company']} | {deal['series']} | {deal['amount']} | {deal['valuation']} | {investors} | {deal['homepage'] or '홈페이지 미확인'}")

    return deals
