# 세트를 만들고 관리하는 함수들을 확인하는 테스트
from progress import default_progress
from sets import close_set, is_set_finished, mark_known_words, record_study_day, start_new_set

BANK = [{"word": w, "meaning_ko": "뜻", "pos": "noun"} for w in ["the", "be", "client", "invoice", "flight"]]


def progress_with(set_size: int = 3, **changes) -> dict:
    # 테스트용 학습 기록을 짧게 만든다 (세트 크기를 작게 해서 확인하기 쉽게)
    progress = default_progress()
    progress["settings"]["set_size"] = set_size
    progress.update(changes)
    return progress


def test_start_new_set_fills_with_bank_words_in_order() -> None:
    # 처음에는 단어장 순서대로 세트 크기만큼 채운다
    progress = start_new_set(progress_with(), BANK, "2026-01-01")
    assert progress["current_set"]["words"] == ["the", "be", "client"]
    assert progress["current_set"]["number"] == 1
    assert progress["current_set"]["study_dates"] == []


def test_start_new_set_puts_carried_over_words_first() -> None:
    # 이월된 단어를 먼저 넣고, 남은 자리만 새 단어로 채운다
    before = progress_with(carry_over=["flight"])
    progress = start_new_set(before, BANK, "2026-01-01")
    assert progress["current_set"]["words"] == ["flight", "the", "be"]
    assert progress["carry_over"] == []


def test_start_new_set_skips_words_already_learned_or_in_review() -> None:
    # 이미 복습 중이거나 졸업한 단어는 새 단어로 다시 뽑지 않는다
    before = progress_with(words={
        "the": {"stage": 2, "next_review": "2026-02-01", "recent_results": [], "graduated": False},
        "be": {"stage": 6, "next_review": None, "recent_results": [], "graduated": True},
    })
    progress = start_new_set(before, BANK, "2026-01-01")
    assert progress["current_set"]["words"] == ["client", "invoice", "flight"]


def test_start_new_set_creates_records_for_new_words() -> None:
    # 세트에 새로 들어온 단어는 0단계(세트에서 외우는 중) 기록을 만들어 준다
    progress = start_new_set(progress_with(set_size=1), BANK, "2026-01-01")
    assert progress["words"]["the"] == {
        "stage": 0,
        "next_review": None,
        "recent_results": [],
        "graduated": False,
    }


def test_start_new_set_counts_up_the_set_number() -> None:
    # 세트 번호는 이전 세트 다음 번호로 매긴다
    before = progress_with(current_set={"number": 7, "words": ["old"], "study_dates": ["2026-01-01"]})
    progress = start_new_set(before, BANK, "2026-01-05")
    assert progress["current_set"]["number"] == 8


def test_start_new_set_makes_a_smaller_set_when_bank_runs_out() -> None:
    # 단어장에 남은 단어가 세트 크기보다 적으면, 남은 만큼만으로 세트를 만든다
    progress = start_new_set(progress_with(set_size=10), BANK, "2026-01-01")
    assert progress["current_set"]["words"] == ["the", "be", "client", "invoice", "flight"]


def test_start_new_set_does_not_change_the_original_record() -> None:
    # 원래 기록은 그대로 두고 새 기록을 돌려준다
    before = progress_with()
    start_new_set(before, BANK, "2026-01-01")
    assert before["current_set"] is None
    assert before["words"] == {}


def started_set(set_size: int = 3) -> dict:
    # 세트를 하나 시작한 상태를 만든다 (the, be, client)
    return start_new_set(progress_with(set_size), BANK, "2026-01-01")


def test_mark_known_words_graduates_them_right_away() -> None:
    # 이미 아는 단어로 체크하면 바로 졸업 처리해서, 세트에도 복습에도 다시 나오지 않는다
    progress = mark_known_words(started_set(), ["the"], BANK, "2026-01-01")
    assert progress["words"]["the"]["graduated"] is True
    assert progress["words"]["the"]["next_review"] is None
    assert progress["words"]["the"]["known_on"] == "2026-01-01"


def test_mark_known_words_refills_the_set_with_next_new_words() -> None:
    # 빠진 자리만큼 단어장 다음 순서의 새 단어로 채워서 세트 크기를 유지한다
    progress = mark_known_words(started_set(), ["the", "be"], BANK, "2026-01-01")
    assert progress["current_set"]["words"] == ["client", "invoice", "flight"]


def test_mark_known_words_keeps_the_other_words_in_order() -> None:
    # 체크하지 않은 단어는 원래 순서 그대로 남는다
    progress = mark_known_words(started_set(), ["be"], BANK, "2026-01-01")
    assert progress["current_set"]["words"][:2] == ["the", "client"]


def test_mark_known_words_also_handles_words_outside_the_set() -> None:
    # 세트에 없는 단어를 안다고 체크해도 졸업 처리해서 나중 세트에서 빠지게 한다
    progress = mark_known_words(started_set(), ["flight"], BANK, "2026-01-01")
    assert progress["words"]["flight"]["graduated"] is True
    assert "flight" not in progress["current_set"]["words"]


def test_mark_known_words_with_empty_list_changes_nothing() -> None:
    # 아는 단어가 하나도 없으면 세트가 그대로다
    before = started_set()
    assert mark_known_words(before, [], BANK, "2026-01-01")["current_set"] == before["current_set"]


def test_mark_known_words_does_not_change_the_original_record() -> None:
    # 원래 기록은 그대로 두고 새 기록을 돌려준다
    before = started_set()
    mark_known_words(before, ["the"], BANK, "2026-01-01")
    assert before["current_set"]["words"] == ["the", "be", "client"]
    assert before["words"]["the"]["graduated"] is False


def test_record_study_day_writes_down_today() -> None:
    # 오늘 공부했다는 것을 세트에 기록한다
    progress = record_study_day(started_set(), "2026-01-01")
    assert progress["current_set"]["study_dates"] == ["2026-01-01"]


def test_record_study_day_counts_the_same_day_only_once() -> None:
    # 같은 날 여러 번 공부해도 하루로 센다
    progress = record_study_day(record_study_day(started_set(), "2026-01-01"), "2026-01-01")
    assert progress["current_set"]["study_dates"] == ["2026-01-01"]


def test_record_study_day_adds_each_new_day_in_order() -> None:
    # 다른 날 공부하면 순서대로 쌓인다 (빠진 날은 세지 않는다)
    progress = record_study_day(record_study_day(started_set(), "2026-01-01"), "2026-01-05")
    assert progress["current_set"]["study_dates"] == ["2026-01-01", "2026-01-05"]


def test_set_is_not_finished_before_three_study_days() -> None:
    # 공부한 날이 3일이 안 되면 세트는 아직 안 끝났다
    progress = record_study_day(record_study_day(started_set(), "2026-01-01"), "2026-01-02")
    assert is_set_finished(progress) is False


def test_set_is_finished_after_three_study_days() -> None:
    # 공부한 날이 3일이 되면 세트가 끝난다 (달력으로 3일이 아니라 공부한 날 기준)
    progress = started_set()
    for day in ["2026-01-01", "2026-01-08", "2026-01-20"]:
        progress = record_study_day(progress, day)
    assert is_set_finished(progress) is True


def test_without_a_set_nothing_is_recorded_and_it_is_not_finished() -> None:
    # 아직 세트를 시작하지 않았으면 기록할 것도 없고, 끝난 것도 아니다
    before = progress_with()
    assert record_study_day(before, "2026-01-01")["current_set"] is None
    assert is_set_finished(before) is False


def test_record_study_day_does_not_change_the_original_record() -> None:
    # 원래 기록은 그대로 두고 새 기록을 돌려준다
    before = started_set()
    record_study_day(before, "2026-01-01")
    assert before["current_set"]["study_dates"] == []


def set_with_results(results_by_word: dict, graduated: list[str] | None = None) -> dict:
    # 세트를 3일 공부한 상태를 만들고, 단어별 최근 정답 여부를 채워 넣는다
    progress = started_set()
    for day in ["2026-01-01", "2026-01-02", "2026-01-03"]:
        progress = record_study_day(progress, day)
    for word, results in results_by_word.items():
        progress["words"][word] = {**progress["words"][word], "recent_results": results}
    for word in graduated or []:
        progress["words"][word] = {**progress["words"][word], "graduated": True}
    return progress


def test_close_set_starts_review_for_words_answered_right_twice_in_a_row() -> None:
    # 마지막 2번을 연속으로 맞힌 단어는 통과해서 1단계 복습(3일 뒤)으로 넘어간다
    progress = close_set(set_with_results({"the": [True, True]}), "2026-01-03")
    assert progress["words"]["the"]["stage"] == 1
    assert progress["words"]["the"]["next_review"] == "2026-01-06"
    assert "the" not in progress["carry_over"]


def test_close_set_carries_over_words_that_were_not_answered_right_twice() -> None:
    # 마지막 2번 연속이 아니면 통과 못 하고 다음 세트로 이월된다
    # client는 통과시켜서, 맞·틀(the)과 한 번만 푼 경우(be)만 이월되는지 본다
    results = {"the": [True, False], "be": [True], "client": [True, True]}
    progress = close_set(set_with_results(results), "2026-01-03")
    assert progress["carry_over"] == ["the", "be"]
    assert progress["words"]["the"]["stage"] == 0
    assert progress["words"]["the"]["next_review"] is None


def test_close_set_ignores_words_marked_as_already_known() -> None:
    # 이미 아는 단어로 체크해 졸업한 단어는 이월도, 복습 예약도 하지 않는다
    progress = close_set(set_with_results({"the": [True, True]}, graduated=["the"]), "2026-01-03")
    assert "the" not in progress["carry_over"]
    assert progress["words"]["the"]["next_review"] is None


def test_close_set_clears_the_current_set_and_recent_results() -> None:
    # 세트를 닫으면 현재 세트가 비워지고, 최근 정답 기록도 초기화된다 (다음 세트는 새로 판정)
    progress = close_set(set_with_results({"the": [True, True], "be": [False, False]}), "2026-01-03")
    assert progress["current_set"] is None
    assert progress["words"]["the"]["recent_results"] == []
    assert progress["words"]["be"]["recent_results"] == []


def test_close_set_keeps_carry_over_in_set_order() -> None:
    # 이월 순서는 세트에 있던 순서를 따른다 (the, be, client 순)
    progress = close_set(set_with_results({"the": [False], "be": [True, True], "client": [False]}), "2026-01-03")
    assert progress["carry_over"] == ["the", "client"]


def test_close_set_without_a_set_changes_nothing() -> None:
    # 세트가 없으면 아무것도 바뀌지 않는다
    before = progress_with()
    assert close_set(before, "2026-01-03") == before


def test_close_set_does_not_change_the_original_record() -> None:
    # 원래 기록은 그대로 두고 새 기록을 돌려준다
    before = set_with_results({"the": [True, True]})
    close_set(before, "2026-01-03")
    assert before["current_set"] is not None
    assert before["words"]["the"]["stage"] == 0


def test_record_study_day_also_counts_total_study_days() -> None:
    # 세트가 바뀌어도 이어지도록, 공부한 날 총합도 따로 센다 (진도 예상에 쓰임)
    progress = record_study_day(record_study_day(started_set(), "2026-01-01"), "2026-01-02")
    assert progress["total_study_days"] == 2
    assert record_study_day(progress, "2026-01-02")["total_study_days"] == 2
