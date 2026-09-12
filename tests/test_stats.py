# calculate_stats 함수가 단어 데이터로 통계를 잘 계산하는지 확인하는 테스트
from stats import calculate_stats


def test_stats_on_empty_words() -> None:
    # 단어가 하나도 없으면 모두 0이다
    assert calculate_stats({}) == {
        "total_words": 0,
        "total_wrong_count": 0,
        "mastered_words": 0,
    }


def test_stats_counts_total_words() -> None:
    # 총 단어 수를 센다
    words = {
        "apple": {"meaning": "사과", "wrong_count": 0},
        "banana": {"meaning": "바나나", "wrong_count": 2},
    }
    assert calculate_stats(words)["total_words"] == 2


def test_stats_sums_wrong_count() -> None:
    # 틀린 횟수를 전부 더한다
    words = {
        "apple": {"meaning": "사과", "wrong_count": 3},
        "banana": {"meaning": "바나나", "wrong_count": 2},
    }
    assert calculate_stats(words)["total_wrong_count"] == 5


def test_stats_counts_mastered_words() -> None:
    # 한 번도 안 틀린(wrong_count가 0인) 단어 수를 센다
    words = {
        "apple": {"meaning": "사과", "wrong_count": 0},
        "banana": {"meaning": "바나나", "wrong_count": 2},
        "cherry": {"meaning": "체리", "wrong_count": 0},
    }
    assert calculate_stats(words)["mastered_words"] == 2
