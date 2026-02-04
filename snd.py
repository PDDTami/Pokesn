import streamlit as st
import requests
from typing import Any, Dict, List, Optional, Tuple
import json


# -----------------------------
# 0) 공통 HTTP 유틸
# -----------------------------
def get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """
    SNKRDUNK에 GET 요청을 보내고 JSON으로 응답을 파싱해서 반환한다.
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://snkrdunk.com/",
    }

    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# -----------------------------
# 1) SNKRDUNK API - 검색 엔드포인트 (개선된 버전)
# -----------------------------
def search_trading_cards(keyword: str, page: int = 1, per_page: int = 20) -> Any:
    """
    포켓몬 카드를 검색하는 API
    실제 엔드포인트는 다음 중 하나일 가능성이 높음:
    1. /en/v1/trading-cards (with query params)
    2. /en/v1/search/trading-cards
    3. /en/v1/products (with category filter)
    """
    # 여러 가능한 엔드포인트 시도
    endpoints = [
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "keyword": keyword,
                "page": page,
                "perPage": per_page,
                "sortType": "popular"
            }
        },
        {
            "url": "https://snkrdunk.com/en/v1/search",
            "params": {
                "q": keyword,
                "type": "trading-cards",
                "page": page,
                "perPage": per_page
            }
        },
        {
            "url": "https://snkrdunk.com/en/v1/products/search",
            "params": {
                "keyword": keyword,
                "category": "trading-cards",
                "page": page,
                "limit": per_page
            }
        }
    ]
    
    errors = []
    for config in endpoints:
        try:
            result = get_json(config["url"], config["params"])
            # 성공하면 결과 반환
            return {"success": True, "data": result, "endpoint": config["url"]}
        except Exception as e:
            errors.append({
                "url": config["url"],
                "params": config["params"],
                "error": str(e)
            })
            continue
    
    # 모든 엔드포인트 실패
    return {"success": False, "errors": errors}


# -----------------------------
# 2) SNKRDUNK API - 기존 확정된 엔드포인트
# -----------------------------
def get_used_listings(card_id: str, per_page: int = 16, page: int = 1) -> Any:
    """
    카드ID 기준으로 used-listings(중고 리스팅/가격 관련) JSON을 가져온다.
    """
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}/used-listings"
    params = {
        "perPage": per_page,
        "page": page,
        "sortType": "latest",
        "isOnlyOnSale": "false",
    }
    return get_json(url, params=params)


def get_related_single_cards(card_id: str, per_page: int = 10, page: int = 1) -> Any:
    """
    카드ID 기준으로 related-single-cards(유사 상품) JSON을 가져온다.
    """
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}/related-single-cards"
    params = {
        "perPage": per_page,
        "page": page,
    }
    return get_json(url, params=params)


def get_card_detail(card_id: str) -> Any:
    """
    카드 상세 정보 가져오기
    """
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}"
    return get_json(url)


# -----------------------------
# 3) 검색 결과에서 카드 정보 추출
# -----------------------------
def extract_cards_from_response(response_data: Any) -> List[Dict[str, Any]]:
    """
    검색 응답에서 카드 정보 추출
    """
    cards = []
    
    # 다양한 응답 구조 처리
    if isinstance(response_data, dict):
        # 일반적인 패턴들
        for key in ["items", "list", "data", "results", "cards", "products"]:
            if key in response_data and isinstance(response_data[key], list):
                return response_data[key]
        
        # 중첩된 구조
        if "data" in response_data and isinstance(response_data["data"], dict):
            for key in ["items", "list", "results", "cards"]:
                if key in response_data["data"] and isinstance(response_data["data"][key], list):
                    return response_data["data"][key]
    
    return cards


def extract_card_id(card_item: Dict[str, Any]) -> Optional[str]:
    """
    카드 아이템에서 ID 추출
    """
    # 가능한 ID 필드명들
    id_fields = ["id", "cardId", "tradingCardId", "productId", "item_id"]
    
    for field in id_fields:
        if field in card_item:
            return str(card_item[field])
    
    return None


# -----------------------------
# 4) 가격 정보 추출
# -----------------------------
def extract_price_info(data: Any) -> Dict[str, Any]:
    """
    JSON에서 가격 정보 추출
    """
    price_info = {
        "lowest_price": None,
        "highest_price": None,
        "average_price": None,
        "all_prices": []
    }
    
    def walk(obj):
        if isinstance(obj, dict):
            # 가격 관련 키 찾기
            for key, value in obj.items():
                key_lower = key.lower()
                if any(price_key in key_lower for price_key in ["price", "amount", "value"]):
                    if isinstance(value, (int, float)) and value > 0:
                        price_info["all_prices"].append(float(value))
                    elif isinstance(value, str):
                        try:
                            price_val = float(value.replace(",", "").replace("¥", "").replace("$", ""))
                            if price_val > 0:
                                price_info["all_prices"].append(price_val)
                        except:
                            pass
            
            for value in obj.values():
                walk(value)
        
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    
    walk(data)
    
    if price_info["all_prices"]:
        price_info["lowest_price"] = min(price_info["all_prices"])
        price_info["highest_price"] = max(price_info["all_prices"])
        price_info["average_price"] = sum(price_info["all_prices"]) / len(price_info["all_prices"])
    
    return price_info


# -----------------------------
# 5) Streamlit UI
# -----------------------------
st.set_page_config(page_title="SNKRDUNK 포켓몬 카드 검색", layout="wide")

st.title("🃏 SNKRDUNK 포켓몬 카드 검색기")
st.markdown("### SNKRDUNK에서 포켓몬 카드를 검색하고 가격 정보를 확인하세요")

# 사이드바
with st.sidebar:
    st.header("🔍 검색 옵션")
    
    search_mode = st.radio(
        "검색 방법",
        ["키워드 검색", "Card ID 직접 입력"],
        help="키워드로 검색하거나, 알고 있는 Card ID를 직접 입력할 수 있습니다"
    )
    
    st.divider()
    
    if search_mode == "키워드 검색":
        year = st.text_input("연도", value="2023", help="예: 2023, 2024")
        card_name = st.text_input("카드 이름", value="Pikachu", help="예: Pikachu, Charizard")
        card_number = st.text_input("카드 번호", value="025", help="예: 025, 098")
        
        # 키워드 조합
        keyword = f"{year} {card_name} {card_number}".strip()
        st.info(f"검색어: {keyword}")
    else:
        card_id = st.text_input("Card ID", value="135232", help="SNKRDUNK의 카드 ID")
    
    st.divider()
    
    # 고급 옵션
    with st.expander("⚙️ 고급 옵션"):
        per_page = st.slider("결과 수", 5, 50, 20)
        show_raw_json = st.checkbox("Raw JSON 표시", value=False)
    
    search_button = st.button("🔍 검색 시작", type="primary", use_container_width=True)

# 메인 컨텐츠
if search_button:
    if search_mode == "키워드 검색":
        with st.spinner(f"'{keyword}' 검색 중..."):
            # 검색 API 호출
            search_result = search_trading_cards(keyword, per_page=per_page)
            
            if not search_result["success"]:
                st.error("❌ 검색 실패 - 모든 API 엔드포인트 시도 실패")
                
                with st.expander("🔧 디버그 정보 (개발자용)"):
                    st.json(search_result["errors"])
                    st.markdown("""
                    **해결 방법:**
                    1. 브라우저에서 SNKRDUNK 사이트 방문
                    2. 개발자도구(F12) → Network 탭 열기
                    3. 카드 검색 수행
                    4. XHR/Fetch 요청 중 'trading-cards' 또는 'search' 관련 요청 찾기
                    5. 실제 엔드포인트 URL과 파라미터 확인
                    """)
                st.stop()
            
            st.success(f"✅ 검색 성공! (엔드포인트: {search_result['endpoint']})")
            
            # 카드 목록 추출
            cards = extract_cards_from_response(search_result["data"])
            
            if not cards:
                st.warning("검색 결과가 없습니다.")
                if show_raw_json:
                    st.json(search_result["data"])
                st.stop()
            
            st.info(f"총 {len(cards)}개의 카드를 찾았습니다")
            
            # 카드 목록 표시
            st.subheader("📋 검색 결과")
            
            for idx, card in enumerate(cards[:10], 1):  # 최대 10개만 표시
                with st.expander(f"카드 #{idx} - {card.get('name', '이름 없음')}"):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # 이미지가 있으면 표시
                        if "imageUrl" in card or "image" in card or "thumbnailUrl" in card:
                            img_url = card.get("imageUrl") or card.get("image") or card.get("thumbnailUrl")
                            if img_url:
                                st.image(img_url, width=200)
                    
                    with col2:
                        # 카드 정보
                        st.markdown(f"**카드명:** {card.get('name', 'N/A')}")
                        st.markdown(f"**번호:** {card.get('number', 'N/A')}")
                        st.markdown(f"**세트:** {card.get('setName', card.get('series', 'N/A'))}")
                        
                        # Card ID 추출
                        extracted_id = extract_card_id(card)
                        if extracted_id:
                            st.markdown(f"**Card ID:** `{extracted_id}`")
                            
                            if st.button(f"상세 정보 보기", key=f"detail_{idx}"):
                                st.session_state['selected_card_id'] = extracted_id
                                st.rerun()
                    
                    if show_raw_json:
                        st.json(card)
            
            # Raw JSON 표시 (옵션)
            if show_raw_json:
                with st.expander("🔍 전체 응답 JSON"):
                    st.json(search_result["data"])
    
    else:  # Card ID 직접 입력
        st.session_state['selected_card_id'] = card_id

# 선택된 카드 상세 정보 표시
if 'selected_card_id' in st.session_state:
    selected_id = st.session_state['selected_card_id']
    
    st.divider()
    st.header(f"📊 카드 상세 정보 (ID: {selected_id})")
    
    try:
        tab1, tab2, tab3 = st.tabs(["💰 가격 정보", "🔗 관련 카드", "📝 카드 상세"])
        
        with tab1:
            with st.spinner("가격 정보 로딩 중..."):
                used_data = get_used_listings(selected_id)
                price_info = extract_price_info(used_data)
                
                if price_info["all_prices"]:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💵 최저가", f"¥{price_info['lowest_price']:,.0f}")
                    col2.metric("💵 최고가", f"¥{price_info['highest_price']:,.0f}")
                    col3.metric("💵 평균가", f"¥{price_info['average_price']:,.0f}")
                    
                    # 가격 분포 차트
                    if len(price_info["all_prices"]) > 1:
                        st.subheader("가격 분포")
                        st.bar_chart(price_info["all_prices"])
                else:
                    st.info("가격 정보를 찾을 수 없습니다")
                
                if show_raw_json:
                    with st.expander("Raw JSON - Used Listings"):
                        st.json(used_data)
        
        with tab2:
            with st.spinner("관련 카드 로딩 중..."):
                related_data = get_related_single_cards(selected_id)
                related_cards = extract_cards_from_response(related_data)
                
                if related_cards:
                    st.subheader(f"관련 카드 ({len(related_cards)}개)")
                    
                    # 그리드 형식으로 표시
                    cols = st.columns(3)
                    for idx, card in enumerate(related_cards[:9]):
                        with cols[idx % 3]:
                            st.markdown(f"**{card.get('name', 'N/A')}**")
                            if "imageUrl" in card or "image" in card:
                                img_url = card.get("imageUrl") or card.get("image")
                                if img_url:
                                    st.image(img_url, width=150)
                else:
                    st.info("관련 카드가 없습니다")
                
                if show_raw_json:
                    with st.expander("Raw JSON - Related Cards"):
                        st.json(related_data)
        
        with tab3:
            with st.spinner("카드 상세 정보 로딩 중..."):
                try:
                    detail_data = get_card_detail(selected_id)
                    st.json(detail_data)
                except Exception as e:
                    st.warning(f"상세 정보를 가져올 수 없습니다: {str(e)}")
    
    except requests.HTTPError as e:
        st.error(f"❌ HTTP 에러: {e}")
        st.info("Card ID가 올바른지 확인해주세요")
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>💡 <b>사용 팁:</b> 검색이 작동하지 않으면 Card ID 직접 입력 모드를 사용해보세요</p>
    <p>🔧 개발 중인 도구입니다. 피드백은 환영합니다!</p>
</div>
""", unsafe_allow_html=True)
