# 오늘의 학습을 진행하는 함수들 (세트 자동 시작·마감, 문제 내기, 채점, 기록)
import random
import textwrap
from typing import Any, Callable

from ai import pregenerate_sentence_quizzes
from choice_quiz import make_meaning_choice_quiz
from grading import grade_answer
from schedule import update_after_review
from session import build_today_session
from sets import close_set, is_set_finished, mark_known_words, record_study_day, start_new_set
from wordbank import load_word_bank

LINE = "-" * 40
# 문제 종류를 화면에 보여줄 때 쓰는 이름
KIND_NAMES = {"meaning_choice": "뜻 고르기", "spelling": "영어 쓰기", "sentence": "예문 빈칸"}


# 지금 세트 단어 중 예문 퀴즈가 아직 없는 단어만 골라 만들어 채운다
# (아는 단어를 걸러내면 세트 단어가 바뀌므로, 세트를 시작할 때 한 번 만들고 끝내면 빈칸이 생긴다)
def ensure_quiz_cache(
    progress: dict, bank: list[dict], pregenerate: Callable[..., dict] = pregenerate_sentence_quizzes
) -> dict:
    current = progress["current_set"]
    if not current:
        return progress
    missing = [word for word in current["words"] if word not in progress["quiz_cache"]]
    if not missing:
        return progress
    print(f"\n예문 퀴즈 {len(missing)}개를 미리 만드는 중입니다. 2~4분 걸릴 수 있습니다...")
    return {**progress, "quiz_cache": {**progress["quiz_cache"], **pregenerate(missing, bank)}}


# 세트를 마감할 때 통과한 단어와 이월된 단어를 화면에 알려준다
def print_close_summary(before: dict, after: dict) -> None:
    number = before["current_set"]["number"]
    passed = [word for word in before["current_set"]["words"] if after["words"][word]["stage"] == 1]
    carried = after["carry_over"]
    print(f"\n세트 {number} 마감!")
    print(f"  통과({len(passed)}개): {', '.join(passed) if passed else '없음'}")
    print(f"  다음 세트로 이월({len(carried)}개): {', '.join(carried) if carried else '없음'}\n")


# 입력한 "1, 3" 같은 번호들을 실제 단어로 바꾼다 (번호가 아니거나 범위를 벗어나면 무시한다)
def picked_words(answer: str, words: list[str]) -> list[str]:
    picked = []
    for piece in answer.replace(" ", "").split(","):
        if piece.isdigit() and 1 <= int(piece) <= len(words):
            picked.append(words[int(piece) - 1])
    return picked


# 새 세트 단어를 보여주고 이미 아는 단어를 받아 바로 졸업시킨다 (그만큼 새 단어로 채워진다)
def ask_known_words(progress: dict, bank: list[dict], input_func, today: str) -> dict:
    words = progress["current_set"]["words"]
    meanings = {**progress.get("my_words", {}), **{entry["word"]: entry["meaning_ko"] for entry in bank}}
    print(f"\n세트 {progress['current_set']['number']} 단어 {len(words)}개입니다.")
    for number, word in enumerate(words, 1):
        print(f"  {number}) {word} - {meanings.get(word, '')}")
    answer = input_func("\n이미 아는 단어 번호를 쉼표로 입력하세요 (없으면 엔터) > ")
    known = picked_words(answer, words)
    if not known:
        return progress
    print(f"\n아는 단어 {len(known)}개를 졸업 처리하고 새 단어로 채웁니다: {', '.join(known)}")
    return mark_known_words(progress, known, bank, today)


# 세트가 없거나 다 끝났으면 마감하고 새 세트를 시작한다. 세트 단어의 예문 퀴즈도 미리 만들어둔다
def ensure_current_set(
    progress: dict,
    bank: list[dict],
    today: str,
    pregenerate: Callable[..., dict] = pregenerate_sentence_quizzes,
    input_func: Callable[[str], str] | None = None,
) -> dict:
    if progress["current_set"] and not is_set_finished(progress):
        return ensure_quiz_cache(progress, bank, pregenerate=pregenerate)
    if progress["current_set"]:
        closed = close_set(progress, today)
        print_close_summary(progress, closed)
        progress = closed
    progress = start_new_set(progress, bank, today)
    # 아는 단어를 먼저 걸러내야 최종 세트 단어로 예문 퀴즈를 만든다 (헛수고 방지)
    if input_func:
        progress = ask_known_words(progress, bank, input_func, today)
    return ensure_quiz_cache(progress, bank, pregenerate=pregenerate)


# 채점 결과를 기록한다. 세트 단어는 최근 결과에 쌓고, 복습 단어는 복습 단계를 올리거나 내린다
def record_answer(progress: dict, item: dict, is_correct: bool, today: str) -> dict:
    word = item["word"]
    record = progress["words"][word]
    if item["source"] == "review":
        updated = update_after_review(record, is_correct, today)
    else:
        updated = {**record, "recent_results": [*record["recent_results"], is_correct][-2:]}
    carry_over = progress["carry_over"]
    if item["source"] == "review" and not is_correct and word not in carry_over:
        carry_over = [*carry_over, word]
    return {**progress, "words": {**progress["words"], word: updated}, "carry_over": carry_over}


# 보기 목록을 번호를 붙여 보여준다
def print_options(options: list[str]) -> None:
    for number, option in enumerate(options, 1):
        print(f"  {number}) {option}")
    print()


# 보기에서 고른 번호를 실제 보기 내용으로 바꾼다 (번호가 아니면 입력한 그대로 둔다)
def chosen_option(answer: str, options: list[str]) -> str:
    stripped = answer.strip()
    if stripped.isdigit() and 1 <= int(stripped) <= len(options):
        return options[int(stripped) - 1]
    return stripped


# 뜻 고르기 문제를 내고 번호로 답을 받아 채점한다
def ask_meaning_choice(word: str, bank: list[dict], input_func, rng: random.Random) -> bool:
    quiz = make_meaning_choice_quiz(word, bank, rng)
    print(f"{word} 의 뜻은?\n")
    print_options(quiz["options"])
    picked = chosen_option(input_func("번호 입력 > "), quiz["options"])
    correct = picked == quiz["answer"]
    print("정답입니다!" if correct else f"오답입니다. 정답은 '{quiz['answer']}' 입니다.")
    return correct


# 한국어 낱말 뒤에 붙일 목적격 조사를 고른다 (받침이 있으면 '을', 없으면 '를')
def object_particle(word: str) -> str:
    last = word.strip()[-1] if word.strip() else ""
    has_final_consonant = "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28 != 0
    return "을" if has_final_consonant else "를"


# 한국어 낱말 뒤에 받침에 맞는 목적격 조사를 붙인다 ('송장을', '휴가를')
def with_object_particle(word: str) -> str:
    return f"{word}{object_particle(word)}"


# 뜻을 보여주고 영어 단어를 직접 쓰게 한다
def ask_spelling(word: str, meaning: str, input_func) -> bool:
    print(f"'{meaning}'{object_particle(meaning)} 뜻하는 영어 단어는?\n")
    correct = grade_answer(input_func("영어로 입력 > "), word)
    print("정답입니다!" if correct else f"오답입니다. 정답은 '{word}' 입니다.")
    return correct


# 미리 만들어둔 예문 빈칸 퀴즈를 내고 채점한다 (풀 때는 AI를 부르지 않는다)
def ask_sentence(word: str, quiz: dict, input_func) -> bool:
    print(textwrap.fill(quiz["sentence"], width=60) + "\n")
    print_options(quiz["options"])
    picked = chosen_option(input_func("정답 입력 (번호 또는 영어 단어) > "), quiz["options"])
    correct = grade_answer(picked, quiz["answer"])
    print("정답입니다!" if correct else f"오답입니다. 정답은 '{quiz['answer']}' 입니다.")
    if quiz.get("explanation"):
        print("\n해설: " + textwrap.fill(quiz["explanation"], width=40))
    return correct


# 문제 하나를 종류에 맞게 내고 채점 결과를 돌려준다
def ask_item(item: dict, bank: list[dict], progress: dict, input_func, rng: random.Random) -> bool:
    word = item["word"]
    # 단어장 뜻을 먼저 쓰되, 단어장에 없는 내 단어는 내가 적어둔 뜻을 쓴다
    meanings = {**progress.get("my_words", {}), **{entry["word"]: entry["meaning_ko"] for entry in bank}}
    if item["kind"] == "meaning_choice":
        return ask_meaning_choice(word, bank, input_func, rng)
    if item["kind"] == "spelling":
        return ask_spelling(word, meanings.get(word, ""), input_func)
    quiz = progress["quiz_cache"].get(word)
    if not quiz:
        print("(예문 퀴즈를 아직 못 만들어서 영어 쓰기로 대신합니다)\n")
        return ask_spelling(word, meanings.get(word, ""), input_func)
    return ask_sentence(word, quiz, input_func)


# 오늘이 세트 몇 일차이고 어떤 종류의 문제를 푸는지 화면 맨 위에 알려준다
def print_session_header(progress: dict, session: list[dict], today: str) -> None:
    current = progress["current_set"]
    set_items = [item for item in session if item["source"] == "set"]
    reviews = len(session) - len(set_items)
    kind = KIND_NAMES.get(set_items[0]["kind"], "") if set_items else ""
    day = len(current["study_dates"]) + (0 if today in current["study_dates"] else 1) if current else 0
    print(f"\n세트 {current['number'] if current else '-'} · {day}일차 · 오늘 {len(session)}문제")
    print(f"  세트 단어 {len(set_items)}문제({kind}) + 복습 {reviews}문제")


# 오늘 풀 문제를 차례로 내고, 결과를 기록한 학습 기록을 돌려준다
def run_today_session(
    progress: dict,
    bank: list[dict] | None = None,
    today: str = "",
    input_func: Callable[[str], str] = input,
    rng: random.Random | None = None,
    pregenerate: Callable[..., dict] = pregenerate_sentence_quizzes,
) -> dict:
    bank = bank if bank is not None else load_word_bank()
    rng = rng or random.Random()
    progress = ensure_current_set(progress, bank, today, pregenerate=pregenerate, input_func=input_func)
    session = build_today_session(progress, bank, today)
    print_session_header(progress, session, today)
    correct_count = 0
    for number, item in enumerate(session, 1):
        label = "복습" if item["source"] == "review" else "세트 단어"
        print(f"\n{LINE}\n{label} {number}/{len(session)}\n")
        is_correct = ask_item(item, bank, progress, input_func, rng)
        correct_count += int(is_correct)
        progress = record_answer(progress, item, is_correct, today)
    print(f"\n{LINE}\n오늘 {len(session)}문제 중 {correct_count}개를 맞혔습니다.")
    return record_study_day(progress, today)
