import os
import json
import time
import re
import requests

from datetime import date, datetime
from urllib.parse import unquote

from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv


# =========================================================
# 1. 환경변수
# =========================================================

load_dotenv()

raw_api_key = os.getenv("TOUR_API_KEY", "")

if not raw_api_key:
    raise ValueError(
        "TOUR_API_KEY가 없습니다. "
        ".env 파일에 TOUR_API_KEY=발급받은키 형태로 입력하세요."
    )

API_KEY = unquote(raw_api_key)


# =========================================================
# 2. API 주소
# =========================================================

BASE_URL = "https://apis.data.go.kr/B551011/KorService2"

FESTIVAL_URL = f"{BASE_URL}/searchFestival2"
COMMON_URL = f"{BASE_URL}/detailCommon2"
INTRO_URL = f"{BASE_URL}/detailIntro2"


# =========================================================
# 3. 기본 설정
# =========================================================

NUM_OF_ROWS = 100

# API를 너무 빠르게 연속 호출하지 않도록 약간 쉬기
REQUEST_DELAY = 0.05

OUTPUT_PATH = "data/events.json"


# =========================================================
# 4. 태그 규칙
# =========================================================

TAG_RULES = {
    "먹거리": [
        "먹거리", "푸드트럭", "푸드존", "먹거리존",
        "미식", "식도락",
        "치맥", "치킨", "맥주", "와인", "막걸리",
        "전어", "꽃게", "수산물",
        "음식축제", "먹거리 축제",
        "로컬푸드", "푸드 페스타", "푸드페스타",
    ],

    "체험": [
        "체험 프로그램", "체험프로그램", "체험존",
        "체험 부스", "체험부스",
        "만들기 체험", "만들기",
        "원데이 클래스", "워크숍", "워크샵",
        "미션투어", "미션 투어",
        "보물찾기", "스탬프 투어",
        "직접 체험", "참여형 체험",
    ],

    "공연": [
        "공연", "콘서트", "버스킹",
        "뮤지컬", "연극", "국악",
        "무용", "댄스", "퍼포먼스",
        "마술공연", "재즈", "밴드",
        "가요제", "음악회",
        "페인터즈", "예술제", "춤축제",
    ],

    "전통·역사": [
        "전통문화", "전통예술",
        "국가유산", "문화유산", "문화재",
        "궁궐", "왕궁", "조선시대",
        "수문장", "파수의식",
        "농악", "풍물", "민속",
        "한복", "향교", "서원",
        "역사탐방", "역사문화",
    ],

    "자연": [
        "생태", "갯벌", "반딧불",
        "꽃 축제", "꽃축제",
        "맥문동", "억새", "단풍",
        "수목원", "자연휴양림",
        "해양축제", "바다축제",
        "숲 체험", "숲체험",
    ],

    "야간": [
        "야간", "야행", "야경",
        "나이트", "별빛", "달빛",
        "심야", "밤하늘",
        "드론쇼", "드론 쇼",
        "불꽃쇼", "불꽃 쇼",
        "라이트쇼", "라이트 쇼",
        "야시장", "유등",
    ],

    "마켓": [
        "플리마켓", "플리 마켓",
        "야시장", "마켓 부스",
        "아트마켓", "아트 마켓",
        "로컬마켓", "로컬 마켓",
        "장터", "판매장터",
    ],

    "전시·박람회": [
        "박람회", "비엔날레",
        "페어", "아트페어",
        "특별전시", "기획전시",
        "사진전", "작품전",
        "전시 프로그램",
        "영화제",
    ],

    "스포츠·레저": [
        "e스포츠", "이스포츠",
        "스포츠제전", "스포츠 대회",
        "걷기대회", "워킹 페스티벌",
        "러닝", "마라톤",
        "요트", "카누", "철인3종",
        "카약", "패들보드",
        "해양레저",
    ],

    "가족": [
        "가족 단위", "가족과 함께",
        "어린이", "키즈",
        "유아", "아동",
        "아이와", "아이들",
        "어린이날",
        "놀이시설", "키즈존",
    ],
}


# =========================================================
# 5. 공통 API 호출
# =========================================================

def request_api(url, params):
    try:
        response = requests.get(
            url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        print(f"API 요청 실패: {error}")
        return None

    try:
        data = response.json()

    except ValueError:
        print("JSON 변환 실패")
        return None

    # 일반적인 TourAPI 응답
    if "response" in data:
        header = data.get("response", {}).get("header", {})

        result_code = header.get("resultCode")

        if result_code != "0000":
            print(
                "TourAPI 오류:",
                result_code,
                header.get("resultMsg"),
            )
            return None

    # 일부 오류 응답 형태 대응
    elif data.get("resultCode"):
        print(
            "TourAPI 오류:",
            data.get("resultCode"),
            data.get("resultMsg"),
        )
        return None

    return data


# =========================================================
# 6. 공통 파라미터
# =========================================================

COMMON_PARAMS = {
    "serviceKey": API_KEY,
    "MobileOS": "ETC",
    "MobileApp": "fundays",
    "_type": "json",
}


# =========================================================
# 7. 시/도 추출
# =========================================================

def extract_region(address):
    if not address:
        return ""

    parts = address.strip().split()

    if not parts:
        return ""

    first = parts[0]
    second = parts[1] if len(parts) > 1 else ""

    # 일반적인 축약/비표준 표기 보정
    aliases = {
        "서울": "서울특별시",
        "서울특별": "서울특별시",

        "부산": "부산광역시",
        "대구": "대구광역시",
        "인천": "인천광역시",
        "광주": "광주광역시",
        "대전": "대전광역시",
        "울산": "울산광역시",

        "세종": "세종특별자치시",

        "경기": "경기도",

        "강원": "강원특별자치도",

        "충북": "충청북도",
        "충남": "충청남도",

        "전북": "전북특별자치도",
        "전남": "전라남도",

        "경북": "경상북도",
        "경남": "경상남도",

        "제주": "제주특별자치도",
    }

    if first in aliases:
        return aliases[first]

    # 현재 TourAPI에서 발견된 특이 표기
    if first == "전남광주통합특별시":

        # 광주광역시의 5개 자치구
        gwangju_districts = {
            "동구",
            "서구",
            "남구",
            "북구",
            "광산구",
        }

        if second in gwangju_districts:
            return "광주광역시"

        # 여수시, 목포시, 무안군, 고흥군 등
        return "전라남도"

    # 광역시·도 없이 도시명부터 시작하는 예외
    city_to_region = {
        "포항시": "경상북도",
    }

    if first in city_to_region:
        return city_to_region[first]

    # 이미 정상적인 시·도라면 그대로 사용
    valid_regions = {
        "서울특별시",
        "부산광역시",
        "대구광역시",
        "인천광역시",
        "광주광역시",
        "대전광역시",
        "울산광역시",
        "세종특별자치시",
        "경기도",
        "강원특별자치도",
        "충청북도",
        "충청남도",
        "전북특별자치도",
        "전라남도",
        "경상북도",
        "경상남도",
        "제주특별자치도",
    }

    if first in valid_regions:
        return first

    # 모르는 형태는 일단 원본 첫 단어 유지
    return first


# =========================================================
# 8. 날짜 형식 변환
# 20260820 → 2026-08-20
# =========================================================

def format_date(date_string):
    if not date_string:
        return ""

    try:
        parsed = datetime.strptime(
            date_string,
            "%Y%m%d",
        )

        return parsed.strftime("%Y-%m-%d")

    except ValueError:
        return date_string


# =========================================================
# 9. 태그용 텍스트 정리
# =========================================================

def normalize_text(value):
    if not value:
        return ""

    value = value.lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# =========================================================
# 10. 태그 자동 생성
# =========================================================

def generate_tags(event):

    # 제목과 개요:
    # 행사의 핵심 성격을 판단할 때 사용
    main_text = normalize_text(
        " ".join([
            event.get("title", ""),
            event.get("overview", ""),
        ])
    )

    # 프로그램:
    # 체험, 야간, 전통 등 부가 성격 판단에 사용
    program_text = normalize_text(
        event.get(
            "program",
            "",
        )
    )

    all_text = (
        main_text
        + " "
        + program_text
    )

    tags = []

    for tag, keywords in TAG_RULES.items():

        # 먹거리 / 마켓 / 공연은
        # 단순 부대 프로그램 때문에
        # 과도하게 붙는 것을 방지
        if tag in {
            "먹거리",
            "마켓",
            "공연",
        }:
            target_text = main_text

        else:
            target_text = all_text

        matched = any(
            keyword.lower() in target_text
            for keyword in keywords
        )

        if matched:
            tags.append(tag)

    # 어떤 태그에도 해당하지 않는 경우
    if not tags:
        tags.append("기타")

    return tags


# =========================================================
# 11. 행사 목록 전체 수집
# =========================================================

def fetch_all_festivals(start_date, end_date):

    all_items = []

    page = 1

    while True:

        params = {
            **COMMON_PARAMS,
            "eventStartDate": start_date,
            "eventEndDate": end_date,
            "numOfRows": NUM_OF_ROWS,
            "pageNo": page,
            "arrange": "A",
        }

        print(
            f"행사 목록 페이지 {page} 조회 중..."
        )

        data = request_api(
            FESTIVAL_URL,
            params,
        )

        if not data:
            break

        body = data["response"]["body"]

        total_count = body.get(
            "totalCount",
            0,
        )

        items_container = (
            body.get("items")
            or {}
        )

        items = (
            items_container.get("item")
            or []
        )

        if isinstance(
            items,
            dict,
        ):
            items = [items]

        if not items:
            break

        all_items.extend(
            items
        )

        print(
            f"  {len(all_items)} / "
            f"{total_count}건 수집"
        )

        if len(all_items) >= total_count:
            break

        page += 1

        time.sleep(
            REQUEST_DELAY
        )

    return all_items


# =========================================================
# 12. detailCommon2
# =========================================================

def fetch_common_detail(content_id):

    params = {
        **COMMON_PARAMS,
        "contentId": content_id,
    }

    data = request_api(
        COMMON_URL,
        params,
    )

    if not data:
        return {}

    body = data["response"]["body"]

    items_container = (
        body.get("items")
        or {}
    )

    items = (
        items_container.get("item")
        or []
    )

    if isinstance(
        items,
        dict,
    ):
        return items

    if (
        isinstance(items, list)
        and items
    ):
        return items[0]

    return {}


# =========================================================
# 13. detailIntro2
# =========================================================

def fetch_intro_detail(
    content_id,
    content_type_id,
):

    params = {
        **COMMON_PARAMS,
        "contentId": content_id,
        "contentTypeId": content_type_id,
    }

    data = request_api(
        INTRO_URL,
        params,
    )

    if not data:
        return {}

    body = data["response"]["body"]

    items_container = (
        body.get("items")
        or {}
    )

    items = (
        items_container.get("item")
        or []
    )

    if isinstance(
        items,
        dict,
    ):
        return items

    if (
        isinstance(items, list)
        and items
    ):
        return items[0]

    return {}


# =========================================================
# 14. 내부 데이터 형태로 정규화
# =========================================================

def normalize_event(
    basic,
    common,
    intro,
):

    address = (
        common.get("addr1")
        or basic.get("addr1", "")
    )

    category_codes = [
        code
        for code in [
            common.get("lclsSystm1")
            or basic.get("lclsSystm1"),

            common.get("lclsSystm2")
            or basic.get("lclsSystm2"),

            common.get("lclsSystm3")
            or basic.get("lclsSystm3"),
        ]
        if code
    ]

    event = {
        "id": basic.get(
            "contentid",
            "",
        ),

        "title": (
            common.get("title")
            or basic.get(
                "title",
                "",
            )
        ),

        "start_date": format_date(
            intro.get("eventstartdate")
            or basic.get(
                "eventstartdate",
                "",
            )
        ),

        "end_date": format_date(
            intro.get("eventenddate")
            or basic.get(
                "eventenddate",
                "",
            )
        ),

        "region": extract_region(
            address
        ),

        "address": address,

        "place": intro.get(
            "eventplace",
            "",
        ),

        "overview": common.get(
            "overview",
            "",
        ),

        "program": intro.get(
            "program",
            "",
        ),

        "playtime": intro.get(
            "playtime",
            "",
        ),

        "price": intro.get(
            "usetimefestival",
            "",
        ),

        "age": intro.get(
            "agelimit",
            "",
        ),

        "homepage": common.get(
            "homepage",
            "",
        ),

        "tel": (
            common.get("tel")
            or basic.get(
                "tel",
                "",
            )
        ),

        "category_codes": (
            category_codes
        ),

        "tags": [],

        "source": "tourapi",
    }

    # 모든 필드가 만들어진 뒤
    # 규칙 기반 태그 생성
    event["tags"] = generate_tags(
        event
    )

    return event


# =========================================================
# 15. 메인 실행
# =========================================================

def main():

    today = date.today()

    three_months_later = (
        today
        + relativedelta(
            months=3
        )
    )

    start_date = today.strftime(
        "%Y%m%d"
    )

    end_date = (
        three_months_later.strftime(
            "%Y%m%d"
        )
    )

    print("=" * 70)
    print(
        "놀만한날 TourAPI 데이터 업데이트"
    )
    print("=" * 70)

    print(
        f"조회 기간: "
        f"{start_date} ~ {end_date}"
    )

    print()

    # -----------------------------------------------------
    # 행사 목록
    # -----------------------------------------------------

    festivals = fetch_all_festivals(
        start_date,
        end_date,
    )

    print()

    print(
        f"행사 목록 총 "
        f"{len(festivals)}건 수집 완료"
    )

    print()

    # -----------------------------------------------------
    # 상세정보
    # -----------------------------------------------------

    normalized_events = []

    total = len(
        festivals
    )

    for index, basic in enumerate(
        festivals,
        start=1,
    ):

        content_id = basic.get(
            "contentid"
        )

        content_type_id = basic.get(
            "contenttypeid"
        )

        title = basic.get(
            "title",
            "",
        )

        print(
            f"[{index}/{total}] "
            f"{title}"
        )

        common = fetch_common_detail(
            content_id
        )

        time.sleep(
            REQUEST_DELAY
        )

        intro = fetch_intro_detail(
            content_id,
            content_type_id,
        )

        time.sleep(
            REQUEST_DELAY
        )

        event = normalize_event(
            basic,
            common,
            intro,
        )

        normalized_events.append(
            event
        )

    # -----------------------------------------------------
    # 날짜 기준 한번 더 필터링
    # -----------------------------------------------------

    today_iso = (
        today.isoformat()
    )

    end_limit_iso = (
        three_months_later.isoformat()
    )

    filtered_events = []

    for event in normalized_events:

        start_date_value = (
            event.get(
                "start_date",
                "",
            )
        )

        end_date_value = (
            event.get(
                "end_date",
                "",
            )
        )

        if (
            not start_date_value
            or not end_date_value
        ):
            continue

        # 이미 종료된 행사 제외
        if end_date_value < today_iso:
            continue

        # 3개월 뒤보다 늦게 시작하는 행사 제외
        if (
            start_date_value
            > end_limit_iso
        ):
            continue

        filtered_events.append(
            event
        )

    # -----------------------------------------------------
    # 정렬
    # -----------------------------------------------------

    filtered_events.sort(
        key=lambda event: (
            event.get(
                "start_date",
                "",
            ),
            event.get(
                "title",
                "",
            ),
        )
    )

    # -----------------------------------------------------
    # 저장
    # -----------------------------------------------------

    os.makedirs(
        "data",
        exist_ok=True,
    )

    output = {
        "updated_at": (
            datetime.now().isoformat(
                timespec="seconds"
            )
        ),

        "range": {
            "start": today.isoformat(),
            "end": (
                three_months_later.isoformat()
            ),
        },

        "count": len(
            filtered_events
        ),

        "events": filtered_events,
    }

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 70)
    print("업데이트 완료")
    print("=" * 70)

    print(
        f"최종 행사 수: "
        f"{len(filtered_events)}건"
    )

    print(
        f"저장 위치: "
        f"{OUTPUT_PATH}"
    )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":
    main()