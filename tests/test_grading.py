# grade_answer 함수가 정답을 올바르게 채점하는지 확인하는 테스트
from grading import grade_answer


def test_exact_match_passes() -> None:
    # 정확히 같으면 통과
    assert grade_answer("apple", "apple") is True


def test_case_insensitive_passes() -> None:
    # 대소문자만 다르면 통과
    assert grade_answer("Apple", "apple") is True


def test_surrounding_whitespace_passes() -> None:
    # 앞뒤 공백만 다르면 통과
    assert grade_answer("  apple  ", "apple") is True


def test_one_of_multiple_answers_passes() -> None:
    # 정답이 여러 개일 때, 그중 하나만 맞아도 통과
    assert grade_answer("lift", "elevator/lift") is True


def test_wrong_answer_fails() -> None:
    # 완전히 틀리면 실패
    assert grade_answer("banana", "apple") is False


def test_empty_answer_fails() -> None:
    # 빈 문자열은 실패
    assert grade_answer("", "apple") is False
