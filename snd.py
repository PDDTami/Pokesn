import time """ Sleep 함수 호출"""
import re """ 문자열에서 특정 숫자 뽑기"""
import statistics """ 평균, 중앙값 계산"""
from typing import Any, Dict, List, Optional, Tuple

import request """ HTTP 요청 보낼 라이브러리 """
import streamlit as st """ UI 만들기 """

Base_Web = "https://snkrdunk.com/en"
Base_API = "https://snkrdunk.com/en/v1"


""" SND에서 데이터를 꺼내오는 함수 """
def safe_get(d: Any, path: List[Any], default = None):
  cur = d
  try:
    for p in path:
      cur = cur[p]
    return cur
  except Exception:
    return default


def headers(card_id_for_referer: Optional[int] = None) -> Dict[str, str]:
  referer = f"{Base_Web}/tradingcards/{card_id_for_referer}" if card_id_for_referer else Base_Web
  return {
    "Accept : "application/json",
    "Accept_Language" : "en
