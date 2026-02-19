import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()


def send_email(content, recipients):
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
        msg["Subject"] = "KTI Portfolio Daily News"
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


def format_email_content(news_data, user_name):
    # 베타 테스트 모드 및 임계값: filter_config.json
    from utils.data_loader import load_filter_config

    filter_cfg = load_filter_config()
    beta_test_mode = filter_cfg["beta_test_mode"]
    relevance_threshold = filter_cfg["relevance_threshold"]

    email_body = "<h1> [Gemini Test 발송] KTI Portfolio Daily News </h1>"
    email_body += f"<p> 안녕하세요 {user_name}님. KTI 투자포트폴리오사의 뉴스리스트 메일링입니다</p><br><br>"

    email_body += """
    <div style="font-family: Arial, sans-serif; font-size: 14px; color: #555;">
        <p style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; border: 1px solid #ddd;">
            <strong>업데이트 소식:</strong><br>
            수신자별로 담당 포트폴리오사의 뉴스가 상단에 배치됩니다. <br>
            각 회사별 검색 키워드도 함께 제공됩니다. <br>
            <span style="color: #0066cc; font-weight: bold;">🆕 AI 필터로 관련 없는 뉴스를 필터링하는 기능을 테스트 중입니다!</span><br>
            ** 키워드 추가/변경/삭제를 원하실 경우 언제든 말씀해주세요!<br>
            ** 회사별 키워드는 <a href="https://drive.google.com/drive/u/0/folders/1Y_SD1yqjnijE6pY52c1xRp2yxBePHuzq" style="color: #1a73e8; text-decoration: none;">KTI 공용드라이브의 구글시트</a>에서 관리 중입니다. 변경하실 경우 담당자에게 변경사실을 알려주세요
        </p>
    </div>
    <br>
    """

    for company, news_detail in news_data.items():
        keywords = " / ".join(news_detail["keyword"])
        email_body += f"<h2 style='background-color: #FFD700;'>{company}</h2>"
        email_body += f"<p><strong>검색 키워드:</strong> {keywords}</p>"
        email_body += "<hr>"  # 회사 구분선

        for news in news_detail["news_list"]:
            if len(news) == 4:
                title, description, url, score = news
                if score < relevance_threshold:
                    title_with_tag = f'<span style="background-color: #ffcccc; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: bold;">[관련성 낮음 - 필터링 예정 (점수: {score}/10)]</span> {title}'
                    email_body += f"<h3>{title_with_tag}</h3>"
                else:
                    title_with_score = f'<span style="background-color: #d4edda; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: bold;">[관련성: {score}/10]</span> {title}'
                    email_body += f"<h3>{title_with_score}</h3>"
            else:
                title, description, url = news
                email_body += f"<h3>{title}</h3>"

            email_body += f"<p>{description}</p>"
            email_body += f'<a href="{url}">Link</a><br>'
            email_body += "<hr>"

        email_body += "<br>"

    return email_body
