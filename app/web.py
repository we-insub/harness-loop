from __future__ import annotations

from pathlib import Path

import streamlit as st

try:
    from .config import DEFAULT_MODEL, DEFAULT_OUTPUT_DIR, DEFAULT_PROMPTS_DIR
    from .runner import RunOptions, run_harness
except ImportError:  # Streamlit executes script files outside package mode.
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from app.config import DEFAULT_MODEL, DEFAULT_OUTPUT_DIR, DEFAULT_PROMPTS_DIR
    from app.runner import RunOptions, run_harness


def main() -> None:
    st.set_page_config(page_title="하네스&루프", layout="wide")
    st.title("하네스&루프")

    left, right = st.columns([0.42, 0.58], gap="large")

    with left:
        title = st.text_input("제목")
        source = st.text_area("원문 데이터", height=320)
        provider = st.selectbox("실행 방식", ["openai", "agent", "mock"], index=0)
        api_key = st.text_input("API Key", type="password", disabled=provider != "openai")
        model = st.text_input("모델", value=DEFAULT_MODEL, disabled=provider != "openai")
        agent_command = st.text_input("Agent command", disabled=provider != "agent")
        loop = st.checkbox("루프 돌리기")
        runs = st.number_input("루프 횟수", min_value=1, max_value=20, value=3, disabled=not loop)
        auto_repair = st.checkbox("자동 수정", value=True)
        temperature = st.slider("temperature", min_value=0.0, max_value=1.5, value=0.4, step=0.1)
        run_button = st.button("생성", type="primary", use_container_width=True)

    with right:
        if run_button:
            if not title.strip():
                st.error("제목을 입력하세요.")
                return
            if not source.strip():
                st.error("원문 데이터를 입력하세요.")
                return
            options = RunOptions(
                provider=provider,
                api_key=api_key or None,
                model=model or DEFAULT_MODEL,
                prompts_dir=Path(DEFAULT_PROMPTS_DIR),
                output_dir=Path(DEFAULT_OUTPUT_DIR),
                loop=loop,
                runs=int(runs),
                auto_repair=auto_repair,
                temperature=float(temperature),
                agent_command=agent_command or None,
            )
            try:
                with st.spinner("생성 중"):
                    result = run_harness(title, source, options)
            except Exception as exc:
                st.error(str(exc))
                return

            report = result.best_record.report
            st.success(f"best.txt 저장 완료 · 점수 {report.score}/{report.max_score}")
            st.text_area("best.txt", value=result.best_text, height=520)
            st.download_button(
                "best.txt 다운로드",
                data=result.best_text,
                file_name="best.txt",
                mime="text/plain",
                use_container_width=True,
            )

            st.subheader("검증 결과")
            for item in report.items:
                if item.passed:
                    st.write(f"통과 · {item.name}")
                else:
                    st.error(f"실패 · {item.name} · {item.message}")
        else:
            st.info("입력 후 생성 버튼을 누르세요.")


if __name__ == "__main__":
    main()
