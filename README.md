# 하네스&루프

네이버 블로그용 정보성 글을 생성하고, 규칙 검증과 루프 실행으로 가장 좋은 결과물을 고르는 도구입니다.

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`에 `OPENAI_API_KEY`를 입력하면 CLI와 웹 UI에서 함께 사용합니다.

## CLI 실행

```bash
python -m app.main \
  --title "도쿄 후지산 버스 투어 추천 하는 이유" \
  --source-file examples/sample_source.txt \
  --loop \
  --runs 3
```

API 호출 없이 배선만 확인하려면 `mock` 실행 방식을 사용합니다.

```bash
python -m app.main \
  --provider mock \
  --title "도쿄 후지산 버스 투어 추천 하는 이유" \
  --source-file examples/sample_source.txt \
  --loop \
  --runs 3
```

이미 로그인된 AI 에이전트 CLI를 사용하려면 표준 입력으로 프롬프트를 받고 표준 출력으로 결과를 반환하는 명령을 지정합니다.

```bash
AGENT_COMMAND="your-agent-command" \
python -m app.main \
  --provider agent \
  --title "도쿄 후지산 버스 투어 추천 하는 이유" \
  --source-file examples/sample_source.txt
```

## 웹 UI 실행

```bash
streamlit run app/web.py
```

웹 UI에서는 제목, 원문 데이터, API Key, 모델, 루프 체크박스, 루프 횟수, 자동 수정 여부를 입력할 수 있습니다.

## 출력 파일

실행 결과는 `outputs/`에 저장됩니다.

```text
outputs/
├─ run_001.txt
├─ run_002.txt
├─ run_003.txt
├─ best.txt
└─ report.json
```

## 검증 항목

- 제목 완전 일치
- 출력 마커 존재
- 소제목 최소 3개
- 목차의 `ㅂㅂㅂ` 마커 금지
- 이미지 태그 순서 유지
- 방문일자 범위 확인
- 정보성 데이터의 표 생성
- 표 마커 형식 확인
- 마크다운 표와 HTML 표 금지
- 볼드 마커 금지
- 금지 표현 확인
- 원문 숫자 데이터 보존
