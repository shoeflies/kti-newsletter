import json
import csv
import os

# 프로젝트 루트 (utils/ 기준 상위 디렉터리)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILTER_CONFIG_PATH = os.path.join(_REPO_ROOT, "filter_config.json")


def load_json(file_path):
    """JSON 파일 로드. 상대 경로면 프로젝트 루트 기준."""
    if not os.path.isabs(file_path):
        file_path = os.path.join(_REPO_ROOT, file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def load_company_info_from_csv(csv_path="portfolio_news_data.csv"):
    """
    프로젝트 최상위의 CSV에서 회사 정보를 읽어 company_info와 동일한 구조의 dict를 반환합니다.
    반환 형태: { 회사명: { "keyword": [...], "comment": str, "manager": [...] } }
    csv_path는 기본값이면 프로젝트 루트의 portfolio_news_data.csv를 사용합니다.
    """
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(_REPO_ROOT, csv_path)
    company_info = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("기업명", "").strip()
            if not name:
                continue
            comment = row.get("회사소개", "").strip()
            manager_str = row.get("담당자", "").strip()
            keyword_str = row.get("키워드", "").strip()
            managers = [m.strip() for m in manager_str.split("/") if m.strip()]
            keyword_for_list = keyword_str if keyword_str else name
            company_info[name] = {
                "keyword": [keyword_for_list],
                "comment": [comment],  # 리스트로 저장 (main.py/test.py KT 추가 방식과 일관성)
                "manager": managers,
            }
    return company_info


def get_special_companies():
    """CSV에 없는 특별 모니터링 회사 정보 반환 (KT, LP 출자 동향 등)"""
    return {
        "KT": {
            "comment": ["국내 최대 통신사이자 디지털 플랫폼 기업으로 ICT, 금융사업, 위성방송서비스사업, 기타사업 등을 영위"],
            "keyword": ["KT/케이티/KT클라우드/케이티클라우드"],
            "manager": []
        },
        "LP 출자 동향": {
            "comment": ["국내 주요 기관 LP(모태펀드·성장금융·연기금·공제회 등)의 비상장 벤처펀드 출자 사업 및 공고 동향"],
            "keyword": ["모태펀드/벤처출자/성장금융/벤처LP/은행/공제회/국민성장펀드"],
            "manager": []
        },
    }


def load_filter_config():
    """
    filter_config.json에서 AI 관련성 필터 설정 로드.
    파일이 없거나 키가 없으면 환경 변수로 폴백.
    반환: {
        "enable_relevance_filter": bool,
        "relevance_threshold": int,
        "beta_test_mode": bool,
        "enable_keyword_prefilter": bool,
        "relevance_criteria": str or None
    }
    """
    out = {
        "enable_relevance_filter": True,
        "relevance_threshold": 6,
        "beta_test_mode": False,
        "enable_keyword_prefilter": True,
        "relevance_criteria": None,  # None이면 코드의 하드코딩된 기본값 사용
    }
    if os.path.isfile(FILTER_CONFIG_PATH):
        try:
            with open(FILTER_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "enable_relevance_filter" in data:
                v = data["enable_relevance_filter"]
                out["enable_relevance_filter"] = v if isinstance(v, bool) else str(v).lower() in ("true", "1")
            if "relevance_threshold" in data:
                out["relevance_threshold"] = int(data["relevance_threshold"])
            if "beta_test_mode" in data:
                v = data["beta_test_mode"]
                out["beta_test_mode"] = v if isinstance(v, bool) else str(v).lower() in ("true", "1")
            if "enable_keyword_prefilter" in data:
                v = data["enable_keyword_prefilter"]
                out["enable_keyword_prefilter"] = v if isinstance(v, bool) else str(v).lower() in ("true", "1")
            if "relevance_criteria" in data:
                out["relevance_criteria"] = data["relevance_criteria"]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    # 환경 변수로 덮어쓰기 (선택)
    if "ENABLE_RELEVANCE_FILTER" in os.environ:
        out["enable_relevance_filter"] = os.environ.get("ENABLE_RELEVANCE_FILTER", "true").lower() == "true"
    if "RELEVANCE_THRESHOLD" in os.environ:
        try:
            out["relevance_threshold"] = int(os.environ.get("RELEVANCE_THRESHOLD", "6"))
        except ValueError:
            pass
    if "BETA_TEST_MODE" in os.environ:
        out["beta_test_mode"] = os.environ.get("BETA_TEST_MODE", "false").lower() == "true"
    return out
