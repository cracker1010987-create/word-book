# wordbook CLI 진입점. add/quiz/stats/list 명령어와 메뉴 모드를 연결한다
import argparse
import os
import sys
import textwrap
from datetime import date
from typing import Any, Callable

from grading import grade_answer
from review import pick_word_to_quiz, record_result
from storage import add_word, load_words, save_words
from stats import calculate_stats
from ai import Quiz, make_quiz_verified

LINE = "=" * 40
THIN_LINE = "-" * 40
MENU = {"1": "단어 추가", "2": "퀴즈 풀기", "3": "통계 보기", "4": "목록 보기", "5": "종료"}


# wordbook 명령어들의 인자 구조를 정의한다
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wordbook")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("word")
    add_parser.add_argument("meaning")

    subparsers.add_parser("quiz")
    subparsers.add_parser("stats")
    subparsers.add_parser("list")

    return parser


# 터미널 화면을 깨끗하게 지운다 (윈도우는 cls, 그 외는 clear)
def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


# 화면 맨 위에 구분선과 제목을 출력한다
def print_header(title: str) -> None:
    print(LINE)
    print(f"  {title}")
    print(LINE)
    print()


# 단어를 추가하고, 새 단어인지 이미 있던 단어인지 화면에 알려준다
def run_add(word: str, meaning: str, path: str) -> None:
    is_new = add_word(word, meaning, path)
    if is_new:
        print(f"'{word}' 단어를 추가했습니다.")
    else:
        print(f"'{word}'는 이미 있는 단어라서 뜻만 업데이트했습니다. (틀린 횟수는 그대로)")


# 퀴즈 예문과 보기를 읽기 좋게 출력한다
def print_question(quiz: Quiz) -> None:
    print(textwrap.fill(quiz.sentence, width=60))
    print()
    for i, option in enumerate(quiz.options, 1):
        print(f"  {i}) {option}")
    print()


# 채점 결과와 해설을 구분선 사이에 출력한다
def print_result(quiz: Quiz, is_correct: bool) -> None:
    print()
    print(THIN_LINE)
    if is_correct:
        print("정답입니다!")
    else:
        print(f"오답입니다. 정답은 '{quiz.answer}' 입니다.")
    print()
    print("해설:")
    print(textwrap.fill(quiz.explanation, width=40))
    print(THIN_LINE)


# 단어 하나를 골라 퀴즈를 내고, 답을 받아 채점한 뒤 결과를 반영하고 알려준다
def run_quiz(
    path: str, chain: Any, grammar_chain: Any, input_func: Callable[[str], str], today: str
) -> None:
    words = load_words(path)
    if not words:
        print("아직 추가된 단어가 없습니다. 먼저 단어를 추가해주세요.")
        return
    word = pick_word_to_quiz(words)
    print("문제를 만드는 중입니다...\n")
    quiz = make_quiz_verified(word, words[word]["meaning"], chain=chain, grammar_chain=grammar_chain)
    print_question(quiz)
    user_answer = input_func("정답 입력 > ")
    is_correct = grade_answer(user_answer, quiz.answer)
    record_result(words, word, is_correct, today)
    save_words(words, path)
    print_result(quiz, is_correct)


# 단어 데이터를 통계로 계산해서 화면에 출력한다
def print_stats(path: str) -> None:
    stats = calculate_stats(load_words(path))
    print(f"  총 단어 수: {stats['total_words']}")
    print(f"  틀린 횟수 합계: {stats['total_wrong_count']}")
    print(f"  완전히 외운 단어 수: {stats['mastered_words']}")


# 추가된 단어 전체를 번호를 붙여 목록으로 보여준다
def print_word_list(path: str) -> None:
    words = load_words(path)
    if not words:
        print("아직 추가된 단어가 없습니다.")
        return
    for i, (word, info) in enumerate(words.items(), 1):
        print(f"  {i}. {word} - {info['meaning']} (틀린 횟수: {info['wrong_count']})")


# 화면을 지우고 메인 메뉴를 그린 뒤, 사용자가 고른 번호를 돌려준다
def ask_menu_choice(input_func: Callable[[str], str], clear_func: Callable[[], None]) -> str:
    clear_func()
    print_header("wordbook")
    for number, label in MENU.items():
        print(f"  {number}. {label}")
    print()
    return input_func("번호 입력 > ").strip()


# 메뉴에서 고른 기능 하나를 실행한다
def run_menu_action(
    choice: str, path: str, chain: Any, grammar_chain: Any,
    input_func: Callable[[str], str], today: str,
) -> None:
    if choice == "1":
        word = input_func("추가할 영어 단어 > ")
        meaning = input_func("뜻 > ")
        run_add(word, meaning, path)
    elif choice == "2":
        run_quiz(path, chain, grammar_chain, input_func, today)
    elif choice == "3":
        print_stats(path)
    elif choice == "4":
        print_word_list(path)
    else:
        print("1~5 중에서 골라주세요.")


# 메뉴 → (화면 지우고) 기능 실행 → 엔터 대기 → 메뉴를 5번(종료)을 고를 때까지 반복한다
def run_interactive(
    path: str, chain: Any, grammar_chain: Any, input_func: Callable[[str], str],
    today: str, clear_func: Callable[[], None],
) -> None:
    while True:
        choice = ask_menu_choice(input_func, clear_func)
        if choice == "5":
            break
        clear_func()
        print_header(MENU.get(choice, "잘못된 입력"))
        run_menu_action(choice, path, chain, grammar_chain, input_func, today)
        input_func("\n엔터를 누르면 메뉴로 돌아갑니다...")


# 명령줄 인자를 받아 알맞은 명령어를 실행한다. 인자가 없으면 메뉴 모드로 들어간다
def main(
    argv: list[str] | None = None,
    path: str = "words.json",
    chain: Any = None,
    grammar_chain: Any = None,
    input_func: Callable[[str], str] = input,
    today: str | None = None,
    clear_func: Callable[[], None] = clear_screen,
) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "add":
        run_add(args.word, args.meaning, path)
    elif args.command == "quiz":
        run_quiz(path, chain, grammar_chain, input_func, today)
    elif args.command == "stats":
        print_stats(path)
    elif args.command == "list":
        print_word_list(path)
    else:
        run_interactive(path, chain, grammar_chain, input_func, today, clear_func)


if __name__ == "__main__":
    main(sys.argv[1:], today=date.today().isoformat())
