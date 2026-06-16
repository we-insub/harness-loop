from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from typing import Protocol

from .config import DEFAULT_MODEL
from .prompt_builder import PromptInputs, format_visit_date


class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str, *, context: PromptInputs | None = None) -> str:
        ...


class GenerationError(RuntimeError):
    pass


@dataclass
class OpenAIClient:
    api_key: str | None = None
    model: str = DEFAULT_MODEL
    temperature: float = 0.4

    def generate(self, system_prompt: str, user_prompt: str, *, context: PromptInputs | None = None) -> str:
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise GenerationError("OPENAI_API_KEY가 없어서 OpenAI 생성을 실행할 수 없습니다.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise GenerationError("openai 패키지가 설치되어 있지 않습니다. `pip install -r requirements.txt`를 실행하세요.") from exc

        client = OpenAI(api_key=api_key)
        try:
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
            )
        except Exception as exc:  # pragma: no cover - depends on external API
            raise GenerationError(f"OpenAI 생성 실패: {exc}") from exc

        text = getattr(response, "output_text", None)
        if text:
            return text.strip()
        return str(response).strip()


@dataclass
class MockClient:
    """Deterministic local generator for wiring tests and UI smoke checks."""

    def generate(self, system_prompt: str, user_prompt: str, *, context: PromptInputs | None = None) -> str:
        if context is None:
            context = _extract_context_from_prompt(user_prompt)
        return _mock_blog_output(context)


@dataclass
class AgentCommandClient:
    command: str
    timeout_seconds: int = 600

    def generate(self, system_prompt: str, user_prompt: str, *, context: PromptInputs | None = None) -> str:
        if not self.command.strip():
            raise GenerationError("agent 실행 방식에는 AGENT_COMMAND 또는 --agent-command가 필요합니다.")
        full_prompt = f"""SYSTEM PROMPT
{system_prompt}

USER PROMPT
{user_prompt}
"""
        try:
            completed = subprocess.run(
                shlex.split(self.command),
                input=full_prompt,
                text=True,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            raise GenerationError(f"agent command 실행 실패: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise GenerationError(f"agent command가 실패했습니다: {detail}")
        return completed.stdout.strip()


def create_client(
    provider: str,
    api_key: str | None,
    model: str,
    temperature: float = 0.4,
    agent_command: str | None = None,
) -> LLMClient:
    provider = (provider or "openai").lower()
    if provider == "mock":
        return MockClient()
    if provider == "agent":
        return AgentCommandClient(command=agent_command or os.getenv("AGENT_COMMAND", ""))
    if provider == "openai":
        _load_dotenv_if_available()
        return OpenAIClient(api_key=api_key, model=model or DEFAULT_MODEL, temperature=temperature)
    raise GenerationError(f"지원하지 않는 실행 방식입니다: {provider}")


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _extract_context_from_prompt(user_prompt: str) -> PromptInputs:
    title_match = re.search(r"제목:\n(.+?)\n\n", user_prompt, re.DOTALL)
    source_match = re.search(r"원문 데이터:\n(.+?)\n\n검증 전 자체 확인:", user_prompt, re.DOTALL)
    date_match = re.search(r"(20\d{2})\.(\d{2})\.(\d{2})\s*방문 기준", user_prompt)
    from datetime import date

    title = title_match.group(1).strip() if title_match else "제목 없음"
    source = source_match.group(1).strip() if source_match else ""
    visit_date = date(*(int(part) for part in date_match.groups())) if date_match else date(2026, 6, 1)
    from .prompt_builder import extract_image_tags

    return PromptInputs(title=title, source=source, visit_date=visit_date, image_tags=extract_image_tags(user_prompt))


def _mock_blog_output(context: PromptInputs) -> str:
    source_summary = _compact_source(context.source)
    first_images = context.image_tags[:2]
    remaining_images = context.image_tags[2:]
    intro_images = "\n\n".join(first_images)
    extra_image_text = "\n\n".join(remaining_images)

    if intro_images:
        intro_images = f"\n\n{intro_images}\n"
    if extra_image_text:
        extra_image_text = f"\n{extra_image_text}\n"

    return f"""제목을입력해주세요1: {context.title}

본문2:
안녕하세요.

{format_visit_date(context.visit_date)} 방문 기준
확인한 내용입니다.

가격과 일정,
포함 정보를
중심으로 봤습니다.
{intro_images}
ㄱ. 기본정보
ㄴ. 이용 흐름
ㄷ. 확인할 점
ㄹ. 마치며

ㅂㅂㅂ기본정보
원문에 나온
핵심 정보를
먼저 봤습니다.

상품명과 가격,
포함 항목은
본문에서 빠지면
안 되는 부분이거든요.

표 3 x 2 시작
(0,0) 항목
(0,1) 내용
(1,0) 방문일자
(1,1) {format_visit_date(context.visit_date)} 방문 기준
(2,0) 원문 주요정보
(2,1) {source_summary}
표 3 x 2 끝

ㅂㅂㅂ이용 흐름
전체 흐름은
원문 순서를
기준으로 봤습니다.
{extra_image_text}
이미지 태그는
순서가 중요해서
추가하거나
빼지 않았습니다.

일정이나 코스는
원문 표현을
우선 기준으로
확인했습니다.

ㅂㅂㅂ확인할 점
가격과 시간은
방문 기준에 따라
달라질 수 있습니다.

그래서 본문에는
원문에 있는
숫자 정보를
그대로 남겼습니다.

감상은 줄이고
이용 전에 볼
정보 위주로
정리했습니다.

ㅂㅂㅂ마치며
이번 글은
{format_visit_date(context.visit_date)} 방문 기준
정보를 바탕으로
작성했습니다.

제목과 이미지,
표 형식을
함께 확인하면
검수하기 쉽습니다.

필요한 정보가
빠지지 않도록
원문 데이터를
기준으로 마무리했습니다.
"""


def _compact_source(source: str) -> str:
    source = re.sub(r"\[image_\d+\.[^\]]+\]", " ", source or "")
    source = re.sub(r"\s+", " ", source).strip()
    return source[:180] if source else "원문 정보 없음"
