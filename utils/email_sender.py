import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()


def send_email(content, recipients, subject=None):
    # SMTP 서버 설정
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    email_login = os.environ.get("EMAIL_LOGIN")
    email_password = os.environ.get("EMAIL_PASSWORD")
    email_password = email_password.replace("-", " ")

    print(f"Attempting to send email to: {recipients}")
    print(f"Using SMTP server: {smtp_server}:{smtp_port}")

    # 수신자가 비어있는 경우 처리
    if not recipients:
        print("Warning: No recipients specified")
        return

    try:
        # recipients가 리스트인 경우 문자열로 변환
        if isinstance(recipients, list):
            recipients_str = ", ".join(recipients)
        else:
            recipients_str = recipients

        # 메시지 생성
        msg = MIMEMultipart("alternative")
        if subject is None:
            subject = "KTI Portfolio Daily News"
        msg["Subject"] = subject
        msg["From"] = email_login
        msg["To"] = recipients_str

        # HTML 형식의 본문 추가
        html_part = MIMEText(content, "html")
        msg.attach(html_part)

        # SMTP 연결 및 전송
        send_to = recipients if isinstance(recipients, list) else [recipients]

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(email_login, email_password)
            server.sendmail(email_login, send_to, msg.as_string())
            print("Email sent successfully!")

    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        print(f"Recipients: {recipients}")
        raise


def get_email_styles():
    """이메일 CSS 스타일"""
    return """
        /* 기본 리셋 */
        body, table, td, p, a, li, blockquote {
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
            margin: 0;
            padding: 0;
        }

        body {
            width: 100% !important;
            height: 100% !important;
            margin: 0;
            padding: 0;
            background-color: #F7F7F7;
        }

        /* 폰트 */
        * {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
        }

        /* 래퍼 */
        .email-wrapper {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
            background-color: #FFFFFF;
        }

        /* 헤더 */
        .email-header {
            background-color: #090B43;
            color: #FFFFFF;
            padding: 20px;
            text-align: center;
        }

        .email-header h1 {
            font-size: 30px;
            font-weight: 700;
            margin: 0;
            line-height: 1.6;
        }

        .email-header p {
            font-size: 12px;
            font-weight: 400;
            margin: 4px 0 0 0;
            opacity: 0.9;
        }

        /* 공지 박스 */
        .notice-box {
            background-color: #F7F7F7;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 13px;
            margin: 16px;
        }

        .notice-box strong {
            color: #090B43;
            font-size: 15px;
            font-weight: 600;
        }

        .notice-box p {
            color: #1E1E1E;
            font-size: 14px;
            line-height: 1.4;
            margin: 5px 0 0 0;
        }

        .notice-highlight {
            color: #D93931;
            font-weight: 600;
        }

        .notice-link {
            color: #D93931;
            text-decoration: none;
        }

        .notice-link:hover {
            text-decoration: underline;
        }

        /* 회사 섹션 */
        .company-section {
            background-color: #F7F7F7;
            margin: 10px 0;
            padding: 16px;
            border-radius: 8px;
        }

        .company-header {
            color: #090B43;
            font-size: 20px;
            font-weight: 600;
            margin: 0 0 8px 0;
        }

        .company-keywords {
            color: #6B7280;
            font-size: 14px;
            margin: 0 0 10px 0;
        }

        .company-keywords strong {
            color: #1E1E1E;
            font-weight: 500;
        }

        /* 뉴스 카드 */
        .news-card {
            background-color: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 13px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            text-decoration: none;
            display: block;
            color: inherit;
            transition: all 0.2s;
        }

        .news-card:hover {
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-color: #D93931;
        }

        .news-card:last-child {
            margin-bottom: 0;
        }

        .news-header {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }

        .relevance-badge {
            display: inline-block;
            padding: 3px 7px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 5px;
        }

        .relevance-high {
            background-color: #6B7280;
            color: #FFFFFF;
        }

        .relevance-low {
            background-color: #D1D5DB;
            color: #4B5563;
        }

        .news-title {
            color: #1E1E1E;
            font-size: 16px;
            font-weight: 600;
            line-height: 1.2;
            margin: 0;
        }

        .news-description {
            color: #6B7280;
            font-size: 15px;
            line-height: 1.4;
            margin: 8px 0 0 0;
        }


        /* 푸터 */
        .email-footer {
            background-color: #F7F7F7;
            color: #9CA3AF;
            padding: 16px;
            text-align: center;
            font-size: 13px;
            line-height: 1.3;
        }

        .email-footer p {
            margin: 3px 0;
        }

        /* 모바일 최적화 */
        @media only screen and (max-width: 1200px) {
            .email-wrapper {
                width: 100% !important;
            }

            .email-header,
            .notice-box,
            .company-section,
            .email-footer {
                padding: 13px !important;
            }

            .news-card {
                padding: 10px !important;
            }

            .email-header h1 {
                font-size: 20px !important;
            }

            .company-header {
                font-size: 18px !important;
            }
        }

        /* 다크모드 */
        @media (prefers-color-scheme: dark) {
            body {
                background-color: #1E1E1E !important;
            }

            .email-wrapper {
                background-color: #2D2D2D !important;
            }

            .email-header {
                background-color: #1C419A !important;
            }

            .notice-box {
                background-color: #3A3A3A !important;
                border-color: #4A4A4A !important;
            }

            .notice-box p {
                color: #E5E7EB !important;
            }

            .company-section {
                background-color: #3A3A3A !important;
            }

            .news-card {
                background-color: #2D2D2D !important;
                border-color: #4A4A4A !important;
            }

            .news-title {
                color: #FFFFFF !important;
            }

            .news-description {
                color: #9CA3AF !important;
            }

            .company-keywords {
                color: #9CA3AF !important;
            }

            .company-keywords strong {
                color: #E5E7EB !important;
            }
        }
    """


def get_header_html(user_name):
    """이메일 헤더"""
    return f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td class="email-header" style="background-color: #090B43;" data-ogsc="#1C419A">
                    <img src="https://images.squarespace-cdn.com/content/v1/62149eb06e1020220949de66/58ee7847-c613-4b0e-896f-ee35190825aa/kti_logo.png"
                         alt="KTI Logo"
                         style="width: 120px; height: auto; margin-bottom: 5px; display: block; margin-left: auto; margin-right: auto;">
                    <h1>Portfolio Daily News</h1>
                    <p>Hello there, mighty fine morning!</p>
                </td>
            </tr>
        </table>
    """


def get_update_notice_html():
    """업데이트 공지 박스"""
    return """
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td style="padding: 0 16px;">
                    <div class="notice-box">
                        <p style="margin: 0;"><strong>📢 참고</strong></p>
                        <p>
                            • 키워드 추가/변경/삭제를 원하실 경우 담당자(최우석)에게 문의 부탁드립니다.<br>
                            • 회사별 키워드는 <a href="https://drive.google.com/drive/u/0/folders/1Y_SD1yqjnijE6pY52c1xRp2yxBePHuzq" class="notice-link">KTI 공용드라이브의 구글시트</a>에서 관리 중입니다.
                        </p>
                    </div>
                </td>
            </tr>
        </table>
    """


def get_news_card_html(news_item, beta_test_mode, relevance_threshold):
    """개별 뉴스 카드"""
    if len(news_item) == 4:
        title, description, url, score = news_item

        if score < relevance_threshold:
            badge = f'<span class="relevance-badge relevance-low">관련성 낮음 ({score}/10)</span>'
        else:
            badge = f'<span class="relevance-badge relevance-high">관련성 {score}/10</span>'

        return f"""
            <a href="{url}" target="_blank" class="news-card">
                <div class="news-header">
                    {badge}
                </div>
                <h3 class="news-title">{title}</h3>
                <p class="news-description">{description}</p>
            </a>
        """
    else:
        title, description, url = news_item
        return f"""
            <a href="{url}" target="_blank" class="news-card">
                <h3 class="news-title">{title}</h3>
                <p class="news-description">{description}</p>
            </a>
        """


def get_section_header_html(title):
    """섹션 헤더"""
    return f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td style="padding: 20px 16px 10px 16px;">
                    <h2 style="color: #090B43; font-size: 22px; font-weight: 700; margin: 0; border-bottom: 2px solid #D93931; padding-bottom: 8px;">
                        {title}
                    </h2>
                </td>
            </tr>
        </table>
    """


def _render_company_news(company, news_detail, beta_test_mode, relevance_threshold):
    """개별 회사의 뉴스 렌더링 (헬퍼 함수)"""
    keywords = " / ".join(news_detail["keyword"])

    html = f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td style="padding: 0 16px;">
                    <div class="company-section">
                        <h2 class="company-header">{company}</h2>
                        <p class="company-keywords"><strong>검색 키워드:</strong> {keywords}</p>
    """

    for news in news_detail["news_list"]:
        html += get_news_card_html(news, beta_test_mode, relevance_threshold)

    html += """
                    </div>
                </td>
            </tr>
        </table>
    """

    return html


def get_companies_html(news_data, beta_test_mode, relevance_threshold, user_companies=None):
    """회사 섹션 (담당/비담당 구분)"""
    html = ""

    # 담당 포트폴리오 섹션
    if user_companies:
        html += get_section_header_html("📌 담당 포트폴리오")

        for company in user_companies:
            if company in news_data and company != "KT":  # KT 제외
                html += _render_company_news(company, news_data[company], beta_test_mode, relevance_threshold)

        # 기타 포트폴리오 섹션
        other_companies = [c for c in news_data.keys() if c not in user_companies and c != "KT"]  # KT 제외
        if other_companies:
            html += get_section_header_html("📋 기타 포트폴리오")

            for company in other_companies:
                html += _render_company_news(company, news_data[company], beta_test_mode, relevance_threshold)

        # KT 관련 기사 섹션 (별도)
        if "KT" in news_data:
            html += get_section_header_html("📡 KT 관련 기사")
            html += _render_company_news("KT", news_data["KT"], beta_test_mode, relevance_threshold)
    else:
        # user_companies 없으면 기존 방식대로 (KT만 분리)
        for company, news_detail in news_data.items():
            if company != "KT":
                html += _render_company_news(company, news_detail, beta_test_mode, relevance_threshold)

        # KT는 마지막에
        if "KT" in news_data:
            html += get_section_header_html("📡 KT 관련 기사")
            html += _render_company_news("KT", news_data["KT"], beta_test_mode, relevance_threshold)

    return html


def get_footer_html():
    """이메일 푸터"""
    return """
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td class="email-footer">
                    <p>본 메일은 자동으로 발송되었습니다.</p>
                    <p style="margin-top: 8px;">© 2026 KT Investment Co., Ltd. All rights reserved.</p>
                </td>
            </tr>
        </table>
    """


def format_email_content(news_data, user_name, user_companies=None):
    """이메일 콘텐츠 포맷팅"""
    from utils.data_loader import load_filter_config

    filter_cfg = load_filter_config()
    beta_test_mode = filter_cfg["beta_test_mode"]
    relevance_threshold = filter_cfg["relevance_threshold"]

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <link rel="preconnect" href="https://cdn.jsdelivr.net">
    <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" rel="stylesheet">
    <style>{get_email_styles()}</style>
</head>
<body>
    <table role="presentation" class="email-wrapper" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
            <td>
                {get_header_html(user_name)}
                {get_update_notice_html()}
                {get_companies_html(news_data, beta_test_mode, relevance_threshold, user_companies)}
                {get_footer_html()}
            </td>
        </tr>
    </table>
</body>
</html>"""

    return html
