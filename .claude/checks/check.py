# 이 프로젝트가 지켜야 할 최소 규칙 세 가지(API 키 하드코딩 금지, .gitignore, pytest 통과)를 검사하는 스크립트
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_DIR_NAMES = {".venv", "venv", ".git", "__pycache__", ".pytest_cache", "node_modules"}

API_KEY_LITERAL = re.compile(r"""["']sk-[A-Za-z0-9_\-]+["']""")
ENV_DIRECT_ASSIGN = re.compile(r"""os\.environ\[[^\]]+\]\s*=\s*["']""")


def find_python_files() -> list[Path]:
    # 검사 대상 .py 파일 목록을 찾는다 (가상환경/캐시/이 스크립트 자신은 제외)
    this_file = Path(__file__).resolve()
    files = []
    for path in PROJECT_ROOT.rglob("*.py"):
        if path.resolve() == this_file:
            continue
        if EXCLUDE_DIR_NAMES & set(path.parts):
            continue
        files.append(path)
    return files


def check_hardcoded_api_key() -> list[str]:
    # .py 파일 안에 API 키가 직접 쓰여 있는지 검사한다
    problems = []
    for path in find_python_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if API_KEY_LITERAL.search(line) or ENV_DIRECT_ASSIGN.search(line):
                rel = path.relative_to(PROJECT_ROOT)
                problems.append(f"[API 키 하드코딩] {rel}:{lineno}: {line.strip()}")
    return problems


def check_gitignore_has_env() -> list[str]:
    # .gitignore에 .env가 포함되어 있는지 검사한다
    gitignore = PROJECT_ROOT / ".gitignore"
    if not gitignore.exists():
        return ["[.gitignore] 파일이 없습니다. .env를 추가해야 합니다."]
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    if ".env" not in lines:
        return ["[.gitignore] .env 항목이 없습니다."]
    return []


def find_python_with_pytest() -> str:
    # pytest가 설치된 파이썬 실행 파일을 찾는다 (.venv 우선, 없으면 현재 인터프리터)
    for candidate in (PROJECT_ROOT / ".venv" / "Scripts" / "python.exe", PROJECT_ROOT / ".venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def check_pytest_passes() -> list[str]:
    # pytest를 실행해서 실패한 테스트가 있는지 검사한다
    python = find_python_with_pytest()
    result = subprocess.run(
        [python, "-m", "pytest", "-q"], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        return ["[pytest 실패]\n" + result.stdout + result.stderr]
    return []


def main() -> None:
    # 세 가지 검사를 모두 실행하고 결과를 출력한다
    problems = check_hardcoded_api_key() + check_gitignore_has_env() + check_pytest_passes()
    if problems:
        for problem in problems:
            print(problem)
        sys.exit(2)
    print("OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
