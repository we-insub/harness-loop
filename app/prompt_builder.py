from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .config import PROMPT_FILE_ORDER, VISIT_END, VISIT_START

IMAGE_TAG_RE = re.compile(r"\[image_\d+\.(?:jpg|jpeg|png|webp|gif)\]", re.IGNORECASE)
VISIT_DATE_RE = re.compile(r"(20\d{2})[.\-/](\d{2})[.\-/](\d{2})\s*방문 기준")


@dataclass(frozen=True)
class PromptInputs:
    title: str
    source: str
    visit_date: date
    image_tags: list[str]


@dataclass(frozen=True)
class BuiltPrompt:
    system_prompt: str
    user_prompt: str
    inputs: PromptInputs


def extract_image_tags(text: str) -> list[str]:
    return IMAGE_TAG_RE.findall(text or "")


def extract_visit_date(text: str) -> date | None:
    match = VISIT_DATE_RE.search(text or "")
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    return date(year, month, day)


def format_visit_date(value: date) -> str:
    return value.strftime("%Y.%m.%d")


def deterministic_visit_date(title: str, source: str, run_index: int = 0) -> date:
    span_days = (VISIT_END - VISIT_START).days + 1
    seed = f"{title}\0{source}\0{run_index}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()
    offset = int(digest[:8], 16) % span_days
    return VISIT_START + timedelta(days=offset)


def make_prompt_inputs(title: str, source: str, run_index: int = 0) -> PromptInputs:
    source_visit_date = extract_visit_date(source)
    visit_date = source_visit_date or deterministic_visit_date(title, source, run_index)
    return PromptInputs(
        title=title.strip(),
        source=source.strip(),
        visit_date=visit_date,
        image_tags=extract_image_tags(source),
    )


def load_prompt_sections(prompts_dir: Path) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    for file_name in PROMPT_FILE_ORDER:
        path = prompts_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        sections.append((file_name, path.read_text(encoding="utf-8").strip()))
    return sections


def build_prompt(title: str, source: str, prompts_dir: Path, run_index: int = 0) -> BuiltPrompt:
    inputs = make_prompt_inputs(title, source, run_index)
    sections = load_prompt_sections(prompts_dir)
    system_prompt = "\n\n".join(f"[{name}]\n{content}" for name, content in sections)
    image_tags = "\n".join(inputs.image_tags) if inputs.image_tags else "없음"
    user_prompt = f"""아래 입력값을 기준으로 최종 블로그 글만 작성하라.

제목:
{inputs.title}

방문일자:
{format_visit_date(inputs.visit_date)} 방문 기준

원문 이미지 태그:
{image_tags}

원문 데이터:
{inputs.source}

검증 전 자체 확인:
- 제목을 한 글자도 바꾸지 않았는가
- 원문 이미지 태그 순서와 개수를 유지했는가
- 본문 도입부에 방문일자를 넣었는가
- 정보성 데이터가 있으면 표 마커 형식으로 표를 넣었는가
- 출력 형식이 제목을입력해주세요1, 본문2 순서인가
"""
    return BuiltPrompt(system_prompt=system_prompt, user_prompt=user_prompt, inputs=inputs)

