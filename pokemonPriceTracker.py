import streamlit as st
import pandas as pd
from scraper import SnkrdunkScraper
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="SNKRDUNK 포켓몬 카드 시세 조회", page_icon="🃏", layout="wide")

# 스타일 설정
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
    }
    .card-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_stdio=True)

st.title("🃏 SNKRDUNK 포켓몬 카드 시세 분석기")
st.write("SNKRDUNK에서 최근 거래된 포켓몬 카드의 평균 가격을 확인하세요.")

# 세션 상태 초기화
if 'scraper' not in st.session_state:
    st.session_state.scraper = SnkrdunkScraper()

# 검색 영역
with st.container():
    col1, col2 = st.columns([4, 1])
    with col1:
        search_query = st.text_input("카드 이름을 입력하세요 (예: Pikachu, Charizard)", placeholder="Pikachu")
    with col2:
        search_button = st.button("검색")

if search_button or search_query:
    if not search_query:
        st.warning("검색어를 입력해주세요.")
    else:
        with st.spinner('카드를 찾는 중...'):
            results = st.session_state.scraper.search_cards(search_query)
            
        if not results:
            st.error("검색 결과가 없습니다. 다른 키워드로 시도해보세요.")
        else:
            st.subheader(f"🔍 '{search_query}' 검색 결과")
            
            # 결과 표시 (그리드 형태)
            cols = st.columns(3)
            for idx, card in enumerate(results[:9]): # 상위 9개만 표시
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div class="card-container">
                            <img src="{card['thumbnail']}" style="width:100%; border-radius:5px;">
                            <p style="font-weight:bold; margin-top:10px; height: 3em; overflow: hidden;">{card['name']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"시세 분석: {card['id']}", key=f"btn_{card['id']}"):
                            with st.spinner('최근 거래 데이터를 분석 중...'):
                                prices = st.session_state.scraper.get_recent_prices(card['id'])
                                
                                if not prices:
                                    st.warning("최근 거래 내역을 찾을 수 없습니다.")
                                else:
                                    # 통계 계산
                                    avg_price = sum(prices) / len(prices)
                                    max_price = max(prices)
                                    min_price = min(prices)
                                    
                                    st.success(f"✅ 분석 완료: {card['name']}")
                                    
                                    # 지표 표시
                                    m1, m2, m3 = st.columns(3)
                                    m1.metric("평균 거래가", f"US ${avg_price:.2f}")
                                    m2.metric("최고가", f"US ${max_price}")
                                    m3.metric("최저가", f"US ${min_price}")
                                    
                                    # 차트 표시
                                    df = pd.DataFrame({"Price": prices})
                                    fig = px.line(df, y="Price", title="최근 거래 가격 추이 (SOLD)", 
                                                 labels={"index": "거래 순서", "Price": "가격 (USD)"},
                                                 markers=True)
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    st.info(f"총 {len(prices)}건의 최근 거래 데이터를 기반으로 계산되었습니다.")

st.markdown("---")
st.caption("Data provided by SNKRDUNK. This tool is for educational purposes.")

