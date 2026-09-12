# 단어 데이터로 총 단어 수·총 틀린 횟수·완전히 외운 단어 수를 계산하는 함수
def calculate_stats(words: dict) -> dict:
    wrong_counts = [word["wrong_count"] for word in words.values()]
    return {
        "total_words": len(words),
        "total_wrong_count": sum(wrong_counts),
        "mastered_words": sum(1 for count in wrong_counts if count == 0),
    }
