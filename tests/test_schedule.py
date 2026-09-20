# 복습 단계와 다음 복습일을 계산하는 함수들을 확인하는 테스트
import pytest

from schedule import due_review_words, next_review_date, update_after_review


def entry(stage: int, results: list[bool] | None = None) -> dict:
    # 테스트용 단어 기록을 짧게 만든다
    return {"stage": stage, "next_review": "2026-01-01", "recent_results": results or [], "graduated": False}


def test_next_review_date_uses_stage_interval() -> None:
    # 단계별 간격: 1단계 3일, 2단계 7일, 3단계 14일, 4단계 30일, 5단계 60일 뒤
    assert next_review_date(1, "2026-01-01") == "2026-01-04"
    assert next_review_date(2, "2026-01-01") == "2026-01-08"
    assert next_review_date(3, "2026-01-01") == "2026-01-15"
    assert next_review_date(4, "2026-01-01") == "2026-01-31"
    assert next_review_date(5, "2026-01-01") == "2026-03-02"


def test_next_review_date_rejects_stage_without_interval() -> None:
    # 복습 단계(1~5)가 아닌 값은 간격이 없으므로 에러를 낸다
    with pytest.raises(ValueError):
        next_review_date(0, "2026-01-01")


def test_correct_review_raises_stage_and_schedules_next() -> None:
    # 복습에서 맞히면 다음 단계로 올라가고, 그 단계의 간격만큼 뒤로 다음 복습일을 잡는다
    updated = update_after_review(entry(1), True, "2026-01-01")
    assert updated["stage"] == 2
    assert updated["next_review"] == "2026-01-08"
    assert updated["graduated"] is False


def test_correct_review_at_last_stage_graduates() -> None:
    # 5단계(60일)까지 맞히면 졸업하고, 더 이상 복습일을 잡지 않는다
    updated = update_after_review(entry(5), True, "2026-01-01")
    assert updated["graduated"] is True
    assert updated["next_review"] is None


def test_wrong_review_sends_word_back_to_the_set() -> None:
    # 복습에서 틀리면 복습 단계에서 빠져(0단계) 다음 세트에서 다시 외운다
    updated = update_after_review(entry(3), False, "2026-01-01")
    assert updated["stage"] == 0
    assert updated["next_review"] is None
    assert updated["graduated"] is False


def test_review_records_recent_results_keeping_last_two() -> None:
    # 최근 정답 여부를 기록하되 마지막 2개만 남긴다 (세트 통과 판정에 쓰임)
    updated = update_after_review(entry(1, [False, True]), True, "2026-01-01")
    assert updated["recent_results"] == [True, True]


def test_update_after_review_does_not_change_the_original_record() -> None:
    # 원래 기록은 그대로 두고 새 기록을 돌려준다 (실수로 덮어쓰는 것을 막기 위해)
    original = entry(1)
    update_after_review(original, True, "2026-01-01")
    assert original["stage"] == 1


def progress_with(words: dict, daily_review_limit: int = 30) -> dict:
    # 테스트용 학습 기록을 짧게 만든다
    return {"settings": {"set_size": 50, "study_days_per_set": 3, "daily_review_limit": daily_review_limit},
            "current_set": None, "words": words, "carry_over": [], "quiz_cache": {}}


def review_word(stage: int, next_review: str | None, graduated: bool = False) -> dict:
    # 테스트용 복습 단어 기록을 짧게 만든다
    return {"stage": stage, "next_review": next_review, "recent_results": [], "graduated": graduated}


def test_due_review_words_picks_only_words_due_today_or_earlier() -> None:
    # 복습일이 오늘이거나 지난 단어만 고른다 (아직 안 된 단어는 놔둔다)
    progress = progress_with({
        "past": review_word(1, "2026-01-05"),
        "today": review_word(2, "2026-01-10"),
        "future": review_word(3, "2026-01-11"),
    })
    assert sorted(due_review_words(progress, "2026-01-10")) == ["past", "today"]


def test_due_review_words_skips_graduated_and_words_still_in_the_set() -> None:
    # 졸업한 단어와 아직 세트에서 외우는 중(0단계, 복습일 없음)인 단어는 복습 대상이 아니다
    progress = progress_with({
        "graduated": review_word(6, None, graduated=True),
        "in_set": review_word(0, None),
        "due": review_word(1, "2026-01-01"),
    })
    assert due_review_words(progress, "2026-01-10") == ["due"]


def test_due_review_words_puts_most_overdue_first() -> None:
    # 오래 밀린 단어부터 낸다
    progress = progress_with({
        "recent": review_word(1, "2026-01-09"),
        "oldest": review_word(1, "2026-01-02"),
        "middle": review_word(1, "2026-01-05"),
    })
    assert due_review_words(progress, "2026-01-10") == ["oldest", "middle", "recent"]


def test_due_review_words_orders_same_date_words_by_alphabet() -> None:
    # 같은 날짜면 단어 순서대로 (실행할 때마다 순서가 바뀌지 않게)
    progress = progress_with({"banana": review_word(1, "2026-01-01"), "apple": review_word(1, "2026-01-01")})
    assert due_review_words(progress, "2026-01-10") == ["apple", "banana"]


def test_due_review_words_uses_daily_limit_from_settings() -> None:
    # 하루 복습 상한(설정값)까지만 고른다
    words = {f"w{i}": review_word(1, f"2026-01-0{i}") for i in range(1, 6)}
    assert len(due_review_words(progress_with(words, daily_review_limit=2), "2026-01-10")) == 2


def test_due_review_words_limit_can_be_given_directly() -> None:
    # 상한을 직접 넘기면 설정값 대신 그 값을 쓴다
    words = {f"w{i}": review_word(1, f"2026-01-0{i}") for i in range(1, 6)}
    assert due_review_words(progress_with(words), "2026-01-10", limit=3) == ["w1", "w2", "w3"]
