# 오늘 풀 문제 목록(복습 단어 + 세트 단어)을 만드는 함수들
from schedule import due_review_words

# 세트를 공부한 날 차수에 따라 내는 퀴즈 종류 (쉬운 것 → 어려운 것 순서)
KIND_BY_STUDY_DAY = {1: "meaning_choice", 2: "spelling"}
SENTENCE_KIND = "sentence"
# 복습은 단계마다 종류를 돌려가며 낸다 (같은 예문을 반복해서 보면 문장을 외워버린다)
REVIEW_KINDS = (SENTENCE_KIND, "spelling", "meaning_choice")


# 오늘이 이 세트의 몇 번째 공부한 날인지 센다 (오늘 이미 공부했으면 그날 차수를 그대로 쓴다)
def study_day_number(current_set: dict, today: str) -> int:
    dates = current_set["study_dates"]
    return len(dates) if today in dates else len(dates) + 1


# 그날 차수에 맞는 퀴즈 종류를 고른다 (3일차 이후는 예문 빈칸 퀴즈)
def kind_for_study_day(day: int) -> str:
    return KIND_BY_STUDY_DAY.get(day, SENTENCE_KIND)


# 복습 단계에 맞는 문제 종류를 고른다 (1단계 예문 → 2단계 영어 쓰기 → 3단계 뜻 고르기 → 다시 처음)
def kind_for_review_stage(stage: int) -> str:
    return REVIEW_KINDS[(stage - 1) % len(REVIEW_KINDS)]


# 오늘 풀 문제 목록을 만든다. 복습 단어를 먼저 내고, 그다음 세트 단어를 낸다
def build_today_session(progress: dict, bank: list[dict], today: str) -> list[dict]:
    session = [
        {"word": word, "kind": kind_for_review_stage(progress["words"][word]["stage"]), "source": "review"}
        for word in due_review_words(progress, today)
    ]
    current = progress["current_set"]
    if not current:
        return session
    kind = kind_for_study_day(study_day_number(current, today))
    session.extend({"word": word, "kind": kind, "source": "set"} for word in current["words"])
    return session
