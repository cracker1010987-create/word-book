# pick_word_to_quiz, record_result 함수를 확인하는 테스트
from review import pick_word_to_quiz, record_result


def test_picks_word_with_most_wrong_count() -> None:
    # 틀린 횟수가 가장 많은 단어가 선택된다
    words = {
        "apple": {"meaning": "사과", "wrong_count": 3},
        "banana": {"meaning": "바나나", "wrong_count": 1},
    }
    assert pick_word_to_quiz(words) == "apple"


def test_picks_the_only_word() -> None:
    # 단어가 하나뿐이면 그 단어가 선택된다
    words = {"apple": {"meaning": "사과", "wrong_count": 0}}
    assert pick_word_to_quiz(words) == "apple"


def test_returns_one_of_the_words_when_counts_are_equal() -> None:
    # 틀린 횟수가 모두 같아도 에러 없이 단어 목록 중 하나를 돌려준다
    words = {
        "apple": {"meaning": "사과", "wrong_count": 0},
        "banana": {"meaning": "바나나", "wrong_count": 0},
    }
    assert pick_word_to_quiz(words) in words


def test_wrong_answer_increments_wrong_count() -> None:
    # 틀리면 wrong_count가 1 늘어난다
    words = {"apple": {"meaning": "사과", "wrong_count": 0}}
    record_result(words, "apple", False, "2026-01-01")
    assert words["apple"]["wrong_count"] == 1


def test_wrong_answer_sets_last_wrong_date() -> None:
    # 틀리면 last_wrong_date가 today로 기록된다
    words = {"apple": {"meaning": "사과", "wrong_count": 0}}
    record_result(words, "apple", False, "2026-01-01")
    assert words["apple"]["last_wrong_date"] == "2026-01-01"


def test_correct_answer_decrements_wrong_count() -> None:
    # 맞히면 wrong_count가 1 줄어든다 (계속 맞히면 우선순위가 낮아지도록)
    words = {"apple": {"meaning": "사과", "wrong_count": 2}}
    record_result(words, "apple", True, "2026-01-01")
    assert words["apple"]["wrong_count"] == 1


def test_correct_answer_does_not_go_below_zero() -> None:
    # wrong_count가 이미 0이면 맞혀도 음수가 되지 않는다
    words = {"apple": {"meaning": "사과", "wrong_count": 0}}
    record_result(words, "apple", True, "2026-01-01")
    assert words["apple"]["wrong_count"] == 0


def test_correct_answer_does_not_set_last_wrong_date() -> None:
    # 맞히면 last_wrong_date가 새로 기록되지 않는다
    words = {"apple": {"meaning": "사과", "wrong_count": 2}}
    record_result(words, "apple", True, "2026-01-01")
    assert "last_wrong_date" not in words["apple"]
