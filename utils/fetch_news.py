import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

KST = timezone(timedelta(hours=9))


def get_search_interval():
    now = datetime.now(KST)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 월요일(weekday=0)이면 금요일 자정(3일 전)부터, 그 외엔 전날 자정부터
    if now.weekday() == 0:
        start = today_midnight - timedelta(days=3)
    else:
        start = today_midnight - timedelta(days=1)

    return now.strftime("%Y.%m.%d.%H.%M"), start.strftime("%Y.%m.%d.%H.%M")


def make_target_url(search_keyword):
    date_end, date_start = get_search_interval()
    target_url = (
        f"https://search.naver.com/search.naver?where=news&query=%22{search_keyword}%22"
        f"&sm=tab_opt&sort=0&photo=0&field=0&pd=4&ds={date_start}&de={date_end}"
        f"&docid=&related=0&mynews=0&office_type=0&office_section_code=0"
        f"&news_office_checked=&nso=so%3Ar%2Cp%3A1d&is_sug_officeid=0&office_category=0"
        f"&service_area=0"
    )
    return target_url


async def fetch_html(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_selector("div.sds-comps-base-layout", timeout=10000)
        except Exception:
            pass  # 검색 결과 없음
        html = await page.content()
        await browser.close()
        return html


async def fetch_news(target_url):
    html = await fetch_html(target_url)
    soup = BeautifulSoup(html, "html.parser")

    articles = []
    for card in soup.select("div.sds-comps-base-layout"):
        title_span = card.select_one("span.sds-comps-text-type-headline1")
        if not title_span:
            continue

        title = title_span.get_text(" ", strip=True)
        link = title_span.find_parent("a")["href"]

        content_span = card.select_one("span.sds-comps-text-ellipsis-3")
        content = content_span.get_text(" ", strip=True) if content_span else ""
        articles.append((title, content, link))
    return articles


async def fetch_news_for_company(keywords: list) -> list:
    """하나의 브라우저로 회사의 모든 키워드를 순차 검색 (브라우저 재사용)"""
    articles = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for keyword in keywords:
            url = make_target_url(keyword.strip())
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                try:
                    await page.wait_for_selector("div.sds-comps-base-layout", timeout=10000)
                except Exception:
                    pass
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                for card in soup.select("div.sds-comps-base-layout"):
                    title_span = card.select_one("span.sds-comps-text-type-headline1")
                    if not title_span:
                        continue
                    title = title_span.get_text(" ", strip=True)
                    link = title_span.find_parent("a")["href"]
                    content_span = card.select_one("span.sds-comps-text-ellipsis-3")
                    content = content_span.get_text(" ", strip=True) if content_span else ""
                    articles.append((title, content, link))
            finally:
                await page.close()
            await asyncio.sleep(1.5)
        await browser.close()
    return articles
