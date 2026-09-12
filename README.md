# wordbook

영어 단어를 저장하고 AI가 퀴즈를 내주는 CLI 앱.

## 처음 실행하기 전에 (한 번만)

1. **가상환경 만들기** (이미 `.venv`가 있으면 건너뛰기)
   ```
   python -m venv .venv
   ```

2. **필요한 패키지 설치**
   ```
   .venv\Scripts\pip install langchain langchain-openai python-dotenv pytest
   ```

3. **API 키 설정** — 프로젝트 루트에 `.env` 파일을 만들고 아래처럼 채운다.
   (`.env`는 `.gitignore`에 이미 포함되어 있어서 깃에 올라가지 않는다.)
   ```
   OPENAI_API_KEY=sk-여기에_실제_키
   ```

## 사용 방법 (메뉴 모드, 추천)

프로젝트 루트(이 폴더)에서 인자 없이 그냥 실행하면 번호로 고르는 메뉴가 뜬다.
```
.venv\Scripts\python.exe .
```
```
1. 단어 추가
2. 퀴즈 풀기
3. 통계 보기
4. 종료
번호를 입력하세요:
```
- **1**을 고르면 추가할 영어 단어 → 뜻 순서로 물어본다.
- **2**를 고르면 가장 많이 틀린 단어(동률이면 그중 하나)로 AI가 영어 예문 퀴즈를 낸다.
  보기 번호가 아니라 **영어 단어를 타이핑**하면 채점 결과와 해설이 나온다.
- **3**을 고르면 총 단어 수 / 틀린 횟수 합계 / 완전히 외운 단어 수를 보여준다.
- **4**를 고르면 종료된다.
- 하나 끝나면 다시 메뉴로 돌아오므로 계속 이어서 쓸 수 있다.

## 명령어 방식 (스크립트에서 자동으로 쓸 때)

메뉴 없이 한 줄로 바로 실행하고 싶을 때 쓴다. `python .`은 `__main__.py`를 실행하는 파이썬 문법이다.

```
.venv\Scripts\python.exe . add <단어> <뜻>
.venv\Scripts\python.exe . quiz
.venv\Scripts\python.exe . stats
```
예:
```
.venv\Scripts\python.exe . add elaborate "정교한, 상세히 설명하다"
```

## 데이터

모든 단어는 프로젝트 루트의 `words.json` 파일 하나에 저장된다 (데이터베이스 없음).

## 테스트

```
.venv\Scripts\python.exe -m pytest -q
```

## 프로젝트 문서

- `prd.md` — 기능 목록과 기술 결정
- `TASKS.md` — 기능을 쪼갠 작업 목록과 완료 현황
- `CLAUDE.md` — 이 프로젝트에서 항상 지키는 규칙
