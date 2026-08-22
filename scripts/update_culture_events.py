import os
import json
import html
import time
import requests
import xml.etree.ElementTree as ET

from datetime import date, datetime
from urllib.parse import unquote

from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv


# =========================================================
# 1. 환경변수
# =========================================================

load_dotenv()

raw_api_key = os.getenv(
    "CULTURE_API_KEY",
    "",
)

if not raw_api_key:
    raise ValueError(
        "CULTURE_API_KEY가 없습니다. "
        ".env 파일 또는 GitHub Secret을 확인하세요."
    )

API_KEY = unquote(
    raw_api_key
)


# =========================================================
# 2. API 주소
# =========================================================

BASE_URL = (
    "https://apis.data.go.kr/"
    "B553457/cultureinfo"
)

PERIOD_URL = (
    f"{BASE_URL}/period2"
)

OUTPUT_PATH = (
    "data/culture_events.json"
)

TEMP_PATH = (
    "data/culture_events.tmp.json"
)


# =========================================================
# 3. 기본 설정
# =========================================================

ROWS = 10

REQUEST_DELAY = 0.3

MAX_RETRIES = 4

RETRY_DELAYS = [
    2,
    4,
    8,
    16,
]


# =========================================================
# 4. 기존 데이터
# =========================================================

def load_existing_events():

    if not os.path.exists(
        OUTPUT_PATH
    ):
        return []

    try:

        with open(
            OUTPUT_PATH,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        events = data.get(
            "events",
            [],
        )

        if isinstance(
            events,
            list,
        ):
            return events

    except (
        OSError,
        json.JSONDecodeError,
    ) as error:

        print(
            f"기존 JSON 읽기 실패: "
            f"{error}"
        )

    return []


# =========================================================
# 5. 날짜
# =========================================================

def format_date(value):

    if not value:
        return ""

    try:

        parsed = datetime.strptime(
            value,
            "%Y%m%d",
        )

        return parsed.strftime(
            "%Y-%m-%d"
        )

    except ValueError:

        return value


# =========================================================
# 6. 지역
# =========================================================

def normalize_region(
    area,
    sigungu="",
):

    area = (
        area or ""
    ).strip()

    sigungu = (
        sigungu or ""
    ).strip()

    aliases = {
        "서울": "서울특별시",
        "서울시": "서울특별시",
        "서울특별": "서울특별시",
        "서울특별시": "서울특별시",

        "부산": "부산광역시",
        "부산광역시": "부산광역시",

        "대구": "대구광역시",
        "대구광역시": "대구광역시",

        "인천": "인천광역시",
        "인천광역시": "인천광역시",

        "광주": "광주광역시",
        "광주광역시": "광주광역시",

        "대전": "대전광역시",
        "대전광역시": "대전광역시",

        "울산": "울산광역시",
        "울산광역시": "울산광역시",

        "세종": "세종특별자치시",
        "세종시": "세종특별자치시",
        "세종특별자치시":
            "세종특별자치시",

        "경기": "경기도",
        "경기도": "경기도",

        "강원": "강원특별자치도",
        "강원도": "강원특별자치도",
        "강원특별자치도":
            "강원특별자치도",

        "충북": "충청북도",
        "충청북도": "충청북도",

        "충남": "충청남도",
        "충청남도": "충청남도",

        "전북": "전북특별자치도",
        "전북특별자치도":
            "전북특별자치도",

        "전남": "전라남도",
        "전라남도": "전라남도",

        "경북": "경상북도",
        "경상북도": "경상북도",

        "경남": "경상남도",
        "경상남도": "경상남도",

        "제주": "제주특별자치도",
        "제주도": "제주특별자치도",
        "제주특별자치도":
            "제주특별자치도",
    }

    jeonnam_cities = {
        "목포시",
        "여수시",
        "순천시",
        "나주시",
        "광양시",
        "담양군",
        "곡성군",
        "구례군",
        "고흥군",
        "보성군",
        "화순군",
        "장흥군",
        "강진군",
        "해남군",
        "영암군",
        "무안군",
        "함평군",
        "영광군",
        "장성군",
        "완도군",
        "진도군",
        "신안군",
    }

    first_sigungu = (
        sigungu.split()[0]
        if sigungu
        else ""
    )

    if area in {
        "광주",
        "광주광역시",
        "전남광주통합",
        "전남광주통합특별시",
    }:

        if (
            first_sigungu
            in jeonnam_cities
        ):
            return "전라남도"

        return "광주광역시"

    if area in aliases:
        return aliases[area]

    if not area:
        return ""

    return area


# =========================================================
# 7. XML item
# =========================================================

def item_to_dict(item):

    result = {}

    for child in item:

        value = (
            child.text or ""
        )

        result[child.tag] = (
            html.unescape(value)
            .strip()
        )

    return result


# =========================================================
# 8. 한 페이지 요청
# =========================================================

def fetch_page(
    page,
    start_date,
    end_date,
):

    params = {
        "serviceKey":
            API_KEY,

        "from":
            start_date,

        "to":
            end_date,

        "PageNo":
            page,

        "rows":
            ROWS,
    }

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = requests.get(
                PERIOD_URL,
                params=params,
                timeout=30,
            )

            response.raise_for_status()

            root = ET.fromstring(
                response.text
            )

            result_code = (
                root.findtext(
                    ".//resultCode"
                )
            )

            result_msg = (
                root.findtext(
                    ".//resultMsg"
                )
            )

            if result_code != "00":

                raise RuntimeError(
                    "문화포털 오류: "
                    f"{result_code} / "
                    f"{result_msg}"
                )

            total_count_text = (
                root.findtext(
                    ".//totalCount"
                )
                or "0"
            )

            total_count = int(
                total_count_text
            )

            items = [
                item_to_dict(item)
                for item
                in root.findall(
                    ".//item"
                )
            ]

            return (
                items,
                total_count,
            )

        except (
            requests.RequestException,
            ET.ParseError,
            ValueError,
            RuntimeError,
        ) as error:

            last_error = error

            print(
                f"API 요청 실패 "
                f"({attempt}/"
                f"{MAX_RETRIES}): "
                f"{error}"
            )

            if attempt < MAX_RETRIES:

                delay = (
                    RETRY_DELAYS[
                        attempt - 1
                    ]
                )

                print(
                    f"{delay}초 후 "
                    "재시도..."
                )

                time.sleep(
                    delay
                )

    raise RuntimeError(
        "문화포털 API가 "
        "반복 실패했습니다: "
        f"{last_error}"
    )


# =========================================================
# 9. 전체 목록
# =========================================================

def fetch_all_items(
    start_date,
    end_date,
):

    all_items = []

    page = 1
    total_count = None

    while True:

        print(
            f"페이지 "
            f"{page} 조회 중..."
        )

        (
            items,
            current_total,
        ) = fetch_page(
            page,
            start_date,
            end_date,
        )

        if total_count is None:

            total_count = (
                current_total
            )

            print(
                f"전체 검색 결과: "
                f"{total_count}건"
            )

        if not items:

            if (
                total_count
                and len(all_items)
                < total_count
            ):

                raise RuntimeError(
                    "문화포털 목록 "
                    "수집이 중간에 "
                    "종료되었습니다."
                )

            break

        all_items.extend(
            items
        )

        print(
            f"  {len(all_items)} / "
            f"{total_count}건"
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
            "문화포털 totalCount를 "
            "확인할 수 없습니다."
        )

    if len(all_items) < total_count:

        raise RuntimeError(
            "문화포털 목록이 "
            "완전히 수집되지 않았습니다. "
            f"{len(all_items)} / "
            f"{total_count}"
        )

    return all_items


# =========================================================
# 10. 정규화
# =========================================================

def normalize_event(item):

    region = normalize_region(
        item.get(
            "area",
            "",
        ),

        item.get(
            "sigungu",
            "",
        ),
    )

    return {
        "id":
            item.get(
                "seq",
                "",
            ),

        "title":
            item.get(
                "title",
                "",
            ),

        "type":
            item.get(
                "realmName",
                "",
            ),

        "service_type":
            item.get(
                "serviceName",
                "",
            ),

        "start_date":
            format_date(
                item.get(
                    "startDate",
                    "",
                )
            ),

        "end_date":
            format_date(
                item.get(
                    "endDate",
                    "",
                )
            ),

        "region":
            region,

        "city":
            item.get(
                "sigungu",
                "",
            ),

        "place":
            item.get(
                "place",
                "",
            ),

        "source":
            "culture",
    }


# =========================================================
# 11. 안전성 검사
# =========================================================

def validate_result(
    new_events,
    old_events,
):

    if not new_events:

        raise RuntimeError(
            "문화포털 최종 결과가 "
            "0건입니다. "
            "기존 JSON을 보존합니다."
        )

    old_count = len(
        old_events
    )

    new_count = len(
        new_events
    )

    if (
        old_count >= 20
        and new_count
        < old_count * 0.5
    ):

        raise RuntimeError(
            "문화 행사 수가 "
            "비정상적으로 급감했습니다. "
            f"기존 {old_count}건 → "
            f"신규 {new_count}건. "
            "저장을 취소합니다."
        )


# =========================================================
# 12. 안전 저장
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
# 13. 메인
# =========================================================

def main():

    today = date.today()

    three_months_later = (
        today
        + relativedelta(
            months=3
        )
    )

    start_date = (
        today.strftime(
            "%Y%m%d"
        )
    )

    end_date = (
        three_months_later.strftime(
            "%Y%m%d"
        )
    )

    print("=" * 70)
    print(
        "놀만한날 문화포털 "
        "데이터 업데이트"
    )
    print("=" * 70)

    print(
        f"조회 기간: "
        f"{start_date} ~ "
        f"{end_date}"
    )

    old_events = (
        load_existing_events()
    )

    print(
        f"기존 DB: "
        f"{len(old_events)}건"
    )

    print()

    # -----------------------------------------------------
    # 수집
    # -----------------------------------------------------

    items = fetch_all_items(
        start_date,
        end_date,
    )

    print()
    print(
        f"원본 수집 완료: "
        f"{len(items)}건"
    )

    # -----------------------------------------------------
    # 정규화
    # -----------------------------------------------------

    events = [
        normalize_event(item)
        for item in items
    ]

    # -----------------------------------------------------
    # 중복 제거
    # -----------------------------------------------------

    unique_events = {}

    for event in events:

        event_id = event.get(
            "id",
            "",
        )

        if not event_id:
            continue

        unique_events[
            event_id
        ] = event

    events = list(
        unique_events.values()
    )

    # -----------------------------------------------------
    # 날짜 조건
    # -----------------------------------------------------

    today_iso = (
        today.isoformat()
    )

    end_limit_iso = (
        three_months_later
        .isoformat()
    )

    filtered_events = []

    for event in events:

        start_value = (
            event.get(
                "start_date",
                "",
            )
        )

        end_value = (
            event.get(
                "end_date",
                "",
            )
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

    # -----------------------------------------------------
    # 정렬
    # -----------------------------------------------------

    def sort_key(event):

        start = event.get(
            "start_date",
            "",
        )

        end = event.get(
            "end_date",
            "",
        )

        is_ongoing = (
            start
            <= today_iso
            <= end
        )

        if is_ongoing:

            return (
                0,
                end,
                start,
                event.get(
                    "title",
                    "",
                ),
            )

        return (
            1,
            start,
            end,
            event.get(
                "title",
                "",
            ),
        )

    filtered_events.sort(
        key=sort_key
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
            datetime.now()
            .isoformat(
                timespec="seconds"
            ),

        "range": {
            "start":
                today.isoformat(),

            "end":
                three_months_later
                .isoformat(),
        },

        "count":
            len(filtered_events),

        "events":
            filtered_events,
    }

    save_output(
        output
    )

    print()
    print("=" * 70)
    print("업데이트 완료")
    print("=" * 70)

    print(
        f"원본 행사 수: "
        f"{len(items)}건"
    )

    print(
        f"고유 행사 수: "
        f"{len(events)}건"
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