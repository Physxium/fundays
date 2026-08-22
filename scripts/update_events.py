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
        ".env 파일 또는 GitHub Secret을 확인하세요."
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

REQUEST_DELAY = 0.25

MAX_RETRIES = 4
RETRY_DELAYS = [2, 4, 8, 16]

OUTPUT_PATH = "data/events.json"
TEMP_PATH = "data/events.tmp.json"


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
# 5. 기존 JSON 읽기
# =========================================================

def load_existing_events():

    if not os.path.exists(OUTPUT_PATH):
        return []

    try:
        with open(
            OUTPUT_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        events = data.get("events", [])

        if isinstance(events, list):
            return events

    except (
        OSError,
        json.JSONDecodeError,
    ) as error:
        print(
            f"기존 JSON 읽기 실패: {error}"
        )

    return []


# =========================================================
# 6. API 호출
# =========================================================

def request_api(url, params):

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:
            response = requests.get(
                url,
                params=params,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

            if "response" in data:

                header = (
                    data
                    .get("response", {})
                    .get("header", {})
                )

                result_code = (
                    header.get("resultCode")
                )

                if result_code != "0000":
                    raise RuntimeError(
                        "TourAPI 오류: "
                        f"{result_code} / "
                        f"{header.get('resultMsg')}"
                    )

            elif data.get("resultCode"):

                raise RuntimeError(
                    "TourAPI 오류: "
                    f"{data.get('resultCode')} / "
                    f"{data.get('resultMsg')}"
                )

            return data

        except (
            requests.RequestException,
            ValueError,
            RuntimeError,
        ) as error:

            last_error = error

            print(
                f"API 요청 실패 "
                f"({attempt}/{MAX_RETRIES}): "
                f"{error}"
            )

            if attempt < MAX_RETRIES:

                delay = RETRY_DELAYS[
                    attempt - 1
                ]

                print(
                    f"{delay}초 후 재시도..."
                )

                time.sleep(delay)

    raise RuntimeError(
        "API 요청이 반복 실패했습니다: "
        f"{last_error}"
    )


# =========================================================
# 7. 공통 파라미터
# =========================================================

COMMON_PARAMS = {
    "serviceKey": API_KEY,
    "MobileOS": "ETC",
    "MobileApp": "fundays",
    "_type": "json",
}


# =========================================================
# 8. 지역
# =========================================================

def extract_region(address):

    if not address:
        return ""

    parts = address.strip().split()

    if not parts:
        return ""

    first = parts[0]
    second = (
        parts[1]
        if len(parts) > 1
        else ""
    )

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

    if first == "전남광주통합특별시":

        gwangju_districts = {
            "동구",
            "서구",
            "남구",
            "북구",
            "광산구",
        }

        if second in gwangju_districts:
            return "광주광역시"

        return "전라남도"

    city_to_region = {
        "포항시": "경상북도",
    }

    if first in city_to_region:
        return city_to_region[first]

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

    return first


# =========================================================
# 9. 날짜
# =========================================================

def format_date(date_string):

    if not date_string:
        return ""

    try:
        parsed = datetime.strptime(
            date_string,
            "%Y%m%d",
        )

        return parsed.strftime(
            "%Y-%m-%d"
        )

    except ValueError:
        return date_string


# =========================================================
# 10. 태그
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


def generate_tags(event):

    main_text = normalize_text(
        " ".join([
            event.get("title", ""),
            event.get("overview", ""),
        ])
    )

    program_text = normalize_text(
        event.get("program", "")
    )

    all_text = (
        main_text
        + " "
        + program_text
    )

    tags = []

    for tag, keywords in TAG_RULES.items():

        if tag in {
            "먹거리",
            "마켓",
            "공연",
        }:
            target_text = main_text
        else:
            target_text = all_text

        if any(
            keyword.lower() in target_text
            for keyword in keywords
        ):
            tags.append(tag)

    if not tags:
        tags.append("기타")

    return tags


# =========================================================
# 11. 행사 목록 전체 수집
# =========================================================

def fetch_all_festivals(
    start_date,
    end_date,
):

    all_items = []

    page = 1
    total_count = None

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
            f"행사 목록 페이지 "
            f"{page} 조회 중..."
        )

        data = request_api(
            FESTIVAL_URL,
            params,
        )

        body = (
            data["response"]["body"]
        )

        current_total = body.get(
            "totalCount",
            0,
        )

        if total_count is None:

            total_count = current_total

            print(
                f"전체 검색 결과: "
                f"{total_count}건"
            )

        items_container = (
            body.get("items")
            or {}
        )

        items = (
            items_container.get("item")
            or []
        )

        if isinstance(items, dict):
            items = [items]

        if not items:

            if (
                total_count
                and len(all_items)
                < total_count
            ):
                raise RuntimeError(
                    "목록 수집이 중간에 "
                    "비정상적으로 종료되었습니다."
                )

            break

        all_items.extend(items)

        print(
            f"  {len(all_items)} / "
            f"{total_count}건 수집"
        )

        if (
            total_count is not None
            and len(all_items)
            >= total_count
        ):
            break

        page += 1

        time.sleep(
            REQUEST_DELAY
        )

    if total_count is None:
        raise RuntimeError(
            "TourAPI totalCount를 "
            "확인할 수 없습니다."
        )

    if len(all_items) < total_count:

        raise RuntimeError(
            "TourAPI 목록이 "
            "완전히 수집되지 않았습니다. "
            f"{len(all_items)} / "
            f"{total_count}"
        )

    return all_items


# =========================================================
# 12. 상세 API
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

    body = data["response"]["body"]

    items_container = (
        body.get("items")
        or {}
    )

    items = (
        items_container.get("item")
        or []
    )

    if isinstance(items, dict):
        return items

    if (
        isinstance(items, list)
        and items
    ):
        return items[0]

    return {}


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

    body = data["response"]["body"]

    items_container = (
        body.get("items")
        or {}
    )

    items = (
        items_container.get("item")
        or []
    )

    if isinstance(items, dict):
        return items

    if (
        isinstance(items, list)
        and items
    ):
        return items[0]

    return {}


# =========================================================
# 13. 신규 행사 정규화
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
            or basic.get("title", "")
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
            or basic.get("tel", "")
        ),

        "category_codes":
            category_codes,

        "tags": [],

        "source": "tourapi",
    }

    event["tags"] = (
        generate_tags(event)
    )

    return event


# =========================================================
# 14. 기존 행사에 목록 정보 반영
# =========================================================

def refresh_existing_event(
    existing,
    basic,
):

    event = dict(existing)

    title = basic.get(
        "title",
        "",
    )

    start_date = format_date(
        basic.get(
            "eventstartdate",
            "",
        )
    )

    end_date = format_date(
        basic.get(
            "eventenddate",
            "",
        )
    )

    address = basic.get(
        "addr1",
        "",
    )

    tel = basic.get(
        "tel",
        "",
    )

    if title:
        event["title"] = title

    if start_date:
        event["start_date"] = start_date

    if end_date:
        event["end_date"] = end_date

    if address:

        event["address"] = address

        event["region"] = (
            extract_region(address)
        )

    if tel:
        event["tel"] = tel

    event["tags"] = (
        generate_tags(event)
    )

    return event


# =========================================================
# 15. 안전성 검사
# =========================================================

def validate_result(
    new_events,
    old_events,
):

    if not new_events:

        raise RuntimeError(
            "최종 행사 수가 0건입니다. "
            "기존 JSON을 보존합니다."
        )

    old_count = len(old_events)
    new_count = len(new_events)

    if (
        old_count >= 20
        and new_count
        < old_count * 0.5
    ):

        raise RuntimeError(
            "행사 수가 비정상적으로 "
            "급감했습니다. "
            f"기존 {old_count}건 → "
            f"신규 {new_count}건. "
            "저장을 취소합니다."
        )


# =========================================================
# 16. 안전 저장
# =========================================================

def save_output(output):

    os.makedirs(
        "data",
        exist_ok=True,
    )

    with open(
        TEMP_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        TEMP_PATH,
        OUTPUT_PATH,
    )


# =========================================================
# 17. 메인
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

    old_events = (
        load_existing_events()
    )

    old_by_id = {
        str(event.get("id")): event
        for event in old_events
        if event.get("id")
    }

    print(
        f"기존 DB: "
        f"{len(old_events)}건"
    )

    print()

    # -----------------------------------------------------
    # 목록 조회
    # -----------------------------------------------------

    festivals = (
        fetch_all_festivals(
            start_date,
            end_date,
        )
    )

    print()
    print(
        f"행사 목록 "
        f"{len(festivals)}건 수집 완료"
    )

    # -----------------------------------------------------
    # 기존 / 신규 분리
    # -----------------------------------------------------

    normalized_events = []

    new_count = 0
    reused_count = 0

    total = len(festivals)

    for index, basic in enumerate(
        festivals,
        start=1,
    ):

        content_id = str(
            basic.get(
                "contentid",
                "",
            )
        )

        if not content_id:
            continue

        title = basic.get(
            "title",
            "",
        )

        if content_id in old_by_id:

            print(
                f"[{index}/{total}] "
                f"기존 유지: {title}"
            )

            event = (
                refresh_existing_event(
                    old_by_id[
                        content_id
                    ],
                    basic,
                )
            )

            normalized_events.append(
                event
            )

            reused_count += 1

            continue

        # -------------------------------------------------
        # 신규 ID만 상세 API 호출
        # -------------------------------------------------

        print(
            f"[{index}/{total}] "
            f"신규 상세 조회: {title}"
        )

        content_type_id = basic.get(
            "contenttypeid"
        )

        common = (
            fetch_common_detail(
                content_id
            )
        )

        time.sleep(
            REQUEST_DELAY
        )

        intro = (
            fetch_intro_detail(
                content_id,
                content_type_id,
            )
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

        new_count += 1

    # -----------------------------------------------------
    # 날짜 조건
    # -----------------------------------------------------

    today_iso = (
        today.isoformat()
    )

    end_limit_iso = (
        three_months_later.isoformat()
    )

    filtered_events = []

    for event in normalized_events:

        start_value = event.get(
            "start_date",
            "",
        )

        end_value = event.get(
            "end_date",
            "",
        )

        if (
            not start_value
            or not end_value
        ):
            continue

        if end_value < today_iso:
            continue

        if (
            start_value
            > end_limit_iso
        ):
            continue

        filtered_events.append(
            event
        )

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
    # 안전성 검사
    # -----------------------------------------------------

    validate_result(
        filtered_events,
        old_events,
    )

    # -----------------------------------------------------
    # 저장
    # -----------------------------------------------------

    output = {
        "updated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "range": {
            "start":
                today.isoformat(),

            "end":
                three_months_later.isoformat(),
        },

        "count":
            len(filtered_events),

        "events":
            filtered_events,
    }

    save_output(output)

    print()
    print("=" * 70)
    print("업데이트 완료")
    print("=" * 70)

    print(
        f"기존 재사용: "
        f"{reused_count}건"
    )

    print(
        f"신규 상세 조회: "
        f"{new_count}건"
    )

    print(
        f"최종 행사 수: "
        f"{len(filtered_events)}건"
    )

    print(
        f"저장 위치: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()