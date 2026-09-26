# 오늘의 학습(세트 자동 시작·마감, 문제 내고 채점하고 기록)을 확인하는 테스트
import random

from progress import default_progress
from sets import record_study_day, start_new_set
from study import (
    ask_item,
    ensure_current_set,
    ensure_quiz_cache,
    record_answer,
    run_today_session,
    with_object_particle,
)

BANK = [
    {"word": "invoice", "meaning_ko": "송장", "pos": "noun", "definition_en": ""},
    {"word": "warranty", "meaning_ko": "보증", "pos": "noun", "definition_en": ""},
    {"word": "refund", "meaning_ko": "환불", "pos": "noun", "definition_en": ""},
    {"word": "tenant", "meaning_ko": "세입자", "pos": "noun", "definition_en": ""},
]
CACHED_QUIZ = {
    "sentence": "Please pay the ___ within 30 days.",
    "options": ["invoice", "receipt", "estimate", "manifest"],
    "answer": "invoice",
    "explanation": "해설",
}


def small_progress(set_size: int = 2) -> dict:
    # 세트 크기를 작게 한 학습 기록을 만든다
    progress = default_progress()
    progress["settings"]["set_size"] = set_size
    return progress


def fake_pregenerate(words, bank, **kwargs) -> dict:
    # 실제 API 대신, 단어마다 미리 만든 예문 퀴즈가 있다고 치는 가짜 생성기
    return {word: {**CACHED_QUIZ, "answer": word, "options": [word, "aaa", "bbb", "ccc"]} for word in words}


def test_ensure_current_set_starts_the_first_set_and_caches_quizzes() -> None:
    # 세트가 없으면 새로 시작하고, 그 세트 단어의 예문 퀴즈를 미리 만들어 저장해둔다
    progress = ensure_current_set(small_progress(), BANK, "2026-01-01", pregenerate=fake_pregenerate)
    assert progress["current_set"]["words"] == ["invoice", "warranty"]
    assert sorted(progress["quiz_cache"]) == ["invoice", "warranty"]


def test_ensure_current_set_keeps_an_unfinished_set() -> None:
    # 아직 3일을 안 채운 세트는 그대로 둔다
    started = ensure_current_set(small_progress(), BANK, "2026-01-01", pregenerate=fake_pregenerate)
    again = ensure_current_set(started, BANK, "2026-01-02", pregenerate=fake_pregenerate)
    assert again["current_set"]["number"] == 1


def test_ensure_current_set_closes_a_finished_set_and_starts_the_next() -> None:
    # 공부한 날 3일을 채운 세트는 마감하고 다음 세트를 시작한다 (통과 못 한 단어는 이월)
    progress = ensure_current_set(small_progress(), BANK, "2026-01-01", pregenerate=fake_pregenerate)
    for day in ["2026-01-01", "2026-01-02", "2026-01-03"]:
        progress = record_study_day(progress, day)
    progress["words"]["invoice"]["recent_results"] = [True, True]
    progress = ensure_current_set(progress, BANK, "2026-01-04", pregenerate=fake_pregenerate)
    assert progress["current_set"]["number"] == 2
    assert progress["words"]["invoice"]["stage"] == 1
    assert "warranty" in progress["current_set"]["words"]


def test_record_answer_for_a_set_word_keeps_the_recent_results() -> None:
    # 세트 단어는 맞았는지 여부를 최근 기록에 쌓는다 (세트 마감 때 통과 판정에 쓰임)
    progress = start_new_set(small_progress(), BANK, "2026-01-01")
    item = {"word": "invoice", "kind": "meaning_choice", "source": "set"}
    progress = record_answer(progress, item, True, "2026-01-01")
    assert progress["words"]["invoice"]["recent_results"] == [True]


def test_record_answer_for_a_review_word_moves_the_stage() -> None:
    # 복습 단어는 맞히면 다음 단계로 올라가고 다음 복습일이 잡힌다
    progress = small_progress()
    progress["words"]["refund"] = {
        "stage": 1, "next_review": "2026-01-01", "recent_results": [], "graduated": False
    }
    item = {"word": "refund", "kind": "sentence", "source": "review"}
    progress = record_answer(progress, item, True, "2026-01-01")
    assert progress["words"]["refund"]["stage"] == 2
    assert progress["words"]["refund"]["next_review"] == "2026-01-08"


def test_ask_item_grades_a_meaning_choice_by_number() -> None:
    # 뜻 고르기 문제는 보기 번호로 답한다
    progress = small_progress()
    item = {"word": "invoice", "kind": "meaning_choice", "source": "set"}
    answers = iter(["1"])
    correct = ask_item(item, BANK, progress, lambda prompt: next(answers), random.Random(1))
    assert isinstance(correct, bool)


def test_ask_item_grades_spelling_by_typing_the_english_word() -> None:
    # 영어 쓰기 문제는 영어 단어를 타이핑해서 맞힌다 (대소문자·공백 무시)
    progress = small_progress()
    item = {"word": "invoice", "kind": "spelling", "source": "set"}
    assert ask_item(item, BANK, progress, lambda prompt: " Invoice ", random.Random(1)) is True
    assert ask_item(item, BANK, progress, lambda prompt: "warranty", random.Random(1)) is False


def test_ask_item_uses_the_cached_sentence_quiz() -> None:
    # 예문 문제는 미리 만들어둔 퀴즈를 쓴다 (풀 때는 AI를 부르지 않는다)
    progress = small_progress()
    progress["quiz_cache"]["invoice"] = CACHED_QUIZ
    item = {"word": "invoice", "kind": "sentence", "source": "set"}
    assert ask_item(item, BANK, progress, lambda prompt: "invoice", random.Random(1)) is True


def test_run_today_session_records_the_study_day_and_answers() -> None:
    # 오늘의 학습을 끝내면 공부한 날이 기록되고, 푼 결과가 남는다
    answers = iter(["invoice", "warranty"])
    progress = run_today_session(
        small_progress(), BANK, "2026-01-01",
        input_func=lambda prompt: next(answers, "invoice"),
        rng=random.Random(1),
        pregenerate=fake_pregenerate,
    )
    assert progress["current_set"]["study_dates"] == ["2026-01-01"]
    assert all(progress["words"][word]["recent_results"] for word in ["invoice", "warranty"])


def test_sentence_quiz_shows_the_explanation(capsys) -> None:
    # 예문 문제를 풀면 해설이 화면에 나온다
    progress = small_progress()
    progress["quiz_cache"]["invoice"] = CACHED_QUIZ
    item = {"word": "invoice", "kind": "sentence", "source": "set"}
    ask_item(item, BANK, progress, lambda prompt: "invoice", random.Random(1))
    assert "해설" in capsys.readouterr().out


def test_quiz_cache_is_filled_for_words_added_after_known_check() -> None:
    # 아는 단어를 걸러내 세트 단어가 바뀌어도, 새로 들어온 단어의 예문 퀴즈를 채워준다
    from sets import mark_known_words
    progress = ensure_current_set(small_progress(), BANK, "2026-01-01", pregenerate=fake_pregenerate)
    progress = mark_known_words(progress, ["invoice"], BANK, "2026-01-01")
    progress = ensure_quiz_cache(progress, BANK, pregenerate=fake_pregenerate)
    assert set(progress["current_set"]["words"]) <= set(progress["quiz_cache"])


def test_sentence_item_without_a_cached_quiz_says_so_instead_of_silently_changing(capsys) -> None:
    # 예문 퀴즈가 없으면 조용히 다른 문제로 바꾸지 말고, 바뀌었다고 알려준다
    progress = small_progress()
    item = {"word": "invoice", "kind": "sentence", "source": "set"}
    ask_item(item, BANK, progress, lambda prompt: "invoice", random.Random(1))
    assert "영어 쓰기" in capsys.readouterr().out


def test_object_particle_follows_the_last_letter() -> None:
    # 받침이 있으면 '을', 없으면 '를' (예: '송장을', '환불을', '뜻하는'는 앞말에 따라)
    assert with_object_particle("송장") == "송장을"
    assert with_object_particle("휴가") == "휴가를"


def test_session_shows_which_day_and_quiz_kind_it_is(capsys) -> None:
    # 오늘이 세트 몇 일차이고 어떤 종류의 문제인지 화면에 보여준다
    run_today_session(
        small_progress(), BANK, "2026-01-01",
        input_func=lambda prompt: "invoice", rng=random.Random(1), pregenerate=fake_pregenerate,
    )
    output = capsys.readouterr().out
    assert "1일차" in output
    assert "뜻 고르기" in output


def test_session_shows_a_summary_when_a_set_is_closed(capsys) -> None:
    # 세트가 마감되면 통과한 단어와 이월된 단어를 알려준다
    progress = ensure_current_set(small_progress(), BANK, "2026-01-01", pregenerate=fake_pregenerate)
    for day in ["2026-01-01", "2026-01-02", "2026-01-03"]:
        progress = record_study_day(progress, day)
    progress["words"]["invoice"]["recent_results"] = [True, True]
    ensure_current_set(progress, BANK, "2026-01-04", pregenerate=fake_pregenerate)
    output = capsys.readouterr().out
    assert "마감" in output
    assert "invoice" in output


def test_session_ends_with_how_many_were_correct(capsys) -> None:
    # 학습이 끝나면 오늘 몇 개를 맞혔는지 알려준다
    run_today_session(
        small_progress(), BANK, "2026-01-01",
        input_func=lambda prompt: "1", rng=random.Random(1), pregenerate=fake_pregenerate,
    )
    assert "오늘" in capsys.readouterr().out


def test_spelling_question_uses_the_right_particle(capsys) -> None:
    # 뜻 뒤에 붙는 조사가 받침에 맞게 나온다 ('송장'을 → 을, '휴가'를 → 를)
    progress = small_progress()
    ask_item({"word": "invoice", "kind": "spelling", "source": "set"}, BANK, progress,
             lambda prompt: "invoice", random.Random(1))
    assert "'송장'을 뜻하는" in capsys.readouterr().out


def test_my_own_word_uses_the_meaning_i_wrote(capsys) -> None:
    # 단어장에 없는 내 단어는 내가 적어둔 뜻으로 문제를 낸다
    progress = small_progress()
    progress["my_words"]["brisk"] = "활기찬, 빠른"
    ask_item({"word": "brisk", "kind": "spelling", "source": "set"}, BANK, progress,
             lambda prompt: "brisk", random.Random(1))
    assert "활기찬, 빠른" in capsys.readouterr().out
