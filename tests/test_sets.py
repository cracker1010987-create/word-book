# 세트를 만들고 관리하는 함수들을 확인하는 테스트
from progress import default_progress
from sets import start_new_set

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
