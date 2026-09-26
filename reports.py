# "이 문제 이상해요" 신고를 학습 기록에 남기는 함수들
SENTENCE_KIND = "sentence"


# 신고를 기록한다. 예문 퀴즈 신고면 미리 만들어둔 퀴즈를 버려서 다음에 새로 만들게 한다
def report_problem(progress: dict, word: str, kind: str, today: str) -> dict:
    report = {"word": word, "kind": kind, "date": today}
    cache = dict(progress["quiz_cache"])
    if kind == SENTENCE_KIND:
        cache.pop(word, None)
    return {**progress, "reports": [*progress.get("reports", []), report], "quiz_cache": cache}


# 신고된 단어를 중복 없이 신고된 순서대로 돌려준다 (나중에 뜻이나 퀴즈를 고칠 때 본다)
def reported_words(progress: dict) -> list[str]:
    words = []
    for report in progress.get("reports", []):
        if report["word"] not in words:
            words.append(report["word"])
    return words
