const state = {
    tab: "festival",

    dateFilter: "all",
    selectedDate: null,

    region: "전체",
    category: "전체",

    visibleCount: 20,
};


let festivalEvents = [];
let cultureEvents = [];


/* =========================================================
   DOM
========================================================= */

const eventsEl =
    document.getElementById("events");

const resultSummaryEl =
    document.getElementById("resultSummary");

const moreWrapEl =
    document.getElementById("moreWrap");


const dateFiltersEl =
    document.getElementById("dateFilters");

const customDateButtonEl =
    document.getElementById("customDateButton");

const customDateInputEl =
    document.getElementById("customDateInput");


const regionSelectEl =
    document.getElementById("regionSelect");


const categoryFilterLabelEl =
    document.getElementById("categoryFilterLabel");

const categoryFiltersEl =
    document.getElementById("categoryFilters");


const eventModalEl =
    document.getElementById("eventModal");

const modalContentEl =
    document.getElementById("modalContent");

const modalCloseEl =
    document.getElementById("modalClose");


/* =========================================================
   필터 목록
========================================================= */

const FESTIVAL_TAGS = [
    "전체",
    "먹거리",
    "체험",
    "공연",
    "전통·역사",
    "자연",
    "야간",
    "마켓",
    "전시·박람회",
    "스포츠·레저",
    "가족",
];


const CULTURE_TYPES = [
    "전체",
    "음악/콘서트",
    "전시",
    "연극",
    "뮤지컬/오페라",
    "교육/체험",
    "국악",
    "무용/발레",
    "아동/가족",
    "기타",
];


/* =========================================================
   날짜
========================================================= */

function parseDate(dateString) {

    if (!dateString) {
        return null;
    }


    const parts =
        dateString
            .split("-")
            .map(Number);


    if (parts.length !== 3) {
        return null;
    }


    return new Date(
        parts[0],
        parts[1] - 1,
        parts[2]
    );
}


function dateToString(date) {

    const year =
        date.getFullYear();

    const month =
        String(
            date.getMonth() + 1
        ).padStart(2, "0");

    const day =
        String(
            date.getDate()
        ).padStart(2, "0");


    return `${year}-${month}-${day}`;
}


function addDays(date, days) {

    const result =
        new Date(date);


    result.setDate(
        result.getDate() + days
    );


    return result;
}


function getTodayString() {

    const today =
        new Date();


    today.setHours(
        0,
        0,
        0,
        0
    );


    return dateToString(today);
}


function formatShortDate(dateString) {

    const date =
        parseDate(dateString);


    if (!date) {
        return "";
    }


    return (
        `${date.getMonth() + 1}.` +
        `${date.getDate()}`
    );
}


function formatPeriod(event) {

    const start =
        formatShortDate(
            event.start_date
        );

    const end =
        formatShortDate(
            event.end_date
        );


    if (!start) {
        return "";
    }


    if (
        !end ||
        event.start_date === event.end_date
    ) {
        return start;
    }


    return `${start} ~ ${end}`;
}


function formatSelectedDate(dateString) {

    const date =
        parseDate(dateString);


    if (!date) {
        return "날짜 선택";
    }


    return (
        `${date.getMonth() + 1}월 ` +
        `${date.getDate()}일`
    );
}


/* =========================================================
   지역
========================================================= */

const REGION_SHORT_NAMES = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
};


function shortRegion(region) {

    return (
        REGION_SHORT_NAMES[region]
        || region
        || ""
    );
}


/* =========================================================
   HTML 안전 처리
========================================================= */

function escapeHtml(value) {

    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* =========================================================
   외부 URL
========================================================= */

function safeExternalUrl(value) {

    if (!value) {
        return null;
    }


    const text =
        String(value).trim();


    const match =
        text.match(
            /https?:\/\/[^\s<>"']+/i
        );


    if (!match) {
        return null;
    }


    try {

        const url =
            new URL(match[0]);


        if (
            url.protocol === "http:" ||
            url.protocol === "https:"
        ) {
            return url.href;
        }

    } catch (error) {
        return null;
    }


    return null;
}


/* =========================================================
   정렬
========================================================= */

function sortEvents(events) {

    const today =
        getTodayString();


    return [...events].sort(
        (a, b) => {

            const aActive =
                a.start_date <= today &&
                a.end_date >= today;

            const bActive =
                b.start_date <= today &&
                b.end_date >= today;


            if (
                aActive &&
                !bActive
            ) {
                return -1;
            }


            if (
                !aActive &&
                bActive
            ) {
                return 1;
            }


            if (
                aActive &&
                bActive
            ) {

                const endCompare =
                    a.end_date.localeCompare(
                        b.end_date
                    );


                if (endCompare !== 0) {
                    return endCompare;
                }

            } else {

                const startCompare =
                    a.start_date.localeCompare(
                        b.start_date
                    );


                if (startCompare !== 0) {
                    return startCompare;
                }

            }


            return (
                a.title || ""
            ).localeCompare(
                b.title || "",
                "ko"
            );
        }
    );
}


/* =========================================================
   날짜 필터
========================================================= */

function eventMatchesDate(event) {

    if (state.dateFilter === "all") {
        return true;
    }


    const today =
        new Date();


    today.setHours(
        0,
        0,
        0,
        0
    );


    if (state.dateFilter === "today") {

        const target =
            dateToString(today);


        return (
            event.start_date <= target &&
            event.end_date >= target
        );
    }


    if (state.dateFilter === "weekend") {

        const day =
            today.getDay();


        if (day === 0) {

            const sunday =
                dateToString(today);


            return (
                event.start_date <= sunday &&
                event.end_date >= sunday
            );
        }


        let daysUntilSaturday =
            6 - day;


        if (daysUntilSaturday < 0) {
            daysUntilSaturday += 7;
        }


        const saturday =
            addDays(
                today,
                daysUntilSaturday
            );


        const sunday =
            addDays(
                saturday,
                1
            );


        const weekendStart =
            dateToString(saturday);

        const weekendEnd =
            dateToString(sunday);


        return (
            event.start_date <= weekendEnd &&
            event.end_date >= weekendStart
        );
    }


    if (
        state.dateFilter === "custom" &&
        state.selectedDate
    ) {

        return (
            event.start_date <= state.selectedDate &&
            event.end_date >= state.selectedDate
        );
    }


    return true;
}


/* =========================================================
   지역 필터
========================================================= */

function eventMatchesRegion(event) {

    return (
        state.region === "전체" ||
        event.region === state.region
    );
}


/* =========================================================
   관심사 / 종류 필터
========================================================= */

function eventMatchesCategory(event) {

    if (state.category === "전체") {
        return true;
    }


    if (state.tab === "festival") {

        return (
            Array.isArray(event.tags) &&
            event.tags.includes(
                state.category
            )
        );
    }


    return (
        event.type === state.category
    );
}


/* =========================================================
   현재 데이터
========================================================= */

function getCurrentEvents() {

    let events;


    if (state.tab === "festival") {

        events =
            festivalEvents;

    } else {

        events =
            cultureEvents.filter(
                event =>
                    event.type !== "행사/축제"
            );
    }


    events =
        events
            .filter(eventMatchesDate)
            .filter(eventMatchesRegion)
            .filter(eventMatchesCategory);


    return sortEvents(events);
}


/* =========================================================
   행사·축제 카드
========================================================= */

function festivalCard(event) {

    const tags =
        Array.isArray(event.tags)
            ? event.tags
            : [];


    return `
        <article
            class="event-card festival-card"
            data-event-id="${escapeHtml(event.id)}"
            tabindex="0"
            role="button"
        >

            <div class="event-top">

                <span class="event-period">
                    ${escapeHtml(
        formatPeriod(event)
    )}
                </span>

                <span class="event-region">
                    ${escapeHtml(
        shortRegion(event.region)
    )}
                </span>

            </div>


            <h2 class="event-title">
                ${escapeHtml(event.title)}
            </h2>


            <p class="event-place">
                ${escapeHtml(
        event.place
        || event.address
        || "장소 정보 없음"
    )}
            </p>


            ${tags.length
            ? `
                        <div class="tag-row">

                            ${tags
                .map(
                    tag => `
                                        <span class="tag">
                                            ${escapeHtml(tag)}
                                        </span>
                                    `
                )
                .join("")
            }

                        </div>
                    `
            : ""
        }

        </article>
    `;
}


/* =========================================================
   Culture 검색
========================================================= */

function buildCultureQuery(event) {

    return [
        event.title,
        shortRegion(event.region),
    ]
        .filter(Boolean)
        .join(" ");
}


function openNaverSearch(event) {

    const query =
        buildCultureQuery(event);


    if (!query) {
        return;
    }


    const url =
        "https://search.naver.com/search.naver?query="
        + encodeURIComponent(query);


    window.open(
        url,
        "_blank",
        "noopener,noreferrer"
    );
}


function openGoogleSearch(event) {

    const query =
        buildCultureQuery(event);


    if (!query) {
        return;
    }


    const url =
        "https://www.google.com/search?q="
        + encodeURIComponent(query);


    window.open(
        url,
        "_blank",
        "noopener,noreferrer"
    );
}


/* =========================================================
   공연·전시 카드
========================================================= */

function cultureCard(event) {

    const type =
        event.type || "기타";


    return `
        <article
            class="event-card culture-card"
            data-culture-id="${escapeHtml(event.id)}"
        >

            <div class="event-top">

                <span class="event-period">
                    ${escapeHtml(
        formatPeriod(event)
    )}
                </span>

                <span class="event-region">
                    ${escapeHtml(
        shortRegion(event.region)
    )}
                </span>

            </div>


            <h2 class="event-title">
                ${escapeHtml(event.title)}
            </h2>


            <p class="event-place">
                ${escapeHtml(
        event.place
        || event.city
        || "장소 정보 없음"
    )}
            </p>


            <div class="tag-row">

                <span class="tag">
                    ${escapeHtml(type)}
                </span>

            </div>


            <div class="search-actions">

                <button
                    class="search-btn"
                    type="button"
                    data-search="naver"
                >
                    네이버에서 찾기
                </button>

                <button
                    class="search-btn"
                    type="button"
                    data-search="google"
                >
                    Google에서 찾기
                </button>

            </div>

        </article>
    `;
}


/* =========================================================
   Festival 상세 모달
========================================================= */

function modalInfoItem(label, value) {

    if (!value) {
        return "";
    }


    return `
        <div class="modal-info-item">

            <div class="modal-info-label">
                ${escapeHtml(label)}
            </div>

            <div class="modal-info-value">
                ${escapeHtml(value)}
            </div>

        </div>
    `;
}


function modalSection(title, value) {

    if (!value) {
        return "";
    }


    return `
        <section class="modal-section">

            <h3 class="modal-section-title">
                ${escapeHtml(title)}
            </h3>

            <p class="modal-section-text">
                ${escapeHtml(value)}
            </p>

        </section>
    `;
}


function openFestivalModal(event) {

    const tags =
        Array.isArray(event.tags)
            ? event.tags
            : [];


    const meta =
        [
            shortRegion(event.region),
            formatPeriod(event),
        ]
            .filter(Boolean)
            .join(" · ");


    const infoItems =
        [
            modalInfoItem(
                "운영 시간",
                event.playtime
            ),

            modalInfoItem(
                "요금",
                event.price
            ),

            modalInfoItem(
                "이용 연령",
                event.age
            ),
        ]
            .filter(Boolean)
            .join("");


    const homepage =
        safeExternalUrl(
            event.homepage
        );


    const contactExists =
        Boolean(
            event.tel ||
            homepage
        );


    modalContentEl.innerHTML = `

        <h2
            class="modal-title"
            id="modalTitle"
        >
            ${escapeHtml(event.title)}
        </h2>


        ${meta
            ? `
                    <p class="modal-meta">
                        ${escapeHtml(meta)}
                    </p>
                `
            : ""
        }


        ${event.place ||
            event.address
            ? `
                    <div class="modal-location">

                        ${event.place
                ? `
                                    <p class="modal-place">
                                        ${escapeHtml(event.place)}
                                    </p>
                                `
                : ""
            }

                        ${event.address
                ? `
                                    <p class="modal-address">
                                        ${escapeHtml(event.address)}
                                    </p>
                                `
                : ""
            }

                    </div>
                `
            : ""
        }


        ${tags.length
            ? `
                    <div class="tag-row modal-tags">

                        ${tags
                .map(
                    tag => `
                                    <span class="tag">
                                        ${escapeHtml(tag)}
                                    </span>
                                `
                )
                .join("")
            }

                    </div>
                `
            : ""
        }

        ${event.tel
            ? `
                    <div class="modal-contact">

                        <p class="modal-tel">
                            문의 ${escapeHtml(event.tel)}
                        </p>

                    </div>
                `
            : ""
        }

        ${
        infoItems
            ? `
            <div class="modal-info-grid">
                ${infoItems}
            </div>
        `
            : ""
        }


        ${homepage
                    ? `
                    <div class="modal-homepage-wrap">

                        <a
                            class="modal-homepage"
                            href="${escapeHtml(homepage)}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            관련 페이지 보기
                        </a>

                    </div>
                `
                    : ""
                }


        ${modalSection(
                    "행사 소개",
                    event.overview
                )}


        ${modalSection(
                    "프로그램",
                    event.program
                )}


    `;


    eventModalEl.classList.add(
        "open"
    );


    eventModalEl.setAttribute(
        "aria-hidden",
        "false"
    );


    document.body.classList.add(
        "modal-open"
    );


    modalCloseEl.focus();
}


function closeFestivalModal() {

    eventModalEl.classList.remove(
        "open"
    );


    eventModalEl.setAttribute(
        "aria-hidden",
        "true"
    );


    document.body.classList.remove(
        "modal-open"
    );
}


/* =========================================================
   카테고리 UI
========================================================= */

function renderCategoryFilters() {

    const items =
        state.tab === "festival"
            ? FESTIVAL_TAGS
            : CULTURE_TYPES;


    categoryFilterLabelEl.textContent =
        state.tab === "festival"
            ? "관심사"
            : "종류";


    categoryFiltersEl.innerHTML =
        items
            .map(
                item => `
                    <button
                        class="
                            filter-btn
                            ${state.category === item
                        ? "active"
                        : ""
                    }
                        "
                        type="button"
                        data-category="${escapeHtml(item)}"
                    >
                        ${escapeHtml(item)}
                    </button>
                `
            )
            .join("");


    categoryFiltersEl
        .querySelectorAll(
            "[data-category]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    state.category =
                        button.dataset.category;

                    state.visibleCount =
                        20;


                    renderCategoryFilters();
                    render();
                }
            );

        });
}


/* =========================================================
   날짜 UI
========================================================= */

function renderDateFilters() {

    dateFiltersEl
        .querySelectorAll(
            "[data-date-filter]"
        )
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.dateFilter ===
                state.dateFilter
            );

        });


    customDateButtonEl.textContent =
        state.selectedDate
            ? formatSelectedDate(
                state.selectedDate
            )
            : "날짜 선택";
}


/* =========================================================
   렌더링
========================================================= */

function render() {

    const events =
        getCurrentEvents();


    const visible =
        events.slice(
            0,
            state.visibleCount
        );


    resultSummaryEl.textContent =
        state.tab === "festival"
            ? `행사·축제 ${events.length}개`
            : `공연·전시 ${events.length}개`;


    if (!visible.length) {

        eventsEl.innerHTML = `
            <div class="empty">
                조건에 맞는 행사가 없습니다.
            </div>
        `;


        moreWrapEl.innerHTML =
            "";


        return;
    }


    eventsEl.innerHTML =
        visible
            .map(
                event =>
                    state.tab === "festival"
                        ? festivalCard(event)
                        : cultureCard(event)
            )
            .join("");


    /*
       Festival 카드
    */

    if (state.tab === "festival") {

        eventsEl
            .querySelectorAll(
                ".festival-card"
            )
            .forEach(card => {

                const open =
                    () => {

                        const event =
                            festivalEvents.find(
                                item =>
                                    String(item.id) ===
                                    card.dataset.eventId
                            );


                        if (event) {
                            openFestivalModal(event);
                        }
                    };


                card.addEventListener(
                    "click",
                    open
                );


                card.addEventListener(
                    "keydown",
                    event => {

                        if (
                            event.key === "Enter" ||
                            event.key === " "
                        ) {

                            event.preventDefault();

                            open();
                        }
                    }
                );

            });
    }


    /*
       Culture 검색 버튼
    */

    if (state.tab === "culture") {

        eventsEl
            .querySelectorAll(
                ".culture-card"
            )
            .forEach(card => {

                const event =
                    cultureEvents.find(
                        item =>
                            String(item.id) ===
                            card.dataset.cultureId
                    );


                if (!event) {
                    return;
                }


                card
                    .querySelectorAll(
                        ".search-btn"
                    )
                    .forEach(button => {

                        button.addEventListener(
                            "click",
                            () => {

                                if (
                                    button.dataset.search ===
                                    "naver"
                                ) {
                                    openNaverSearch(event);
                                }


                                if (
                                    button.dataset.search ===
                                    "google"
                                ) {
                                    openGoogleSearch(event);
                                }
                            }
                        );

                    });

            });
    }


    /*
       더 보기
    */

    if (
        events.length >
        state.visibleCount
    ) {

        moreWrapEl.innerHTML = `
            <button
                class="more-btn"
                id="moreBtn"
                type="button"
            >
                행사 더 보기
            </button>
        `;


        document
            .getElementById("moreBtn")
            .addEventListener(
                "click",
                () => {

                    state.visibleCount +=
                        20;

                    render();
                }
            );

    } else {

        moreWrapEl.innerHTML =
            "";
    }
}


/* =========================================================
   탭
========================================================= */

function setupTabs() {

    document
        .querySelectorAll(
            ".tab-btn"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    state.tab =
                        button.dataset.tab;


                    state.category =
                        "전체";

                    state.visibleCount =
                        20;


                    document
                        .querySelectorAll(
                            ".tab-btn"
                        )
                        .forEach(item => {

                            item.classList.toggle(
                                "active",
                                item === button
                            );

                        });


                    renderCategoryFilters();
                    render();
                }
            );

        });
}


/* =========================================================
   날짜 버튼
========================================================= */

function setupDateFilters() {

    dateFiltersEl
        .querySelectorAll(
            "[data-date-filter]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    const value =
                        button.dataset.dateFilter;


                    if (
                        value ===
                        "custom"
                    ) {

                        if (
                            typeof customDateInputEl.showPicker ===
                            "function"
                        ) {

                            customDateInputEl.showPicker();

                        } else {

                            customDateInputEl.click();
                        }


                        return;
                    }


                    state.dateFilter =
                        value;

                    state.selectedDate =
                        null;

                    customDateInputEl.value =
                        "";

                    state.visibleCount =
                        20;


                    renderDateFilters();
                    render();
                }
            );

        });
}


/* =========================================================
   Date Picker
========================================================= */

function setupCustomDatePicker() {

    const today =
        new Date();


    today.setHours(
        0,
        0,
        0,
        0
    );


    const maxDate =
        new Date(today);


    maxDate.setMonth(
        maxDate.getMonth() + 3
    );


    customDateInputEl.min =
        dateToString(today);

    customDateInputEl.max =
        dateToString(maxDate);


    customDateInputEl.addEventListener(
        "change",
        () => {

            if (
                !customDateInputEl.value
            ) {
                return;
            }


            state.dateFilter =
                "custom";

            state.selectedDate =
                customDateInputEl.value;

            state.visibleCount =
                20;


            renderDateFilters();
            render();
        }
    );
}


/* =========================================================
   지역
========================================================= */

function setupRegionFilter() {

    regionSelectEl.addEventListener(
        "change",
        () => {

            state.region =
                regionSelectEl.value;

            state.visibleCount =
                20;


            render();
        }
    );
}


/* =========================================================
   모달 동작
========================================================= */

function setupModal() {

    modalCloseEl.addEventListener(
        "click",
        closeFestivalModal
    );


    eventModalEl.addEventListener(
        "click",
        event => {

            if (
                event.target ===
                eventModalEl
            ) {
                closeFestivalModal();
            }
        }
    );


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape" &&
                eventModalEl.classList.contains(
                    "open"
                )
            ) {
                closeFestivalModal();
            }
        }
    );
}


/* =========================================================
   JSON
========================================================= */

async function loadJson(path) {

    const response =
        await fetch(
            path,
            {
                cache: "no-store",
            }
        );


    if (!response.ok) {

        throw new Error(
            `${path}: HTTP ${response.status}`
        );
    }


    return response.json();
}


async function loadData() {

    resultSummaryEl.textContent =
        "행사를 불러오는 중입니다.";


    try {

        const [
            festivalData,
            cultureData,
        ] = await Promise.all([
            loadJson(
                "./data/events.json"
            ),
            loadJson(
                "./data/culture_events.json"
            ),
        ]);


        festivalEvents =
            Array.isArray(
                festivalData.events
            )
                ? festivalData.events
                : [];


        cultureEvents =
            Array.isArray(
                cultureData.events
            )
                ? cultureData.events
                : [];


        console.log(
            "TourAPI:",
            festivalEvents.length
        );

        console.log(
            "Culture:",
            cultureEvents.length
        );


        render();


    } catch (error) {

        console.error(error);


        resultSummaryEl.textContent =
            "데이터를 불러오지 못했습니다.";


        eventsEl.innerHTML = `
            <div class="empty">

                행사 데이터를 불러오지 못했습니다.
                <br>

                로컬 서버로 실행 중인지 확인해 주세요.

            </div>
        `;


        moreWrapEl.innerHTML =
            "";
    }
}


/* =========================================================
   시작
========================================================= */

setupTabs();
setupDateFilters();
setupCustomDatePicker();
setupRegionFilter();
setupModal();

renderCategoryFilters();
renderDateFilters();

loadData();