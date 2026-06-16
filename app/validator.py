from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date

from .config import FORBIDDEN_PHRASES, INFO_KEYWORDS, VISIT_END, VISIT_START
from .prompt_builder import extract_image_tags, extract_visit_date

TITLE_LINE_RE = re.compile(r"^제목을입력해주세요1:\s*(.*)$", re.MULTILINE)
BODY_MARKER = "본문2:"
SUBTITLE_RE = re.compile(r"^ㅂㅂㅂ\S.*$", re.MULTILINE)
TABLE_START_RE = re.compile(r"^표\s+(\d+)\s*x\s*(\d+)\s+시작\s*$")
TABLE_END_RE = re.compile(r"^표\s+(\d+)\s*x\s*(\d+)\s+끝\s*$")
TABLE_CELL_RE = re.compile(r"^\((\d+),(\d+)\)\s+.+$")
OUTPUT_VISIT_DATE_RE = re.compile(r"(20\d{2})\.(\d{2})\.(\d{2})\s*방문 기준")


@dataclass(frozen=True)
class ValidationItem:
    name: str
    passed: bool
    message: str
    priority: int = 1


@dataclass(frozen=True)
class ValidationReport:
    items: list[ValidationItem]

    @property
    def score(self) -> int:
        return sum(1 for item in self.items if item.passed)

    @property
    def max_score(self) -> int:
        return len(self.items)

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.items)

    @property
    def failures(self) -> list[ValidationItem]:
        return [item for item in self.items if not item.passed]

    def priority_score(self) -> int:
        return sum(item.priority for item in self.items if item.passed)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "max_score": self.max_score,
            "priority_score": self.priority_score(),
            "items": [asdict(item) for item in self.items],
        }


def validate_output(title: str, source: str, output: str) -> ValidationReport:
    output = output or ""
    items: list[ValidationItem] = []

    title_match = TITLE_LINE_RE.search(output)
    actual_title = title_match.group(1).strip() if title_match else ""
    items.append(
        ValidationItem(
            "title_exact",
            bool(title_match) and actual_title == title.strip(),
            "제목 줄이 입력 제목과 완전히 일치해야 합니다.",
            priority=5,
        )
    )
    items.append(
        ValidationItem(
            "title_marker_exists",
            "제목을입력해주세요1:" in output,
            "`제목을입력해주세요1:` 마커가 있어야 합니다.",
            priority=4,
        )
    )
    items.append(
        ValidationItem(
            "body_marker_exists",
            BODY_MARKER in output,
            "`본문2:` 마커가 있어야 합니다.",
            priority=4,
        )
    )

    subtitle_lines = SUBTITLE_RE.findall(output)
    items.append(
        ValidationItem(
            "subtitle_minimum",
            len(subtitle_lines) >= 3,
            "본문 소제목은 최소 3개 이상이어야 합니다.",
            priority=3,
        )
    )
    items.append(
        ValidationItem(
            "subtitle_format",
            _subtitle_format_ok(output),
            "본문 소제목은 `ㅂㅂㅂ소제목명` 형식만 사용해야 합니다.",
            priority=3,
        )
    )
    items.append(
        ValidationItem(
            "toc_has_no_subtitle_marker",
            _toc_has_no_subtitle_marker(output),
            "목차 영역에는 `ㅂㅂㅂ` 마커가 들어가면 안 됩니다.",
            priority=3,
        )
    )

    source_images = extract_image_tags(source)
    output_images = extract_image_tags(output)
    items.append(
        ValidationItem(
            "image_tags_exact_order",
            output_images == source_images,
            "원문 이미지 태그의 개수와 순서를 그대로 유지해야 합니다.",
            priority=5,
        )
    )

    items.append(_validate_visit_date(source, output))

    source_has_info = _source_has_info_data(source)
    table_blocks = _parse_table_blocks(output)
    items.append(
        ValidationItem(
            "table_required_for_info",
            (not source_has_info) or bool(table_blocks),
            "정보성 데이터가 있으면 표가 1개 이상 있어야 합니다.",
            priority=5,
        )
    )
    items.append(
        ValidationItem(
            "table_block_format",
            _table_blocks_are_valid(output),
            "표 블록은 `표 N x M 시작`과 셀 좌표, `표 N x M 끝` 형식을 지켜야 합니다.",
            priority=4,
        )
    )
    items.append(
        ValidationItem(
            "no_markdown_table",
            not _has_markdown_table(output),
            "마크다운 표를 사용하면 안 됩니다.",
            priority=3,
        )
    )
    items.append(
        ValidationItem(
            "no_html_table",
            not re.search(r"</?(table|tr|td|th)\b", output, re.IGNORECASE),
            "HTML 표를 사용하면 안 됩니다.",
            priority=3,
        )
    )
    items.append(
        ValidationItem(
            "no_bold_marker",
            "**" not in output,
            "마크다운 볼드 기호 `**`를 사용하면 안 됩니다.",
            priority=3,
        )
    )

    forbidden_found = [phrase for phrase in FORBIDDEN_PHRASES if phrase in output]
    items.append(
        ValidationItem(
            "no_forbidden_phrases",
            not forbidden_found,
            f"금지 표현이 없어야 합니다: {', '.join(forbidden_found)}",
            priority=2,
        )
    )

    missing_tokens = _missing_fact_tokens(source, output)
    items.append(
        ValidationItem(
            "source_numbers_preserved",
            not missing_tokens,
            f"원문 숫자/금액 데이터가 누락되면 안 됩니다: {', '.join(missing_tokens[:10])}",
            priority=4,
        )
    )
    items.append(
        ValidationItem(
            "mobile_line_length",
            _mobile_line_length_ok(output),
            "본문 줄 길이가 모바일 가독성 기준에서 지나치게 길면 안 됩니다.",
            priority=1,
        )
    )

    return ValidationReport(items=items)


def _subtitle_format_ok(output: str) -> bool:
    for line in output.splitlines():
        stripped = line.strip()
        if "ㅂㅂㅂ" in stripped and not stripped.startswith("ㅂㅂㅂ"):
            return False
        if stripped.startswith("ㅂㅂㅂ") and not SUBTITLE_RE.match(stripped):
            return False
    return True


def _toc_has_no_subtitle_marker(output: str) -> bool:
    body_start = output.find(BODY_MARKER)
    if body_start == -1:
        return False
    first_subtitle = output.find("ㅂㅂㅂ", body_start)
    toc_region = output[body_start:first_subtitle if first_subtitle != -1 else len(output)]
    for line in toc_region.splitlines():
        stripped = line.strip()
        if re.match(r"^[ㄱ-ㅎ가-힣A-Za-z0-9]+[.)]\s*ㅂㅂㅂ", stripped):
            return False
    return True


def _validate_visit_date(source: str, output: str) -> ValidationItem:
    source_date = extract_visit_date(source)
    output_match = OUTPUT_VISIT_DATE_RE.search(output)
    if not output_match:
        return ValidationItem(
            "visit_date",
            False,
            "`YYYY.MM.DD 방문 기준` 형식의 방문일자가 있어야 합니다.",
            priority=5,
        )
    output_date = date(*(int(part) for part in output_match.groups()))
    if source_date:
        return ValidationItem(
            "visit_date",
            output_date == source_date,
            "원문 방문일자가 있으면 같은 날짜를 사용해야 합니다.",
            priority=5,
        )
    return ValidationItem(
        "visit_date",
        VISIT_START <= output_date <= VISIT_END,
        "자동 방문일자는 2026.05.17부터 2026.06.15 사이여야 합니다.",
        priority=5,
    )


def _source_has_info_data(source: str) -> bool:
    if any(keyword in source for keyword in INFO_KEYWORDS):
        return True
    return bool(re.search(r"\d", source or ""))


def _parse_table_blocks(output: str) -> list[tuple[int, int, list[str]]]:
    lines = output.splitlines()
    blocks: list[tuple[int, int, list[str]]] = []
    idx = 0
    while idx < len(lines):
        start_match = TABLE_START_RE.match(lines[idx].strip())
        if not start_match:
            idx += 1
            continue
        rows, cols = int(start_match.group(1)), int(start_match.group(2))
        cells: list[str] = []
        idx += 1
        while idx < len(lines):
            end_match = TABLE_END_RE.match(lines[idx].strip())
            if end_match:
                blocks.append((rows, cols, cells))
                break
            cells.append(lines[idx].strip())
            idx += 1
        idx += 1
    return blocks


def _table_blocks_are_valid(output: str) -> bool:
    lines = output.splitlines()
    found = False
    idx = 0
    while idx < len(lines):
        start_match = TABLE_START_RE.match(lines[idx].strip())
        if not start_match:
            idx += 1
            continue
        found = True
        rows, cols = int(start_match.group(1)), int(start_match.group(2))
        seen: set[tuple[int, int]] = set()
        idx += 1
        closed = False
        while idx < len(lines):
            stripped = lines[idx].strip()
            end_match = TABLE_END_RE.match(stripped)
            if end_match:
                closed = int(end_match.group(1)) == rows and int(end_match.group(2)) == cols
                break
            cell_match = TABLE_CELL_RE.match(stripped)
            if not cell_match:
                return False
            row, col = int(cell_match.group(1)), int(cell_match.group(2))
            if row >= rows or col >= cols:
                return False
            seen.add((row, col))
            idx += 1
        if not closed:
            return False
        if len(seen) < rows * cols:
            return False
        idx += 1
    return True if found else True


def _has_markdown_table(output: str) -> bool:
    lines = output.splitlines()
    for idx, line in enumerate(lines[:-1]):
        if re.match(r"^\s*\|.*\|\s*$", line) and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[idx + 1]):
            return True
    return False


def _missing_fact_tokens(source: str, output: str) -> list[str]:
    source_without_images = re.sub(r"\[image_\d+\.[^\]]+\]", " ", source or "")
    token_re = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:원|엔|달러|분|시간|km|m|명|개|회|박|일|시|%|개월|년)?")
    source_tokens = {re.sub(r"\s+", "", token) for token in token_re.findall(source_without_images)}
    output_compact = re.sub(r"\s+", "", output or "")
    return sorted(token for token in source_tokens if token and token not in output_compact)


def _mobile_line_length_ok(output: str) -> bool:
    regular_lines = []
    in_table = False
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if TABLE_START_RE.match(stripped):
            in_table = True
            continue
        if TABLE_END_RE.match(stripped):
            in_table = False
            continue
        if in_table:
            continue
        if stripped.startswith(("제목을입력해주세요1:", BODY_MARKER, "ㅂㅂㅂ", "[")):
            continue
        regular_lines.append(stripped)
    if not regular_lines:
        return False
    long_lines = [line for line in regular_lines if len(line) > 35]
    return len(long_lines) <= max(1, int(len(regular_lines) * 0.15))

