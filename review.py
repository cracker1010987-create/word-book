# 틀린 횟수가 가장 많은 단어를 골라 다음 퀴즈로 출제하는 함수
def pick_word_to_quiz(words: dict) -> str:
    return max(words, key=lambda word: words[word]["wrong_count"])


# 채점 결과를 반영하는 함수. 맞히면 wrong_count를 내리고(0 밑으로는 안 내려감),
# 틀리면 wrong_count를 올리고 last_wrong_date를 기록한다
def record_result(words: dict, word: str, is_correct: bool, today: str) -> None:
    if is_correct:
        words[word]["wrong_count"] = max(0, words[word]["wrong_count"] - 1)
        return
    words[word]["wrong_count"] += 1
    words[word]["last_wrong_date"] = today
