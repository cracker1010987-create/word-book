# 오늘 풀 문제 목록(세트 단어 + 복습 단어)을 만드는 함수를 확인하는 테스트
from progress import default_progress
from session import build_today_session
from sets import record_study_day, start_new_set

BANK = [{"word": w, "meaning_ko": "뜻", "pos": "noun"} for w in ["alpha", "beta", "gamma", "delta"]]


def progress_with_set(study_dates: list[str], set_size: int = 2) -> dict:
    # 세트를 시작하고 공부한 날을 채워둔 학습 기록을 만든다
    progress = default_progress()
    progress["settings"]["set_size"] = set_size
    progress = start_new_set(progress, BANK, "2026-01-01")
    for day in study_dates:
        progress = record_study_day(progress, day)
    return progress


def review_record(next_review: str) -> dict:
    # 복습할 차례가 된 단어 기록을 만든다
    return {"stage": 1, "next_review": next_review, "recent_results": [], "graduated": False}


def test_first_study_day_asks_meaning_choice() -> None:
    # 세트 1일차에는 '영어 보고 뜻 고르기'로 낸다
    session = build_today_session(progress_with_set([]), BANK, "2026-01-01")
    assert [item["kind"] for item in session] == ["meaning_choice", "meaning_choice"]
    assert [item["word"] for item in session] == ["alpha", "beta"]


def test_second_study_day_asks_to_type_the_english_word() -> None:
    # 2일차에는 '뜻 보고 영어 쓰기'로 낸다
    session = build_today_session(progress_with_set(["2026-01-01"]), BANK, "2026-01-02")
    assert [item["kind"] for item in session] == ["spelling", "spelling"]


def test_third_study_day_asks_the_sentence_quiz() -> None:
    # 3일차에는 예문 빈칸 퀴즈로 낸다
    session = build_today_session(progress_with_set(["2026-01-01", "2026-01-02"]), BANK, "2026-01-03")
    assert [item["kind"] for item in session] == ["sentence", "sentence"]


def test_studying_again_on_the_same_day_keeps_the_same_kind() -> None:
    # 같은 날 다시 들어와도 그날의 퀴즈 종류는 그대로다 (하루로 세기 때문)
    progress = progress_with_set(["2026-01-01"])
    session = build_today_session(progress, BANK, "2026-01-01")
    assert [item["kind"] for item in session] == ["meaning_choice", "meaning_choice"]


def test_review_words_come_first_as_sentence_quizzes() -> None:
    # 복습 단어를 세트 단어보다 먼저, 예문 빈칸 퀴즈로 낸다
    progress = progress_with_set([])
    progress["words"]["gamma"] = review_record("2026-01-01")
    session = build_today_session(progress, BANK, "2026-01-01")
    assert session[0] == {"word": "gamma", "kind": "sentence", "source": "review"}
    assert [item["source"] for item in session] == ["review", "set", "set"]


def test_review_words_follow_the_daily_limit() -> None:
    # 하루 복습 상한을 넘기지 않는다
    progress = progress_with_set([])
    progress["settings"]["daily_review_limit"] = 1
    for word in ["gamma", "delta"]:
        progress["words"][word] = review_record("2026-01-01")
    session = build_today_session(progress, BANK, "2026-01-01")
    assert sum(1 for item in session if item["source"] == "review") == 1


def test_without_a_set_only_reviews_are_given() -> None:
    # 세트가 없으면 복습만 낸다
    progress = default_progress()
    progress["words"]["gamma"] = review_record("2026-01-01")
    session = build_today_session(progress, BANK, "2026-01-01")
    assert session == [{"word": "gamma", "kind": "sentence", "source": "review"}]


def test_nothing_to_study_gives_an_empty_list() -> None:
    # 세트도 복습도 없으면 빈 목록이다
    assert build_today_session(default_progress(), BANK, "2026-01-01") == []
