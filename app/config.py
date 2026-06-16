from __future__ import annotations

from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPTS_DIR = PROJECT_ROOT / "prompts"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"

TODAY = date(2026, 6, 16)
VISIT_START = date(2026, 5, 17)
VISIT_END = date(2026, 6, 15)

DEFAULT_MODEL = "gpt-4.1-mini"

PROMPT_FILE_ORDER = [
    "role.txt",
    "date_rules.txt",
    "hard_rules.txt",
    "style_rules.txt",
    "mobile_rules.txt",
    "image_rules.txt",
    "table_rules.txt",
    "subtitle_rules.txt",
    "output_format.txt",
]

FORBIDDEN_PHRASES = [
    "정리해 드릴게요",
    "공유해 볼게요",
    "보여드릴게요",
    "꼼꼼하게",
    "알찬 팁",
    "완벽한",
]

INFO_KEYWORDS = [
    "가격",
    "요금",
    "비용",
    "일정",
    "코스",
    "포함",
    "불포함",
    "운영시간",
    "영업시간",
    "시간",
    "스펙",
    "상품명",
    "브랜드명",
    "주소",
    "전화",
    "예약",
    "준비물",
    "환불",
    "취소",
]

