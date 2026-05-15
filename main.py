# AI Travel Language Tutor — Gemini 무료 API 버전
# 수정사항:
#   - Gemini 무료 API 유지 (무료 티어: 분당 15회, 일 1500회)
#   - 429 오류 시 명확한 안내 메시지 + 자동 fallback
#   - gTTS → Web Speech API (브라우저 내장, 네트워크 불필요)
#   - 단어 깜빡이 fallback 데이터 추가 (API 없이도 동작)

import streamlit as st
import os
import random
import requests
import json

# ── 상수 ──────────────────────────────────────────────────────────
LANGUAGES: dict[str, dict] = {
    "japanese": {"name": "일본어", "emoji": "🇯🇵", "tts": "ja-JP", "gemini": "Japanese"},
    "english":  {"name": "영어",   "emoji": "🇺🇸", "tts": "en-US", "gemini": "English"},
}

CATEGORIES: list[dict] = [
    {"name": "기본 인사",    "icon": "👋", "en": "Basic Greetings"},
    {"name": "공항/교통",    "icon": "✈️", "en": "Airport & Transportation"},
    {"name": "호텔 체크인",  "icon": "🏨", "en": "Hotel Check-in/Check-out"},
    {"name": "음식점/주문",  "icon": "🍽️", "en": "Restaurant & Ordering"},
    {"name": "쇼핑/결제",    "icon": "🛍️", "en": "Shopping & Payment"},
    {"name": "길 묻기",      "icon": "🧭", "en": "Asking for Directions"},
    {"name": "긴급 상황",    "icon": "🚨", "en": "Emergency"},
    {"name": "숙소 관련",    "icon": "🛏️", "en": "Accommodation"},
    {"name": "관광/활동",    "icon": "🎯", "en": "Sightseeing & Activities"},
]

FALLBACK_CARDS: dict[str, list] = {
    "japanese": [
        ("こんにちは",           "안녕하세요",          "곤니치와"),
        ("ありがとうございます",  "감사합니다",          "아리가토고자이마스"),
        ("すみません",           "실례합니다",          "스미마센"),
        ("どこですか？",          "어디에 있나요?",      "도코 데스카"),
        ("いくらですか？",        "얼마인가요?",         "이쿠라 데스카"),
        ("お願いします",         "부탁합니다",          "오네가이시마스"),
        ("はい",                 "네",                  "하이"),
        ("いいえ",               "아니요",              "이이에"),
        ("わかりません",         "모르겠습니다",        "와카리마센"),
        ("助けてください",       "도와주세요",          "타스케테 구다사이"),
        ("トイレはどこですか",   "화장실이 어디인가요", "토이레와 도코 데스카"),
        ("おいしい",             "맛있다",              "오이시이"),
        ("ホテルまでお願いします","호텔까지 부탁합니다","호테루마데 오네가이시마스"),
        ("チェックインします",   "체크인합니다",        "체쿠인시마스"),
        ("パスポートを見せて",   "여권을 보여주세요",   "파스포토오 미세테"),
    ],
    "english": [
        ("Hello",                "안녕하세요",          "헬로"),
        ("Thank you",            "감사합니다",          "댕큐"),
        ("Excuse me",            "실례합니다",          "익스큐즈 미"),
        ("Where is it?",         "어디에 있나요?",      "웨어 이즈 잇"),
        ("How much?",            "얼마인가요?",         "하우 머치"),
        ("I need help",          "도움이 필요해요",     "아이 니드 헬프"),
        ("Yes",                  "네",                  "예스"),
        ("No",                   "아니요",              "노"),
        ("Sorry",                "죄송합니다",          "쏘리"),
        ("Good morning",         "좋은 아침이에요",     "굿 모닝"),
        ("Where is the bathroom?","화장실이 어디인가요?","웨어 이즈 더 배스룸"),
        ("Can I have the menu?", "메뉴 주세요",         "캔 아이 해브 더 메뉴"),
        ("Check in please",      "체크인 해주세요",     "체크인 플리즈"),
        ("Call the police",      "경찰을 불러주세요",   "콜 더 폴리스"),
        ("I'm lost",             "길을 잃었어요",       "아임 로스트"),
    ],
}

FALLBACK_WORDS: dict[str, list] = {
    "japanese": [
        ("水", "물", "미즈"), ("食べ物", "음식", "타베모노"), ("お金", "돈", "오카네"),
        ("電車", "전철", "덴샤"), ("バス", "버스", "바스"), ("タクシー", "택시", "타쿠시"),
        ("空港", "공항", "쿠코"), ("駅", "역", "에키"), ("ホテル", "호텔", "호테루"),
        ("病院", "병원", "뵤인"), ("薬局", "약국", "야쿄쿠"), ("警察", "경찰", "케이사츠"),
        ("地図", "지도", "치즈"), ("切符", "표", "킵푸"), ("料金", "요금", "료킨"),
        ("予約", "예약", "요야쿠"), ("部屋", "방", "헤야"), ("鍵", "열쇠", "카기"),
        ("荷物", "짐", "니모츠"), ("パスポート", "여권", "파스포토"),
        ("クレジットカード", "신용카드", "쿠레짓토카도"), ("現金", "현금", "겐킨"),
        ("レシート", "영수증", "레시토"), ("入口", "입구", "이리구치"),
        ("出口", "출구", "데구치"), ("右", "오른쪽", "미기"), ("左", "왼쪽", "히다리"),
        ("まっすぐ", "직진", "맛스구"), ("近く", "근처", "치카쿠"), ("遠い", "멀다", "토이"),
        ("大きい", "크다", "오키이"), ("小さい", "작다", "치이사이"),
        ("熱い", "뜨겁다", "아츠이"), ("冷たい", "차갑다", "츠메타이"),
        ("美味しい", "맛있다", "오이시이"), ("辛い", "맵다", "카라이"),
        ("甘い", "달다", "아마이"), ("アレルギー", "알레르기", "아레루기"),
        ("おすすめ", "추천", "오스스메"), ("注文", "주문", "추몬"),
        ("会計", "계산", "카이케이"), ("割引", "할인", "와리비키"),
        ("セール", "세일", "세루"), ("サイズ", "사이즈", "사이즈"),
        ("写真", "사진", "샤신"), ("観光", "관광", "칸코"),
        ("博物館", "박물관", "하쿠부츠칸"), ("お土産", "기념품", "오미야게"),
        ("祭り", "축제", "마츠리"), ("天気", "날씨", "텐키"),
        ("今日", "오늘", "쿄"), ("明日", "내일", "아시타"),
        ("電話", "전화", "덴와"), ("インターネット", "인터넷", "인타넷토"),
        ("充電", "충전", "쥬덴"), ("Wi-Fi", "와이파이", "와이파이"),
    ],
    "english": [
        ("water", "물", "워터"), ("food", "음식", "푸드"), ("money", "돈", "머니"),
        ("subway", "지하철", "서브웨이"), ("bus", "버스", "버스"), ("taxi", "택시", "택시"),
        ("airport", "공항", "에어포트"), ("station", "역", "스테이션"), ("hotel", "호텔", "호텔"),
        ("hospital", "병원", "하스피털"), ("pharmacy", "약국", "파머시"), ("police", "경찰", "폴리스"),
        ("map", "지도", "맵"), ("ticket", "표", "티켓"), ("fare", "요금", "페어"),
        ("reservation", "예약", "레저베이션"), ("room", "방", "룸"), ("key", "열쇠", "키"),
        ("luggage", "짐", "러기지"), ("passport", "여권", "패스포트"),
        ("credit card", "신용카드", "크레딧 카드"), ("cash", "현금", "캐시"),
        ("receipt", "영수증", "리싯"), ("entrance", "입구", "엔트런스"),
        ("exit", "출구", "엑싯"), ("right", "오른쪽", "라이트"), ("left", "왼쪽", "레프트"),
        ("straight", "직진", "스트레이트"), ("nearby", "근처", "니어바이"),
        ("far", "멀다", "파"), ("big", "크다", "빅"), ("small", "작다", "스몰"),
        ("hot", "뜨겁다", "핫"), ("cold", "차갑다", "콜드"), ("delicious", "맛있다", "딜리셔스"),
        ("spicy", "맵다", "스파이시"), ("sweet", "달다", "스윗"),
        ("allergy", "알레르기", "알러지"), ("recommendation", "추천", "레커멘데이션"),
        ("order", "주문", "오더"), ("bill", "계산서", "빌"), ("discount", "할인", "디스카운트"),
        ("sale", "세일", "세일"), ("size", "사이즈", "사이즈"),
        ("photo", "사진", "포토"), ("sightseeing", "관광", "사잇씨잉"),
        ("museum", "박물관", "뮤지엄"), ("souvenir", "기념품", "수버니어"),
        ("festival", "축제", "페스티벌"), ("weather", "날씨", "웨더"),
        ("today", "오늘", "투데이"), ("tomorrow", "내일", "투모로우"),
        ("phone", "전화", "폰"), ("internet", "인터넷", "인터넷"),
        ("charge", "충전", "차지"), ("Wi-Fi", "와이파이", "와이파이"),
    ],
}


# ── Gemini API 유틸 (무료 REST 방식) ─────────────────────────────
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def _get_api_key() -> str:
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    env = os.environ.get("GEMINI_API_KEY", "")
    if env:
        return env
    return st.session_state.get("api_key", "")

def is_api_ready() -> bool:
    return bool(_get_api_key())

def _call_gemini(prompt: str) -> str:
    """Gemini REST API 호출. 실패 시 예외 발생."""
    api_key = _get_api_key()
    resp = requests.post(
        f"{GEMINI_API_URL}?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    
    # 오류 처리
    try:
        err_data = resp.json()
        err_msg = err_data.get("error", {}).get("message", f"HTTP {resp.status_code}")
    except Exception:
        err_msg = f"HTTP {resp.status_code}"
    
    if resp.status_code == 429:
        raise RuntimeError("API 사용량 초과입니다. 잠시 후 다시 시도하거나 기본 데이터를 이용해주세요.")
    elif resp.status_code in (400, 403):
        raise RuntimeError(f"API 키가 올바르지 않습니다: {err_msg}")
    else:
        raise RuntimeError(f"API 오류 ({resp.status_code}): {err_msg}")


def _parse_pipe_lines(text: str, lang: str) -> list[dict]:
    result = []
    for line in text.strip().splitlines():
        line = line.strip().lstrip("0123456789.-) ")
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        foreign, korean = parts[0], parts[1]
        reading = parts[2] if len(parts) > 2 else ""
        if foreign and korean:
            result.append({"foreign": foreign, "korean": korean,
                            "reading": reading, "lang": lang})
    return result


# ── 기능 함수 ──────────────────────────────────────────────────────
def translate(korean_text: str, target_lang: str) -> tuple[dict | None, str | None]:
    if not is_api_ready():
        return None, "사이드바에서 Gemini API 키를 먼저 입력해주세요."

    lang_name = LANGUAGES[target_lang]["gemini"]
    prompt = f"""Translate the following Korean text to {lang_name}.
Respond ONLY with these three lines (no extra text, no markdown):
TRANSLATION: [translated text in {lang_name}]
READING: [pronunciation in Korean characters]
ALTERNATIVE: [one alternative expression in {lang_name}]

Korean text: {korean_text}"""

    try:
        text = _call_gemini(prompt)
        lines = text.strip().splitlines()
        result: dict = {"original": korean_text, "translation": "", "reading": "", "alternative": ""}
        for line in lines:
            line = line.strip()
            if line.startswith("TRANSLATION:"):
                result["translation"] = line[12:].strip()
            elif line.startswith("READING:"):
                result["reading"]     = line[8:].strip()
            elif line.startswith("ALTERNATIVE:"):
                result["alternative"] = line[12:].strip()
        if not result["translation"]:
            return None, "응답 파싱 실패. 다시 시도해 주세요."
        return result, None
    except Exception as e:
        return None, str(e)


def generate_cards(language: str, category: dict, count: int) -> list[dict]:
    if not is_api_ready():
        return _fallback(language, count)

    lang_name = LANGUAGES[language]["gemini"]
    cat_label = f"{category['name']} ({category['en']})"
    prompt = f"""Generate exactly {count} {lang_name} travel phrases for: {cat_label}

Format each line EXACTLY like this (no numbering, no extra text, no markdown):
[phrase in {lang_name}] | [korean meaning] | [pronunciation in Korean]

Generate {count} lines:"""

    try:
        text = _call_gemini(prompt)
        cards = _parse_pipe_lines(text, language)
        return cards[:count] if cards else _fallback(language, count)
    except Exception:
        return _fallback(language, count)


def generate_flash_words(language: str, count: int = 50) -> list[dict]:
    """API 성공 시 AI 단어, 실패 시 fallback 자동 반환."""
    if not is_api_ready():
        return _fallback_words(language, count)

    lang_name = LANGUAGES[language]["gemini"]
    prompt = f"""Generate {count} common {lang_name} words/phrases for travel.
Format each line EXACTLY (no numbering, no markdown):
[word in {lang_name}] | [korean meaning] | [pronunciation in Korean]

Generate {count} lines:"""

    try:
        text = _call_gemini(prompt)
        words = _parse_pipe_lines(text, language)
        if not words:
            return _fallback_words(language, count)
        random.shuffle(words)
        return words
    except Exception:
        return _fallback_words(language, count)


def _fallback(language: str, count: int) -> list[dict]:
    data = FALLBACK_CARDS.get(language, FALLBACK_CARDS["japanese"])
    sample = random.sample(data, min(count, len(data)))
    return [{"foreign": f, "korean": k, "reading": r, "lang": language}
            for f, k, r in sample]


def _fallback_words(language: str, count: int = 50) -> list[dict]:
    data = FALLBACK_WORDS.get(language, FALLBACK_WORDS["japanese"])
    sample = random.sample(data, min(count, len(data)))
    result = [{"foreign": f, "korean": k, "reading": r, "lang": language}
              for f, k, r in sample]
    random.shuffle(result)
    return result


# ── Web Speech API TTS (브라우저 내장, 외부 요청 없음) ─────────────
def tts_html(text: str, lang: str) -> str:
    tts_lang = LANGUAGES[lang]["tts"]
    safe = (text.replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace("\n", " ")
                .replace("\r", ""))
    return f"""<script>
(function(){{
  if(!('speechSynthesis' in window)){{ return; }}
  window.speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance('{safe}');
  u.lang='{tts_lang}'; u.rate=0.85; u.pitch=1.0; u.volume=1.0;
  function speak(){{
    var vs = window.speechSynthesis.getVoices();
    var m = vs.find(function(v){{return v.lang.startsWith('{tts_lang.split('-')[0]}');}});
    if(m) u.voice=m;
    window.speechSynthesis.speak(u);
  }}
  if(window.speechSynthesis.getVoices().length > 0){{ speak(); }}
  else{{ window.speechSynthesis.onvoiceschanged = speak; }}
}})();
</script>"""


def play_audio_btn(label: str, text: str, lang: str, key: str):
    if st.button(label, key=key, use_container_width=True):
        st.components.v1.html(tts_html(text, lang), height=0)


# ── CSS ────────────────────────────────────────────────────────────
DARK_CSS = """<style>
/* ── 기본 배경 ── */
.stApp { background: #0d1117 !important; color: #e6edf3; }

/* ── 상단바: 다크 배경 ── */
header[data-testid="stHeader"] { background: #161b22 !important; border-bottom: 1px solid #30363d !important; }

/* ── 숨길 항목들 (사이드바 토글 버튼은 절대 건드리지 않음) ── */
[data-testid="stDecoration"]       { display: none !important; }
#MainMenu                          { display: none !important; }
footer                             { display: none !important; }
[data-testid="stMainMenuButton"]   { display: none !important; }
[data-testid="stStatusWidget"]     { display: none !important; }
[data-testid="stToolbarActions"]   { display: none !important; }

/* ── 사이드바 토글 버튼: 닫혔을 때도 반드시 보이게 ── */
[data-testid="stSidebarCollapsedControl"] { display: flex !important; visibility: visible !important; opacity: 1 !important; }
[data-testid="collapsedControl"]          { display: flex !important; visibility: visible !important; opacity: 1 !important; }
[data-testid="stSidebarNavCollapseIcon"]  { display: flex !important; visibility: visible !important; }

/* ── 사이드바 ── */
section[data-testid="stSidebar"] {
    background: #161b22 !important; border-right: 1px solid #30363d;
}

/* ── 버튼 ── */
.stButton > button {
    border-radius: 10px !important; font-weight: 500 !important;
    transition: all .18s ease !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1f6feb, #7c3aed) !important;
    border: none !important; color: #fff !important;
}
.stButton > button[kind="secondary"] {
    background: #21262d !important; border: 1px solid #30363d !important;
    color: #8b949e !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; opacity:.9; }

/* ── 입력 ── */
.stTextArea textarea, .stTextInput input {
    background: #21262d !important; border: 1px solid #30363d !important;
    border-radius: 10px !important; color: #e6edf3 !important;
}
.stSelectbox > div > div { background: #21262d !important; border-color: #30363d !important; }
.stSlider > div > div > div > div { background: #1f6feb !important; }
hr { border-color: #30363d !important; }

/* ── 탭 다크 스타일 ── */
[data-testid="stTabs"] button {
    color: #8b949e !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #58a6ff !important;
    border-bottom: 2px solid #58a6ff !important;
    background: transparent !important;
}
[data-testid="stTabs"] { border-bottom: 1px solid #30363d !important; }

/* ── 카드 공통 ── */
.flash-wrap {
    background: linear-gradient(135deg, #1f6feb 0%, #7c3aed 100%);
    border-radius: 20px; padding: 36px 24px; text-align: center;
    box-shadow: 0 12px 40px rgba(31,111,235,.3);
}
.flash-inner {
    background: rgba(255,255,255,.12); border-radius: 14px;
    padding: 28px; margin-bottom: 14px;
}
.flash-word { font-size: 3.2em; font-weight: 800; color: #fff; line-height: 1.2; }
.flash-reading { font-size: 1.3em; color: rgba(255,255,255,.85); margin-top: 8px; }
.flash-korean {
    background: rgba(0,0,0,.25); border-radius: 10px; padding: 12px 20px;
    font-size: 1.6em; font-weight: 600; color: #fff;
    display: inline-block; margin-top: 12px;
}

.result-wrap {
    background: #161b22; border: 1px solid #30363d;
    border-left: 4px solid #1f6feb; border-radius: 14px;
    padding: 24px; margin: 14px 0; text-align: center;
}
.result-main { font-size: 2.6em; font-weight: 700; color: #e6edf3; }
.result-reading { color: #58a6ff; font-size: 1.15em; font-weight: 500; }
.result-alt {
    font-size: .9em; color: #8b949e; background: #21262d;
    padding: 8px 14px; border-radius: 8px; display: inline-block; margin-top: 8px;
}

.study-card-wrap {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 20px; padding: 44px 28px; text-align: center; min-height: 220px;
}
.study-foreign { font-size: 3em; font-weight: 800; color: #e6edf3; }
.study-reading { color: #58a6ff; font-size: 1.2em; font-weight: 500; margin-top: 8px; }
.study-answer {
    background: linear-gradient(135deg, #0d2f0d, #1a4a1a);
    border: 2px solid #3fb950; border-radius: 14px;
    padding: 16px 24px; margin-top: 18px; display: inline-block;
}
.study-korean { color: #3fb950; font-size: 1.6em; font-weight: 600; }
</style>"""


# ── 세션 초기화 ────────────────────────────────────────────────────
def init_session():
    defaults = {
        "api_key":      os.environ.get("GEMINI_API_KEY", ""),
        "lang":         "japanese",
        "cat_idx":      0,
        "cards":        _fallback("japanese", 8),
        "card_idx":     0,
        "show_answer":  False,
        "trans_result": None,
        "flash_words":  [],
        "flash_idx":    0,
        "active_tab":   0,   # 0=번역기, 1=학습카드, 2=단어깜빡이
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── UI ─────────────────────────────────────────────────────────────
def setup_page():
    st.set_page_config(
        page_title="AI 여행 어학 튜터", page_icon="✈️",
        layout="centered", initial_sidebar_state="expanded",
    )
    # 다크모드 강제 적용 (config.toml 없이도 동작)
    st.markdown("""
<script>
// 다크모드 강제 설정
try {
    window.localStorage.setItem('streamlit_theme', 'Dark');
} catch(e) {}
</script>
""", unsafe_allow_html=True)
    st.markdown(DARK_CSS, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center;padding:12px 0 20px'>"
            "<div style='font-size:2em'>✈️</div>"
            "<div style='font-size:1.1em;font-weight:700;color:#e6edf3'>AI 여행 어학 튜터</div>"
            "<div style='font-size:.8em;color:#8b949e'>Travel Language Master</div>"
            "</div>", unsafe_allow_html=True,
        )

        st.markdown("#### 🌍 학습 언어")
        c1, c2 = st.columns(2)
        for i, (key, info) in enumerate(LANGUAGES.items()):
            col = c1 if i == 0 else c2
            with col:
                btype = "primary" if st.session_state.lang == key else "secondary"
                if st.button(f"{info['emoji']} {info['name']}", key=f"lang_{key}",
                             use_container_width=True, type=btype):
                    st.session_state.lang = key
                    st.session_state.cards = _fallback(key, 8)
                    st.session_state.card_idx = 0
                    st.session_state.show_answer = False
                    st.session_state.flash_words = []   # 언어 바뀌면 단어깜빡이 초기화
                    st.session_state.flash_idx = 0
                    st.rerun()

        st.markdown("#### 📂 카테고리")
        for idx, cat in enumerate(CATEGORIES):
            btype = "primary" if st.session_state.cat_idx == idx else "secondary"
            if st.button(f"{cat['icon']} {cat['name']}", key=f"cat_{idx}",
                         use_container_width=True, type=btype):
                st.session_state.cat_idx = idx
                st.session_state.active_tab = 1   # 학습 카드 탭으로 전환
                st.rerun()

        st.markdown("---")
        st.markdown("#### 🔑 Gemini API 키 (무료)")
        if is_api_ready():
            st.success("✅ API 연결됨")
            if st.button("🔧 API 키 변경", use_container_width=True):
                st.session_state.api_key = ""
                st.rerun()
        else:
            st.info("💡 Google AI Studio에서 무료 발급 가능")
            new_key = st.text_input("API Key 입력", type="password",
                                    placeholder="AIza...",
                                    help="무료: 분당 15회, 일 1500회")
            if st.button("💾 저장", type="primary", use_container_width=True):
                if new_key.strip():
                    st.session_state.api_key = new_key.strip()
                    st.success("저장되었습니다!")
                    st.rerun()
                else:
                    st.warning("키를 입력해주세요.")
            st.markdown(
                "**[🔗 무료 API 키 발급받기](https://aistudio.google.com/app/apikey)**",
                unsafe_allow_html=True,
            )
            st.caption("발급 → API keys → Create API key")


def render_translator():
    st.markdown("### ✏️ 한글 번역기")
    st.caption("원하는 말을 한글로 입력하면 번역해 드립니다!")

    col_input, col_lang = st.columns([3, 1])
    with col_input:
        korean_text = st.text_area(
            "한글 입력", placeholder="예: 화장실이 어디에 있나요?",
            height=90, key="korean_input", label_visibility="collapsed",
        )
    with col_lang:
        target = st.selectbox(
            "언어", list(LANGUAGES.keys()),
            format_func=lambda x: f"{LANGUAGES[x]['emoji']} {LANGUAGES[x]['name']}",
            label_visibility="collapsed",
        )

    if st.button("🔄 번역하기", type="primary", use_container_width=True):
        if not korean_text.strip():
            st.warning("번역할 텍스트를 입력해주세요.")
        elif not is_api_ready():
            st.error("사이드바에서 Gemini API 키를 먼저 설정해주세요.")
        else:
            with st.spinner("🤖 번역 중..."):
                result, err = translate(korean_text.strip(), target)
            if err:
                st.error(f"❌ {err}")
            else:
                st.session_state.trans_result = {"data": result, "lang": target}

    if st.session_state.trans_result:
        r    = st.session_state.trans_result["data"]
        lang = st.session_state.trans_result["lang"]
        info = LANGUAGES[lang]
        reading_html = f'<div class="result-reading">📖 {r["reading"]}</div>' if r.get("reading") else ""
        alt_html     = f'<div class="result-alt">💡 다른 표현: {r["alternative"]}</div>' if r.get("alternative") else ""

        st.markdown(f"""
<div class="result-wrap">
  <div style="margin-bottom:12px">
    <span style="background:#1f3a5f;color:#58a6ff;padding:4px 14px;border-radius:20px;font-size:.85em">
      {info['emoji']} {info['name']} 번역 결과
    </span>
  </div>
  <div style="color:#8b949e;font-size:.9em;margin-bottom:10px">🇰🇷 {r['original']}</div>
  <div class="result-main">{r['translation']}</div>
  {reading_html}
  {alt_html}
</div>""", unsafe_allow_html=True)

        play_audio_btn(f"🔊 {info['name']} 발음 듣기", r["translation"], lang, "tts_translate")


def render_study_cards():
    st.markdown("### 📚 학습 카드")

    c1, c2 = st.columns([2, 1])
    with c1:
        count = st.slider("문장 개수", 5, 15, 8, key="card_count")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎯 AI 문장 생성", type="primary", use_container_width=True):
            if not is_api_ready():
                st.error("API 키를 먼저 설정해주세요.")
            else:
                with st.spinner("🤖 생성 중..."):
                    cards = generate_cards(
                        st.session_state.lang,
                        CATEGORIES[st.session_state.cat_idx],
                        count,
                    )
                st.session_state.cards = cards
                st.session_state.card_idx = 0
                st.session_state.show_answer = False
                st.success(f"✅ {len(cards)}개 카드 생성 완료!")
                st.rerun()

    cards  = st.session_state.cards
    idx    = st.session_state.card_idx
    total  = len(cards)
    card   = cards[idx]
    answer = st.session_state.show_answer

    reading_html = f'<div class="study-reading">📖 {card["reading"]}</div>' if card.get("reading") else ""
    answer_html  = (
        f'<div class="study-answer"><div class="study-korean">🇰🇷 {card["korean"]}</div></div>'
        if answer else
        '<div style="color:#484f58;font-size:.95em;margin-top:16px">👆 정답 보기를 눌러주세요</div>'
    )

    st.markdown(f"""
<div class="study-card-wrap">
  <div class="study-foreign">{card['foreign']}</div>
  {reading_html}
  {answer_html}
</div>""", unsafe_allow_html=True)

    btn_label = "🔒 숨기기" if answer else "👀 정답 보기"
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("⏮️", key="first", use_container_width=True):
            st.session_state.card_idx = 0; st.session_state.show_answer = False; st.rerun()
    with c2:
        if st.button("◀ 이전", key="prev", use_container_width=True):
            if idx > 0: st.session_state.card_idx -= 1
            st.session_state.show_answer = False; st.rerun()
    with c3:
        if st.button(btn_label, key="toggle", use_container_width=True, type="primary"):
            st.session_state.show_answer = not answer; st.rerun()
    with c4:
        if st.button("다음 ▶", key="next", use_container_width=True):
            if idx < total - 1: st.session_state.card_idx += 1
            st.session_state.show_answer = False; st.rerun()
    with c5:
        if st.button("⏭️", key="last", use_container_width=True):
            st.session_state.card_idx = total - 1; st.session_state.show_answer = False; st.rerun()

    st.markdown(
        f"<div style='text-align:center;color:#484f58;font-size:.9em;margin-top:10px'>{idx+1} / {total}</div>",
        unsafe_allow_html=True,
    )

    col_audio, col_shuffle = st.columns(2)
    with col_audio:
        play_audio_btn("🔊 발음 듣기", card["foreign"], card["lang"], "tts_card")
    with col_shuffle:
        if st.button("🔀 카드 섞기", key="shuffle", use_container_width=True):
            random.shuffle(st.session_state.cards)
            st.session_state.card_idx = 0; st.session_state.show_answer = False; st.rerun()


def _flash_widget_html(words: list[dict], lang: str) -> str:
    """단어 깜빡이 전체를 브라우저 안에서 처리하는 독립 HTML 위젯.
    - 2초마다 자동 전환 + 카운트다운 진행바
    - 단어 표시 즉시 Web Speech API로 발음 재생
    - 재생/일시정지, 이전/다음, 속도 조절, 새 단어 버튼
    """
    import json as _json
    tts_lang = LANGUAGES[lang]["tts"]
    words_json = _json.dumps(
        [{"f": w["foreign"], "k": w["korean"], "r": w.get("reading", "")} for w in words],
        ensure_ascii=False,
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    font-family: -apple-system, 'Segoe UI', sans-serif;
    color: #e6edf3;
  }}
  .widget {{
    width: 100%;
    max-width: 600px;
    margin: 0 auto;
    padding: 8px 0 16px;
  }}

  /* 카드 */
  .card {{
    background: linear-gradient(135deg, #1f6feb 0%, #7c3aed 100%);
    border-radius: 20px;
    padding: 32px 24px 24px;
    text-align: center;
    box-shadow: 0 12px 40px rgba(31,111,235,.35);
    position: relative;
    overflow: hidden;
  }}
  .card-inner {{
    background: rgba(255,255,255,.13);
    border-radius: 14px;
    padding: 28px 20px 20px;
    margin-bottom: 14px;
  }}
  .word {{
    font-size: 3em;
    font-weight: 800;
    color: #fff;
    line-height: 1.2;
    letter-spacing: .02em;
    transition: opacity .25s;
  }}
  .reading {{
    font-size: 1.2em;
    color: rgba(255,255,255,.88);
    margin-top: 10px;
  }}
  .korean {{
    background: rgba(0,0,0,.28);
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 1.5em;
    font-weight: 600;
    color: #fff;
    display: inline-block;
    margin-top: 4px;
  }}

  /* 진행바 */
  .prog-wrap {{
    width: 100%;
    height: 5px;
    background: rgba(255,255,255,.2);
    border-radius: 3px;
    margin-top: 18px;
    overflow: hidden;
  }}
  .prog-bar {{
    height: 100%;
    background: rgba(255,255,255,.85);
    border-radius: 3px;
    width: 100%;
    transform-origin: left;
    transition: none;
  }}

  /* 카운터 */
  .counter {{
    text-align: center;
    color: rgba(255,255,255,.7);
    font-size: .82em;
    margin-top: 8px;
  }}

  /* 컨트롤 버튼 */
  .controls {{
    display: flex;
    gap: 8px;
    margin-top: 14px;
    justify-content: center;
    flex-wrap: wrap;
  }}
  .btn {{
    flex: 1;
    min-width: 60px;
    padding: 10px 8px;
    border: none;
    border-radius: 10px;
    font-size: .9em;
    font-weight: 600;
    cursor: pointer;
    transition: transform .15s, opacity .15s;
  }}
  .btn:hover {{ transform: translateY(-2px); opacity: .88; }}
  .btn:active {{ transform: scale(.95); }}
  .btn-primary {{
    background: linear-gradient(135deg, #1f6feb, #7c3aed);
    color: #fff;
  }}
  .btn-secondary {{
    background: #21262d;
    border: 1px solid #30363d;
    color: #c9d1d9;
  }}
  .btn-danger {{
    background: #3d1a1a;
    border: 1px solid #6e3030;
    color: #f87171;
  }}

  /* 속도 선택 */
  .speed-row {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-top: 10px;
    font-size: .82em;
    color: #8b949e;
  }}
  .speed-row select {{
    background: #21262d;
    border: 1px solid #30363d;
    color: #c9d1d9;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: .9em;
    cursor: pointer;
  }}

  /* 페이드 애니메이션 */
  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .fade-in {{ animation: fadeIn .3s ease; }}
</style>
</head>
<body>
<div class="widget">
  <div class="card">
    <div class="card-inner">
      <div class="word" id="word">--</div>
      <div class="reading" id="reading"></div>
    </div>
    <div class="korean" id="korean">--</div>
    <div class="prog-wrap">
      <div class="prog-bar" id="prog"></div>
    </div>
    <div class="counter" id="counter">0 / 0</div>
  </div>

  <div class="controls">
    <button class="btn btn-secondary" onclick="prev()">◀ 이전</button>
    <button class="btn btn-primary"   id="playBtn" onclick="togglePlay()">⏸ 일시정지</button>
    <button class="btn btn-secondary" onclick="next()">다음 ▶</button>
    <button class="btn btn-secondary" onclick="toggleMute()" id="muteBtn">🔊 음성</button>
    <button class="btn btn-danger"    onclick="resetWords()">🔄 새 단어</button>
  </div>

  <div class="speed-row">
    <span>⏱ 간격</span>
    <select id="speedSel" onchange="changeSpeed()">
      <option value="1500">1.5초</option>
      <option value="2000" selected>2초</option>
      <option value="3000">3초</option>
      <option value="4000">4초</option>
      <option value="5000">5초</option>
    </select>
    <span id="ttsStatus" style="color:#3fb950">🎵 음성 ON</span>
  </div>
</div>

<script>
const WORDS    = {words_json};
const TTS_LANG = '{tts_lang}';
let idx      = 0;
let playing  = true;
let muted    = false;
let interval = 2000;
let timer    = null;
let progTimer= null;
let progStart= null;

function $(id) {{ return document.getElementById(id); }}

function showWord(i, animate) {{
  const w = WORDS[i];
  if (!w) return;

  const wordEl = $('word');
  const progEl = $('prog');

  if (animate) {{
    wordEl.classList.remove('fade-in');
    void wordEl.offsetWidth;           // reflow
    wordEl.classList.add('fade-in');
  }}

  wordEl.textContent        = w.f;
  $('reading').textContent  = w.r ? '📖 ' + w.r : '';
  $('korean').textContent   = '🇰🇷 ' + w.k;
  $('counter').textContent  = (i + 1) + ' / ' + WORDS.length;

  // 진행바 리셋
  progEl.style.transition = 'none';
  progEl.style.width      = '100%';

  // 발음
  if (!muted) speakWord(w.f);

  // 진행바 애니메이션
  setTimeout(function() {{
    progEl.style.transition = 'width ' + interval + 'ms linear';
    progEl.style.width      = '0%';
  }}, 30);
}}

function speakWord(text) {{
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(text);
  u.lang   = TTS_LANG;
  u.rate   = 0.85;
  u.pitch  = 1.0;
  u.volume = 1.0;
  function doSpeak() {{
    var vs = window.speechSynthesis.getVoices();
    var m  = vs.find(function(v) {{ return v.lang.startsWith(TTS_LANG.split('-')[0]); }});
    if (m) u.voice = m;
    window.speechSynthesis.speak(u);
  }}
  if (window.speechSynthesis.getVoices().length > 0) {{ doSpeak(); }}
  else {{ window.speechSynthesis.onvoiceschanged = doSpeak; }}
}}

function next() {{
  idx = (idx + 1) % WORDS.length;
  showWord(idx, true);
  if (playing) resetTimer();
}}

function prev() {{
  idx = (idx - 1 + WORDS.length) % WORDS.length;
  showWord(idx, true);
  if (playing) resetTimer();
}}

function resetTimer() {{
  clearInterval(timer);
  if (playing) {{
    timer = setInterval(next, interval);
  }}
}}

function togglePlay() {{
  playing = !playing;
  $('playBtn').textContent = playing ? '⏸ 일시정지' : '▶ 재생';
  if (playing) {{
    showWord(idx, false);
    resetTimer();
  }} else {{
    clearInterval(timer);
    // 진행바 정지
    var prog = $('prog');
    var cs   = window.getComputedStyle(prog);
    prog.style.transition = 'none';
    prog.style.width      = cs.width;
    window.speechSynthesis.cancel();
  }}
}}

function toggleMute() {{
  muted = !muted;
  $('muteBtn').textContent    = muted ? '🔇 음성' : '🔊 음성';
  $('ttsStatus').textContent  = muted ? '🔇 음성 OFF' : '🎵 음성 ON';
  $('ttsStatus').style.color  = muted ? '#f87171' : '#3fb950';
  if (muted) window.speechSynthesis.cancel();
}}

function changeSpeed() {{
  interval = parseInt($('speedSel').value);
  if (playing) resetTimer();
}}

function resetWords() {{
  clearInterval(timer);
  window.speechSynthesis.cancel();
  // Streamlit에 신호를 보내 단어 목록 초기화
  window.parent.postMessage({{type:'streamlit:setComponentValue', value:'reset'}}, '*');
}}

// 초기 표시 & 자동 재생 시작
showWord(0, false);
timer = setInterval(next, interval);
</script>
</body>
</html>"""


def render_flash():
    st.markdown("### ⚡ 단어 깜빡이")
    st.caption("2초마다 자동 전환 + 발음 자동 재생. API 없이도 기본 단어로 바로 시작!")

    lang  = st.session_state.lang
    words = st.session_state.flash_words

    # 언어가 바뀌었는데 아직 이전 언어 단어가 남아 있으면 자동 초기화
    if words and words[0].get("lang") != lang:
        st.session_state.flash_words = []
        st.session_state.flash_idx   = 0
        words = []

    if not words:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 AI 단어 생성", type="primary", use_container_width=True):
                with st.spinner("🤖 단어를 가져오는 중..."):
                    w = generate_flash_words(lang)
                st.session_state.flash_words = w
                st.session_state.flash_idx   = 0
                st.rerun()
        with col2:
            if st.button("📦 기본 단어로 시작", use_container_width=True):
                w = _fallback_words(lang, 50)
                st.session_state.flash_words = w
                st.session_state.flash_idx   = 0
                st.rerun()
        lang_name = LANGUAGES[lang]["name"]
        st.caption(f"현재 언어: {LANGUAGES[lang]['emoji']} {lang_name} | API 키 없이도 '기본 단어로 시작' 클릭!")
        return

    st.components.v1.html(
        _flash_widget_html(words, lang),
        height=400,
        scrolling=False,
    )

    # 새 단어 버튼 (Streamlit 레벨)
    if st.button("🔄 단어 목록 초기화", key="fl_reset", use_container_width=True):
        st.session_state.flash_words = []
        st.session_state.flash_idx   = 0
        st.rerun()


# ── 진입점 ─────────────────────────────────────────────────────────
def main():
    setup_page()
    init_session()
    render_sidebar()

    active = st.session_state.get("active_tab", 0)

    # st.tabs는 index 선택을 직접 지원하지 않으므로
    # query_params를 이용해 JS로 탭 클릭 트리거
    if active != 0:
        st.components.v1.html(f"""
<script>
(function tryClick() {{
    var tabs = window.parent.document.querySelectorAll(
        '[data-testid="stTabs"] [data-baseweb="tab"]'
    );
    if (!tabs || tabs.length === 0) {{
        setTimeout(tryClick, 80);
        return;
    }}
    if (tabs[{active}]) tabs[{active}].click();
}})();
</script>
""", height=0)
        st.session_state.active_tab = 0  # 이동 후 리셋

    tab_trans, tab_study, tab_flash = st.tabs(["✏️ 번역기", "📚 학습 카드", "⚡ 단어 깜빡이"])
    with tab_trans:
        render_translator()
    with tab_study:
        render_study_cards()
    with tab_flash:
        render_flash()

    st.markdown(
        "<div style='text-align:center;color:#484f58;padding:24px;font-size:.8em'>"
        "Made with ❤️ using Streamlit &amp; Gemini AI (Free Tier)</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
