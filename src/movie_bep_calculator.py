import json
import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# tracker_hub 연동 (사용량 추적 및 예외 처리)
try:
    from tracker_hub import log_app_usage
except ImportError:
    def log_app_usage(app_name, action, details=None):
        pass

def safe_log_usage(action_name: str, details_data: dict = None):
    """사용량 로그 기록 중 오류 발생 시 메인 분석 흐름 차단 방지"""
    try:
        log_app_usage("movie_bep_calculator", action_name, details_data or {})
    except Exception:
        pass

# 페이지 기본 설정
st.set_page_config(
    page_title="영화 BEP 정산 알고리즘 시각화기",
    page_icon="🎬",
    layout="wide"
)

# 52개 대표 한국 영화 데이터베이스 (단위: 억원 / 만명)
MOVIE_PRESETS = [
    {"title": "호프 (HOPE)", "year": 2026, "net_cost": 500, "pa_cost": 100, "reported_bep": 1200, "pre_sales": 300, "note": "해외 선판매 및 OTT 계약으로 극장 BEP 600만으로 조정"},
    {"title": "명량", "year": 2014, "net_cost": 148, "pa_cost": 42, "reported_bep": 600, "pre_sales": 0, "note": "역대 한국 박스오피스 1위"},
    {"title": "극한직업", "year": 2019, "net_cost": 65, "pa_cost": 30, "reported_bep": 250, "pre_sales": 10, "note": "고수익성 코미디 영화"},
    {"title": "신과함께: 죄와 벌", "year": 2017, "net_cost": 200, "pa_cost": 50, "reported_bep": 600, "pre_sales": 50, "note": "1, 2편 동시 제작으로 제작비 절감"},
    {"title": "국제시장", "year": 2014, "net_cost": 140, "pa_cost": 40, "reported_bep": 600, "pre_sales": 10, "note": "휴먼 드라메 상업 영화"},
    {"title": "베테랑", "year": 2015, "net_cost": 60, "pa_cost": 30, "reported_bep": 280, "pre_sales": 15, "note": "액션 범죄 흥행작"},
    {"title": "서울의 봄", "year": 2023, "net_cost": 233, "pa_cost": 37, "reported_bep": 460, "pre_sales": 20, "note": "최근 1,000만 돌파 대표작"},
    {"title": "파묘", "year": 2024, "net_cost": 140, "pa_cost": 35, "reported_bep": 330, "pre_sales": 40, "note": "오컬트 장르 최초 1,000만 돌파"},
    {"title": "범죄도시2", "year": 2022, "net_cost": 130, "pa_cost": 30, "reported_bep": 320, "pre_sales": 30, "note": "팬데믹 이후 첫 1,000만"},
    {"title": "범죄도시3", "year": 2023, "net_cost": 135, "pa_cost": 35, "reported_bep": 180, "pre_sales": 50, "note": "해외 선판매 비중 확대"},
    {"title": "범죄도시4", "year": 2024, "net_cost": 140, "pa_cost": 35, "reported_bep": 350, "pre_sales": 45, "note": "시리즈 연속 흥행"},
    {"title": "기생충", "year": 2019, "net_cost": 135, "pa_cost": 40, "reported_bep": 370, "pre_sales": 120, "note": "칸 영화제 및 아카데미 수상작"},
    {"title": "도둑들", "year": 2012, "net_cost": 140, "pa_cost": 40, "reported_bep": 450, "pre_sales": 20, "note": "케이퍼 무비 흥행작"},
    {"title": "7번방의 선물", "year": 2013, "net_cost": 35, "pa_cost": 23, "reported_bep": 170, "pre_sales": 5, "note": "중저예산 고수익 영화"},
    {"title": "암살", "year": 2015, "net_cost": 180, "pa_cost": 45, "reported_bep": 700, "pre_sales": 30, "note": "시대극 블록버스터"},
    {"title": "엑시트", "year": 2019, "net_cost": 95, "pa_cost": 35, "reported_bep": 350, "pre_sales": 15, "note": "재난 코미디 흥행작"},
    {"title": "밀수", "year": 2023, "net_cost": 175, "pa_cost": 35, "reported_bep": 330, "pre_sales": 35, "note": "해양 액션 블록버스터"},
    {"title": "한산: 용의 출현", "year": 2022, "net_cost": 300, "pa_cost": 50, "reported_bep": 600, "pre_sales": 40, "note": "이순신 3부작 중 2편"},
    {"title": "노량: 죽음의 바다", "year": 2023, "net_cost": 312, "pa_cost": 50, "reported_bep": 720, "pre_sales": 50, "note": "이순신 3부작 완결편"},
    {"title": "외계+인 1부", "year": 2022, "net_cost": 330, "pa_cost": 70, "reported_bep": 730, "pre_sales": 60, "note": "SF 대작 프로젝트 1부"},
    {"title": "외계+인 2부", "year": 2024, "net_cost": 330, "pa_cost": 40, "reported_bep": 370, "pre_sales": 70, "note": "SF 대작 프로젝트 2부"},
    {"title": "비상선언", "year": 2022, "net_cost": 260, "pa_cost": 40, "reported_bep": 500, "pre_sales": 80, "note": "항공 재난 영화"},
    {"title": "영웅", "year": 2022, "net_cost": 200, "pa_cost": 40, "reported_bep": 350, "pre_sales": 30, "note": "뮤지컬 영화 대작"},
    {"title": "콘크리트 유토피아", "year": 2023, "net_cost": 200, "pa_cost": 40, "reported_bep": 380, "pre_sales": 45, "note": "포스트 아포칼립스 재난물"},
    {"title": "헌트", "year": 2022, "net_cost": 200, "pa_cost": 35, "reported_bep": 420, "pre_sales": 50, "note": "첩보 액션 영화"},
    {"title": "헤어질 결심", "year": 2022, "net_cost": 135, "pa_cost": 30, "reported_bep": 120, "pre_sales": 90, "note": "해외 판권 선판매 비중 우수"},
    {"title": "마녀(魔女) Pt.1", "year": 2018, "net_cost": 65, "pa_cost": 25, "reported_bep": 230, "pre_sales": 10, "note": "신인 주연 미스터리 액션"},
    {"title": "마녀2", "year": 2022, "net_cost": 90, "pa_cost": 25, "reported_bep": 150, "pre_sales": 30, "note": "후속작 선판매 호조"},
    {"title": "반도", "year": 2020, "net_cost": 190, "pa_cost": 40, "reported_bep": 250, "pre_sales": 110, "note": "부산행 세계관 선판매 성과"},
    {"title": "사바하", "year": 2019, "net_cost": 80, "pa_cost": 30, "reported_bep": 250, "pre_sales": 15, "note": "미스터리 오컬트"},
    {"title": "검은 사제들", "year": 2015, "net_cost": 67, "pa_cost": 25, "reported_bep": 200, "pre_sales": 10, "note": "한국형 퇴마물 흥행"},
    {"title": "아가씨", "year": 2016, "net_cost": 150, "pa_cost": 35, "reported_bep": 300, "pre_sales": 70, "note": "해외 175개국 선판매"},
    {"title": "내부자들", "year": 2015, "net_cost": 75, "pa_cost": 30, "reported_bep": 350, "pre_sales": 10, "note": "청소년 관람불가 흥행작"},
    {"title": "곡성", "year": 2016, "net_cost": 100, "pa_cost": 30, "reported_bep": 300, "pre_sales": 25, "note": "칸 영화제 초청작"},
    {"title": "택시운전사", "year": 2017, "net_cost": 150, "pa_cost": 40, "reported_bep": 450, "pre_sales": 30, "note": "휴먼 실화 1,000만"},
    {"title": "부산행", "year": 2016, "net_cost": 115, "pa_cost": 35, "reported_bep": 340, "pre_sales": 60, "note": "한국형 좀비 블록버스터"},
    {"title": "공작", "year": 2018, "net_cost": 165, "pa_cost": 35, "reported_bep": 470, "pre_sales": 30, "note": "실화 바탕 첩보물"},
    {"title": "백두산", "year": 2019, "net_cost": 260, "pa_cost": 40, "reported_bep": 730, "pre_sales": 50, "note": "재난 블록버스터"},
    {"title": "드림", "year": 2023, "net_cost": 139, "pa_cost": 30, "reported_bep": 220, "pre_sales": 35, "note": "해외 로케이션 스포츠물"},
    {"title": "거미집", "year": 2023, "net_cost": 96, "pa_cost": 25, "reported_bep": 200, "pre_sales": 40, "note": "칸 초청 드라마"},
    {"title": "1947 보스톤", "year": 2023, "net_cost": 210, "pa_cost": 35, "reported_bep": 450, "pre_sales": 30, "note": "스포츠 드라마"},
    {"title": "천박사 퇴마 연구소", "year": 2023, "net_cost": 113, "pa_cost": 27, "reported_bep": 240, "pre_sales": 25, "note": "판타지 오컬트"},
    {"title": "타겟", "year": 2023, "net_cost": 45, "pa_cost": 20, "reported_bep": 100, "pre_sales": 10, "note": "스릴러 중저예산"},
    {"title": "잠", "year": 2023, "net_cost": 50, "pa_cost": 20, "reported_bep": 80, "pre_sales": 20, "note": "저예산 미스터리 흥행"},
    {"title": "시민덕희", "year": 2024, "net_cost": 65, "pa_cost": 20, "reported_bep": 160, "pre_sales": 15, "note": "실화 기반 추적극"},
    {"title": "댓글부대", "year": 2024, "net_cost": 80, "pa_cost": 20, "reported_bep": 195, "pre_sales": 15, "note": "범죄 스릴러"},
    {"title": "리볼버", "year": 2024, "net_cost": 100, "pa_cost": 25, "reported_bep": 140, "pre_sales": 40, "note": "하드보일드 액션"},
    {"title": "탈주", "year": 2024, "net_cost": 85, "pa_cost": 25, "reported_bep": 200, "pre_sales": 20, "note": "추격 액션"},
    {"title": "베테랑2", "year": 2024, "net_cost": 130, "pa_cost": 35, "reported_bep": 350, "pre_sales": 60, "note": "속편 액션 흥행작"},
    {"title": "하이재킹", "year": 2024, "net_cost": 140, "pa_cost": 30, "reported_bep": 230, "pre_sales": 35, "note": "실화 바탕 재난극"},
    {"title": "크로스", "year": 2024, "net_cost": 100, "pa_cost": 10, "reported_bep": 0, "pre_sales": 110, "note": "OTT 직접 직행 사례"},
    {"title": "스위치", "year": 2023, "net_cost": 60, "pa_cost": 20, "reported_bep": 140, "pre_sales": 10, "note": "휴먼 코미디"}
]

# 국가별 정산 알고리즘 계산 함수
def calculate_bep_by_region(total_budget_eon, ticket_price=11000, pre_sales_eon=0):
    """
    total_budget_eon: 총제작비(억원)
    ticket_price: 티켓 단가(원)
    pre_sales_eon: 선판매/부대수익(억원)
    """
    # 회수 필요 금액(억원)
    net_required_eon = max(0, total_budget_eon - pre_sales_eon)
    
    # [수정 전] net_required_krw = net_required_eon * 100,000,000 (튜플로 인식됨)
    # [수정 후] 쉼표 대신 언더바(_)를 사용하여 숫자로 정상 인식하도록 변경합니다.
    net_required_krw = net_required_eon * 100_000_000
    
    # 1. 한국 정산 모델
    net_ticket_krw = ticket_price * 0.87
    distributor_gross = net_ticket_krw * 0.5
    korea_producer_per_ticket = distributor_gross * 0.9
    korea_bep_audience = net_required_krw / korea_producer_per_ticket if korea_producer_per_ticket > 0 else 0
    
    # 2. 할리우드 모델
    hollywood_studio_share_ratio = 0.45
    hollywood_producer_per_ticket = ticket_price * hollywood_studio_share_ratio
    hollywood_bep_audience = net_required_krw / hollywood_producer_per_ticket if hollywood_producer_per_ticket > 0 else 0
    
    # 3. 유럽 모델
    europe_grant_ratio = 0.25
    europe_net_required_krw = net_required_krw * (1 - europe_grant_ratio)
    europe_producer_share_ratio = 0.40
    europe_producer_per_ticket = ticket_price * europe_producer_share_ratio
    europe_bep_audience = europe_net_required_krw / europe_producer_per_ticket if europe_producer_per_ticket > 0 else 0
    
    return {
        "korea_bep": round(korea_bep_audience / 10000, 1),
        "hollywood_bep": round(hollywood_bep_audience / 10000, 1),
        "europe_bep": round(europe_bep_audience / 10000, 1),
        "korea_per_ticket": round(korea_producer_per_ticket),
        "hollywood_per_ticket": round(hollywood_producer_per_ticket),
        "europe_per_ticket": round(europe_producer_per_ticket)
    }

# 앱 메인 헤더
st.title("🎬 영화 '호프(HOPE)' 손익분기점 번복 및 글로벌 정산 알고리즘 시각화")
st.caption("한국·할리우드·유럽의 극장 수익 정산 공식을 비교 분석합니다.")

# 사이드바 설정 및 프리셋 선택
st.sidebar.header("⚙️ 분석 설정 및 데이터베이스")
selected_movie_name = st.sidebar.selectbox(
    "내장 영화 프리셋 선택 (52개)",
    options=[m["title"] for m in MOVIE_PRESETS],
    index=0
)

# 선택된 영화 데이터 추출
selected_movie = next(m for m in MOVIE_PRESETS if m["title"] == selected_movie_name)

st.sidebar.markdown("---")
st.sidebar.subheader("✏️ 사용자 지정 계산 파라미터")
custom_net_cost = st.sidebar.number_input("순제작비 (억원)", value=int(selected_movie["net_cost"]), step=10)
custom_pa_cost = st.sidebar.number_input("마케팅/P&A비 (억원)", value=int(selected_movie["pa_cost"]), step=5)
custom_pre_sales = st.sidebar.number_input("OTT/해외 선판매 수익 (억원)", value=int(selected_movie["pre_sales"]), step=10)
ticket_price = st.sidebar.number_input("평균 티켓 가격 (원)", value=11000, step=500)

total_budget = custom_net_cost + custom_pa_cost

# KOBIS API 연동 구조 예시 인터페이스
st.sidebar.markdown("---")
st.sidebar.subheader("🌐 KOBIS Open API 연동")
kobis_api_key = st.sidebar.text_input("KOBIS API 키 입력", type="password")
if st.sidebar.button("KOBIS 데이터 동기화"):
    if kobis_api_key:
        try:
            # API 호출 예시 구문
            url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={kobis_api_key}&targetDt=20260728"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                st.sidebar.success("KOBIS API 연동 성공")
                safe_log_usage("kobis_api_sync_success", {"status": "ok"})
            else:
                st.sidebar.error("API 응답 오류 발생")
        except Exception as e:
            st.sidebar.error(f"통신 실패: {str(e)}")
            safe_log_usage("kobis_api_sync_failed", {"error": str(e)})
    else:
        st.sidebar.warning("API 키를 입력하세요.")

# 사용량 추적 로그
safe_log_usage("view_movie_bep", {"movie": selected_movie_name, "total_budget": total_budget})

# 탭 구성
tab1, tab2, tab3, tab4 = st.tabs([
    "🔥 '호프' BEP 번복 분석", 
    "🌍 글로벌 정산 알고리즘 비교", 
    "📊 52개 영화 DB 탐색기", 
    "🧮 시뮬레이션 계산기"
])

# 탭 1: '호프' BEP 번복 구조 분석
with tab1:
    st.subheader("영화 '호프(HOPE)' 손익분기점 번복 해프닝의 진실")
    st.write(
        "제작비 600억 원 규모의 대작 '호프'는 초기 언론 보도에서 손익분기점이 **1,200만 명**으로 발표되었으나, "
        "이후 **600만 명** 안팎으로 대폭 수정 발표되었습니다. 이는 단순한 언론의 오보나 분식회계가 아닌, "
        "**글로벌 선판매 및 부대수익 정산 방식**이 반영된 결과입니다."
    )
    
    col1, col2 = st.columns(2)
    
    # 극장 매출로만 회수할 때 vs 선판매 반영 후 회수할 때
    calc_no_presale = calculate_bep_by_region(total_budget, ticket_price, pre_sales_eon=0)
    calc_with_presale = calculate_bep_by_region(total_budget, ticket_price, pre_sales_eon=custom_pre_sales)
    
    with col1:
        st.metric(
            label="순수 극장 매출만으로 회수 시 BEP", 
            value=f"{calc_no_presale['korea_bep']} 만명",
            delta="선판매 반영 전"
        )
    with col2:
        st.metric(
            label="OTT/해외 선판매(300억) 반영 후 실제 BEP", 
            value=f"{calc_with_presale['korea_bep']} 만명",
            delta=f"-{round(calc_no_presale['korea_bep'] - calc_with_presale['korea_bep'], 1)} 만명 감축",
            delta_color="inverse"
        )
        
    # 비교 시각화 차트 (범례 글자 색상 및 가독성 개선)
    fig_hope = go.Figure(data=[
        go.Bar(name='선판매 반영 전 필요 관객수', x=['한국 기준 BEP'], y=[calc_no_presale['korea_bep']], marker_color='#EF553B'),
        go.Bar(name='선판매 반영 후 실제 필요 관객수', x=['한국 기준 BEP'], y=[calc_with_presale['korea_bep']], marker_color='#636EFA')
    ])
    fig_hope.update_layout(
        barmode='group', 
        title="선판매 여부에 따른 '호프' 손익분기점 변화 (단위: 만명)",
        legend=dict(
            font=dict(color="#111111", size=13, family="Malgun Gothic"),  # 선명한 검은색 글씨
            bgcolor="rgba(255, 255, 255, 0.95)",                         # 불투명한 흰색 배경
            bordercolor="#CCCCCC",                                        # 깔끔한 테두리
            borderwidth=1
        )
    )
    st.plotly_chart(fig_hope, use_container_width=True)

# 탭 2: 글로벌 정산 알고리즘 비교
with tab2:
    st.subheader("한국 vs 할리우드 vs 유럽 극장 정산 알고리즘")
    st.write("동일한 티켓 가격(11,000원) 결제 시 제작사/투자사로 돌아오는 최종 금액을 비교합니다.")
    
    res = calculate_bep_by_region(total_budget, ticket_price, custom_pre_sales)
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("한국 제작사 수령액 (장당)", f"{res['korea_per_ticket']:,} 원", "순매출 87% 중 5:5 정산")
    col_b.metric("할리우드 제작사 수령액 (장당)", f"{res['hollywood_per_ticket']:,} 원", "글로벌 평균 45% 정산")
    col_c.metric("유럽 제작사 수령액 (장당)", f"{res['europe_per_ticket']:,} 원", "보조금 25% + 40% 정산")
    
    # 10,000원 티켓 분해 파이차트 (한국 기준)
    pie_labels = ['부가가치세 (10%)', '영화발전기금 (3%)', '극장 수수료 (43.5%)', '배급 수수료 (4.35%)', '제작사/투자사 수수료 (39.15%)']
    pie_values = [1000, 300, 4350, 435, 3915]
    
    fig_pie = px.pie(values=pie_values, names=pie_labels, title="한국 영화 티켓 10,000원 한 판의 분배 구조", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

# 탭 3: 52개 영화 DB 탐색기
with tab3:
    st.subheader("52개 대표 한국 영화 제작비 및 BEP 데이터베이스")
    df_movies = pd.DataFrame(MOVIE_PRESETS)
    
    # 검색 필터
    search_term = st.text_input("영화 제목 검색", "")
    if search_term:
        df_movies = df_movies[df_movies["title"].str.contains(search_term)]
        
    st.dataframe(
        df_movies,
        column_config={
            "title": "영화 제목",
            "year": "개봉 연도",
            "net_cost": "순제작비(억)",
            "pa_cost": "P&A비(억)",
            "reported_bep": "발표 BEP(만명)",
            "pre_sales": "선판매/부대수익(억)",
            "note": "비고"
        },
        use_container_width=True
    )

# 탭 4: 실시간 BEP 계산기
with tab4:
    st.subheader("실시간 커스텀 BEP 및 정산 산출기")
    st.write("영화의 예산과 조건이 손익분기점에 미치는 영향을 직접 시뮬레이션할 수 있습니다.")

    # 세션 스테이트 초기화 (기본값으로 영화 '호프' 데이터 설정)
    if "t4_title" not in st.session_state:
        st.session_state["t4_title"] = "호프 (HOPE)"
    if "t4_net" not in st.session_state:
        st.session_state["t4_net"] = 500
    if "t4_pa" not in st.session_state:
        st.session_state["t4_pa"] = 100
    if "t4_pre" not in st.session_state:
        st.session_state["t4_pre"] = 300
    if "t4_price" not in st.session_state:
        st.session_state["t4_price"] = 11000
    if "t4_override" not in st.session_state:
        st.session_state["t4_override"] = 0

    # 예시 버튼 및 상단 안내문
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.info("💡 입력란에 어떤 수치를 넣어야 할지 모를 때 아래 버튼을 누르면 '호프'의 실제 예시 데이터로 초기화됩니다.")
    with col_btn:
        if st.button("🎬 영화 '호프' 예시 채우기", use_container_width=True):
            st.session_state["t4_title"] = "호프 (HOPE)"
            st.session_state["t4_net"] = 500
            st.session_state["t4_pa"] = 100
            st.session_state["t4_pre"] = 300
            st.session_state["t4_price"] = 11000
            st.session_state["t4_override"] = 0
            st.rerun()

    # 상세 설명이 포함된 입력 입력란
    col_in1, col_in2 = st.columns(2)

    with col_in1:
        custom_movie_title = st.text_input(
            "영화 제목 입력",
            key="t4_title",
            help="분석하고자 하는 영화의 이름을 입력합니다. (예: 호프, 서울의 봄)"
        )
        input_net_cost = st.number_input(
            "순제작비 (억원)",
            step=10,
            key="t4_net",
            help="촬영, 세트, 배우 출연료 등 영화 순수 제작에 들어간 돈입니다. (예: 호프는 500억원)"
        )
        input_pa_cost = st.number_input(
            "마케팅 / P&A비 (억원)",
            step=5,
            key="t4_pa",
            help="홍보, 광고, 포스터 제작, 배급에 쓰인 비용(Print & Advertising)입니다. (예: 호프는 100억원)"
        )

    with col_in2:
        input_pre_sales = st.number_input(
            "OTT / 해외 선판매 수익 (억원)",
            step=5,
            key="t4_pre",
            help="개봉 전 OTT(넷플릭스 등) 판권 판매나 해외 선판매로 이미 확보한 확실한 사전 수익입니다. 이 금액이 클수록 극장에서 회수해야 할 손익분기 관객수가 대폭 낮아집니다."
        )
        input_ticket_price = st.number_input(
            "평균 티켓 가격 (원)",
            step=500,
            key="t4_price",
            help="관객 1명이 지불하는 평균 관람료 단가입니다. 기본 11,000원이 적용됩니다."
        )
        override_producer_share = st.number_input(
            "티켓 당 제작사 정산금 직접 지정 (원)",
            step=100,
            key="t4_override",
            help="특약이나 수입 영화처럼 장당 정산금이 고정된 경우 입력합니다. 0을 넣으면 한국 표준 공식(티켓 11,000원 기준 4,306원)이 자동 적용됩니다."
        )

    input_total_budget = input_net_cost + input_pa_cost

    # 기본 계산 수행
    base_calc_res = calculate_bep_by_region(input_total_budget, input_ticket_price, input_pre_sales)

    if override_producer_share > 0:
        net_req_krw = max(0, input_total_budget - input_pre_sales) * 100_000_000
        custom_bep_audience = net_req_krw / override_producer_share if override_producer_share > 0 else 0
        korea_per_ticket_val = override_producer_share
        korea_bep_val = round(custom_bep_audience / 10000, 1)
    else:
        korea_per_ticket_val = base_calc_res["korea_per_ticket"]
        korea_bep_val = base_calc_res["korea_bep"]

    # 결과 표 데이터 구성
    df_custom_res = pd.DataFrame({
        "국가/지역": ["한국 (사용자 지정 반영)", "할리우드 (Standard)", "유럽 (Standard)"],
        "티켓 당 제작사 정산금 (원)": [korea_per_ticket_val, base_calc_res["hollywood_per_ticket"], base_calc_res["europe_per_ticket"]],
        "필요 손익분기점 관객수 (만명)": [korea_bep_val, base_calc_res["hollywood_bep"], base_calc_res["europe_bep"]]
    })

    st.markdown(f"### 📋 [{custom_movie_title}] 손익분기점 산출 결과 (총 예산 {input_total_budget}억원)")

    # 영화 호프 분석 조건인 경우 직관적 안내 상자 출력
    if custom_movie_title == "호프 (HOPE)" and input_pre_sales == 300:
        st.success("✨ '호프' 선판매 반영 분석: 총 예산 600억원 중 선판매 300억원을 제외한 남은 300억원만 극장에서 회수하면 되므로, 필요 관객수가 약 696만명대로 대폭 낮아집니다.")
    elif custom_movie_title == "호프 (HOPE)" and input_pre_sales == 0:
        st.warning("⚠️ '호프' 선판매 미반영 시: 선판매 수익이 0원이라고 가정하면 600억원을 오직 극장 수수료로만 회수해야 하므로 필요 관객수가 약 1,393만명으로 늘어납니다.")

    st.table(df_custom_res)

    # 시각화 그래프
    fig_custom_bar = px.bar(
        df_custom_res,
        x="국가/지역",
        y="필요 손익분기점 관객수 (만명)",
        color="국가/지역",
        title=f"'{custom_movie_title}' 산출 조건별 필요 관객수 비교"
    )
    st.plotly_chart(fig_custom_bar, use_container_width=True)

    # 트래커 기록
    safe_log_usage("movie_bep_calculator", {
        "title": custom_movie_title,
        "total_budget": input_total_budget,
        "override_share": override_producer_share
    })