# wordbook CLI 진입점. add/quiz/stats 명령어를 연결한다
import argparse
import sys
from datetime import date
from typing import Any, Callable

from grading import grade_answer
from review import pick_word_to_quiz, record_result
from storage import add_word, load_words, save_words
from stats import calculate_stats
from ai import make_quiz_verified


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


# 단어를 추가하고, 새 단어인지 이미 있던 단어인지 화면에 알려준다
def run_add(word: str, meaning: str, path: str) -> None:
    is_new = add_word(word, meaning, path)
    if is_new:
        print(f"'{word}' 단어를 추가했습니다.")
    else:
        print(f"'{word}'는 이미 있는 단어라서 뜻만 업데이트했습니다. (틀린 횟수는 그대로)")


# 단어 하나를 골라 퀴즈를 내고, 답을 받아 채점한 뒤 결과를 반영하고 알려준다
def run_quiz(
    path: str, chain: Any, grammar_chain: Any, input_func: Callable[[str], str], today: str
) -> None:
    words = load_words(path)
    if not words:
        print("아직 추가된 단어가 없습니다. 먼저 단어를 추가해주세요.")
        return
    word = pick_word_to_quiz(words)
    quiz = make_quiz_verified(word, words[word]["meaning"], chain=chain, grammar_chain=grammar_chain)
    print(quiz.sentence)
    for i, option in enumerate(quiz.options, 1):
        print(f"{i}. {option}")
    user_answer = input_func("정답을 입력하세요: ")
    is_correct = grade_answer(user_answer, quiz.answer)
    record_result(words, word, is_correct, today)
    save_words(words, path)
    if is_correct:
        print(f"정답입니다! {quiz.explanation}")
    else:
        print(f"오답입니다. 정답은 '{quiz.answer}' 입니다. {quiz.explanation}")


# 단어 데이터를 통계로 계산해서 화면에 출력한다
def print_stats(path: str) -> None:
    stats = calculate_stats(load_words(path))
    print(f"총 단어 수: {stats['total_words']}")
    print(f"틀린 횟수 합계: {stats['total_wrong_count']}")
    print(f"완전히 외운 단어 수: {stats['mastered_words']}")


# 추가된 단어 전체를 목록으로 보여준다
def print_word_list(path: str) -> None:
    words = load_words(path)
    if not words:
        print("아직 추가된 단어가 없습니다.")
        return
    for word, info in words.items():
        print(f"{word} - {info['meaning']} (틀린 횟수: {info['wrong_count']})")


# 명령어를 직접 안 쳐도 되게, 번호를 고르는 메뉴를 계속 보여준다
def run_interactive(
    path: str, chain: Any, grammar_chain: Any, input_func: Callable[[str], str], today: str
) -> None:
    while True:
        print("1. 단어 추가\n2. 퀴즈 풀기\n3. 통계 보기\n4. 목록 보기\n5. 종료")
        choice = input_func("번호를 입력하세요: ")
        if choice == "1":
            word = input_func("추가할 영어 단어: ")
            meaning = input_func("뜻: ")
            run_add(word, meaning, path)
        elif choice == "2":
            run_quiz(path, chain, grammar_chain, input_func, today)
        elif choice == "3":
            print_stats(path)
        elif choice == "4":
            print_word_list(path)
        elif choice == "5":
            break


# 명령줄 인자를 받아 알맞은 명령어를 실행한다. 인자가 없으면 메뉴 모드로 들어간다
def main(
    argv: list[str] | None = None,
    path: str = "words.json",
    chain: Any = None,
    grammar_chain: Any = None,
    input_func: Callable[[str], str] = input,
    today: str | None = None,
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
        run_interactive(path, chain, grammar_chain, input_func, today)


if __name__ == "__main__":
    main(sys.argv[1:], today=date.today().isoformat())
