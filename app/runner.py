from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_MODEL, DEFAULT_OUTPUT_DIR, DEFAULT_PROMPTS_DIR
from .llm import create_client
from .prompt_builder import BuiltPrompt, build_prompt
from .repair import repair_output
from .validator import ValidationReport, validate_output


@dataclass(frozen=True)
class RunOptions:
    provider: str = "openai"
    api_key: str | None = None
    model: str = DEFAULT_MODEL
    prompts_dir: Path = DEFAULT_PROMPTS_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    loop: bool = False
    runs: int = 1
    auto_repair: bool = True
    temperature: float = 0.4
    agent_command: str | None = None


@dataclass(frozen=True)
class RunRecord:
    index: int
    output_path: Path
    report: ValidationReport
    repaired: bool
    text: str

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "output_path": str(self.output_path),
            "repaired": self.repaired,
            "report": self.report.to_dict(),
        }


@dataclass(frozen=True)
class RunnerResult:
    records: list[RunRecord]
    best_record: RunRecord
    best_path: Path
    report_path: Path

    @property
    def best_text(self) -> str:
        return self.best_record.text


def run_harness(title: str, source: str, options: RunOptions) -> RunnerResult:
    if not title.strip():
        raise ValueError("제목을 입력해야 합니다.")
    if not source.strip():
        raise ValueError("원문 데이터를 입력해야 합니다.")

    output_dir = Path(options.output_dir)
    prompts_dir = Path(options.prompts_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_count = max(1, int(options.runs if options.loop else 1))
    client = create_client(
        options.provider,
        options.api_key,
        options.model,
        options.temperature,
        options.agent_command,
    )
    records: list[RunRecord] = []

    for index in range(1, run_count + 1):
        built_prompt = build_prompt(title, source, prompts_dir, run_index=index)
        generated = client.generate(
            built_prompt.system_prompt,
            built_prompt.user_prompt,
            context=built_prompt.inputs,
        ).strip()
        report = validate_output(title, source, generated)
        text = generated
        repaired = False

        if options.auto_repair and not report.passed:
            repaired_text = repair_output(
                client,
                built_prompt.system_prompt,
                generated,
                report,
                built_prompt.inputs,
            )
            repaired_report = validate_output(title, source, repaired_text)
            if repaired_report.score >= report.score:
                text = repaired_text
                report = repaired_report
                repaired = True

        output_path = output_dir / f"run_{index:03d}.txt"
        output_path.write_text(text + "\n", encoding="utf-8")
        records.append(
            RunRecord(
                index=index,
                output_path=output_path,
                report=report,
                repaired=repaired,
                text=text,
            )
        )

    best_record = _select_best(records)
    best_path = output_dir / "best.txt"
    report_path = output_dir / "report.json"
    best_path.write_text(best_record.text + "\n", encoding="utf-8")
    report_path.write_text(
        json.dumps(_report_payload(title, source, options, records, best_record), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return RunnerResult(records=records, best_record=best_record, best_path=best_path, report_path=report_path)


def _select_best(records: list[RunRecord]) -> RunRecord:
    if not records:
        raise ValueError("선택할 실행 결과가 없습니다.")
    return sorted(
        records,
        key=lambda record: (
            record.report.score,
            record.report.priority_score(),
            -record.index,
        ),
        reverse=True,
    )[0]


def _report_payload(
    title: str,
    source: str,
    options: RunOptions,
    records: list[RunRecord],
    best_record: RunRecord,
) -> dict:
    prompt_preview: BuiltPrompt = build_prompt(title, source, Path(options.prompts_dir), run_index=best_record.index)
    return {
        "title": title,
        "provider": options.provider,
        "model": options.model,
        "loop": options.loop,
        "runs_requested": max(1, int(options.runs if options.loop else 1)),
        "best_run": best_record.index,
        "best_path": str(DEFAULT_OUTPUT_DIR / "best.txt") if Path(options.output_dir) == DEFAULT_OUTPUT_DIR else str(Path(options.output_dir) / "best.txt"),
        "visit_date": prompt_preview.inputs.visit_date.isoformat(),
        "image_tags": prompt_preview.inputs.image_tags,
        "records": [record.to_dict() for record in records],
    }
