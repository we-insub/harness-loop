from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from .config import DEFAULT_MODEL, DEFAULT_OUTPUT_DIR, DEFAULT_PROMPTS_DIR
from .runner import RunOptions, run_harness


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        title = args.title or input("제목: ").strip()
        source = _read_source(args)
        api_key = _resolve_api_key(args)
        options = RunOptions(
            provider=args.provider,
            api_key=api_key,
            model=args.model,
            prompts_dir=Path(args.prompts_dir),
            output_dir=Path(args.output_dir),
            loop=args.loop or args.runs > 1,
            runs=args.runs,
            auto_repair=not args.no_repair,
            temperature=args.temperature,
            agent_command=args.agent_command,
        )
        result = run_harness(title, source, options)
    except KeyboardInterrupt:
        print("\n중단했습니다.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"실패: {exc}", file=sys.stderr)
        return 1

    print(f"best: {result.best_path}")
    print(f"report: {result.report_path}")
    print(f"score: {result.best_record.report.score}/{result.best_record.report.max_score}")
    if result.best_record.report.failures:
        print("failures:")
        for item in result.best_record.report.failures:
            print(f"- {item.name}: {item.message}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="네이버 블로그 글 생성 하네스&루프")
    parser.add_argument("--title", help="사용자가 준 제목. 한 글자도 바꾸지 않고 출력합니다.")
    parser.add_argument("--source", help="원문 데이터 문자열")
    parser.add_argument("--source-file", help="원문 데이터 파일 경로")
    parser.add_argument("--provider", choices=["openai", "agent", "mock"], default="openai", help="생성 실행 방식")
    parser.add_argument("--api-key", help="OpenAI API Key. 생략하면 OPENAI_API_KEY를 사용합니다.")
    parser.add_argument("--agent-command", default=os.getenv("AGENT_COMMAND"), help="agent 실행 방식에서 사용할 CLI 명령")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", DEFAULT_MODEL), help="OpenAI 모델명")
    parser.add_argument("--loop", action="store_true", help="N회 반복 생성을 실행합니다.")
    parser.add_argument("--runs", type=int, default=1, help="루프 실행 횟수")
    parser.add_argument("--no-repair", action="store_true", help="자동 수정 단계를 건너뜁니다.")
    parser.add_argument("--temperature", type=float, default=0.4, help="생성 temperature")
    parser.add_argument("--prompts-dir", default=str(DEFAULT_PROMPTS_DIR), help="프롬프트 파일 디렉토리")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="결과 저장 디렉토리")
    return parser.parse_args(argv)


def _read_source(args: argparse.Namespace) -> str:
    if args.source_file:
        return Path(args.source_file).read_text(encoding="utf-8")
    if args.source:
        return args.source
    if sys.stdin.isatty():
        print("원문 데이터를 입력한 뒤 Ctrl-D로 종료하세요.", file=sys.stderr)
    return sys.stdin.read()


def _resolve_api_key(args: argparse.Namespace) -> str | None:
    if args.provider != "openai":
        return None
    if args.api_key:
        return args.api_key
    if os.getenv("OPENAI_API_KEY"):
        return None
    if sys.stdin.isatty():
        value = getpass.getpass("OpenAI API Key (엔터 시 .env/환경변수 사용): ").strip()
        return value or None
    return None


if __name__ == "__main__":
    raise SystemExit(main())
