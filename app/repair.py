from __future__ import annotations

from .llm import LLMClient
from .prompt_builder import PromptInputs, format_visit_date
from .validator import ValidationReport


def repair_output(
    client: LLMClient,
    system_prompt: str,
    original_output: str,
    report: ValidationReport,
    inputs: PromptInputs,
) -> str:
    if report.passed:
        return original_output

    failures = "\n".join(f"- {item.name}: {item.message}" for item in report.failures)
    image_tags = "\n".join(inputs.image_tags) if inputs.image_tags else "없음"
    repair_prompt = f"""아래 결과물은 검증에 실패했다.
실패 항목만 고치고, 최종 블로그 글 전체를 다시 출력하라.

절대 유지할 값:
제목: {inputs.title}
방문일자: {format_visit_date(inputs.visit_date)} 방문 기준
이미지 태그:
{image_tags}

실패 항목:
{failures}

원문 데이터:
{inputs.source}

수정 전 결과:
{original_output}
"""
    return client.generate(system_prompt, repair_prompt, context=inputs).strip()

