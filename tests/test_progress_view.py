# 진도 보기(전체 중 몇 개를 외웠는지, 예상 완주일)를 계산하는 함수를 확인하는 테스트
from progress import default_progress
from stats import calculate_progress

BANK = [{"word": f"w{i}", "meaning_ko": "뜻", "pos": "noun"} for i in range(10)]


def progress_with(words: dict, total_study_days: int = 0) -> dict:
    # 테스트용 학습 기록을 만든다
    record = default_progress()
    record["words"] = words
    record["total_study_days"] = total_study_days
    return record


def word_record(stage: int, graduated: bool = False) -> dict:
    # 테스트용 단어 기록을 짧게 만든다
    return {"stage": stage, "next_review": None, "recent_results": [], "graduated": graduated}


def test_counts_words_by_state() -> None:
    # 전체 단어를 졸업/복습 중/세트에서 외우는 중/아직 안 본 것으로 나눠 센다
    words = {
        "w0": word_record(6, graduated=True),
        "w1": word_record(6, graduated=True),
        "w2": word_record(2),
        "w3": word_record(0),
    }
    result = calculate_progress(progress_with(words), BANK, "2026-01-10")
    assert result["total"] == 10
    assert result["graduated"] == 2
    assert result["reviewing"] == 1
    assert result["in_set"] == 1
    assert result["not_started"] == 6


def test_percent_is_based_on_graduated_words() -> None:
    # 진도율은 졸업한 단어 기준으로 계산한다
    words = {f"w{i}": word_record(6, graduated=True) for i in range(3)}
    assert calculate_progress(progress_with(words), BANK, "2026-01-10")["percent"] == 30.0


def test_estimates_the_finish_date_from_recent_pace() -> None:
    # 지금까지 공부한 날과 시작한 단어 수로 하루 속도를 구해 완주일을 어림잡는다
    # 4단어를 2일 만에 시작했으면 하루 2단어, 남은 6단어는 3일 → 1월 13일
    words = {f"w{i}": word_record(1) for i in range(4)}
    result = calculate_progress(progress_with(words, total_study_days=2), BANK, "2026-01-10")
    assert result["days_left"] == 3
    assert result["finish_date"] == "2026-01-13"


def test_no_estimate_before_the_first_study_day() -> None:
    # 아직 하루도 공부하지 않았으면 완주일을 어림잡지 않는다
    result = calculate_progress(progress_with({}), BANK, "2026-01-10")
    assert result["days_left"] is None
    assert result["finish_date"] is None


def test_my_own_words_are_counted_in_the_total() -> None:
    # 단어장에 없는 내 단어도 외우는 단어이므로 전체 수에 넣는다
    # (안 넣으면 진도가 100%를 넘고 "아직 안 본 단어"가 음수가 된다)
    progress = default_progress()
    progress["words"] = {
        "apple": {"stage": 0, "next_review": None, "recent_results": [], "graduated": True},
        "elaborate": {"stage": 0, "next_review": None, "recent_results": [], "graduated": True},
    }
    bank = [{"word": "apple", "meaning_ko": "사과", "pos": "other"}]
    result = calculate_progress(progress, bank, "2026-09-28")
    assert result["total"] == 2
    assert result["percent"] == 100.0
    assert result["not_started"] == 0


def test_total_is_the_bank_size_when_every_word_comes_from_the_bank() -> None:
    # 평소(내 단어가 없을 때)는 단어장 크기가 그대로 전체 수다
    progress = default_progress()
    progress["words"] = {"apple": {"stage": 0, "next_review": None, "recent_results": [], "graduated": True}}
    bank = [{"word": "apple", "meaning_ko": "사과", "pos": "other"},
            {"word": "brave", "meaning_ko": "용감한", "pos": "other"}]
    assert calculate_progress(progress, bank, "2026-09-28")["total"] == 2
