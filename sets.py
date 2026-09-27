# 50단어 세트를 만들고 관리하는 함수들
from schedule import next_review_date
from wordbank import study_order

NEW_WORD_RECORD = {"stage": 0, "next_review": None, "recent_results": [], "graduated": False}
RESULTS_NEEDED_TO_PASS = 2


# 아직 한 번도 세트에 넣은 적 없는 단어를 외울 순서대로 고른다 (복습 중이거나 졸업한 단어는 건너뛴다)
def pick_new_words(progress: dict, bank: list[dict], count: int) -> list[str]:
    new_words = []
    for entry in study_order(bank, progress["settings"].get("skip_basic_rank", 0)):
        if len(new_words) >= count:
            break
        if entry["word"] not in progress["words"]:
            new_words.append(entry["word"])
    return new_words


# 이 단어가 세트를 통과했는지 본다 (마지막 2번을 연속으로 맞혔으면 통과)
def passed_the_set(record: dict) -> bool:
    results = record["recent_results"]
    return len(results) >= RESULTS_NEEDED_TO_PASS and all(results[-RESULTS_NEEDED_TO_PASS:])


# 세트를 마감한다: 통과한 단어는 1단계 복습으로, 못 한 단어는 다음 세트로 이월한다
def close_set(progress: dict, today: str) -> dict:
    current = progress["current_set"]
    if not current:
        return progress
    records = {**progress["words"]}
    carry_over = []
    for word in current["words"]:
        record = {**records[word], "recent_results": []}
        if record["graduated"]:
            records[word] = record
            continue
        if passed_the_set(records[word]):
            records[word] = {**record, "stage": 1, "next_review": next_review_date(1, today)}
        else:
            records[word] = {**record, "stage": 0, "next_review": None}
            carry_over.append(word)
    return {
        **progress,
        "current_set": None,
        "last_set_number": current["number"],
        "words": records,
        "carry_over": carry_over,
    }


# 오늘 공부했다는 것을 세트에 기록한다 (같은 날 여러 번 공부해도 하루로 센다)
def record_study_day(progress: dict, today: str) -> dict:
    current = progress["current_set"]
    if not current or today in current["study_dates"]:
        return progress
    return {
        **progress,
        "current_set": {**current, "study_dates": [*current["study_dates"], today]},
        # 세트가 바뀌어도 이어지도록 공부한 날 총합을 따로 센다 (진도 예상에 쓰임)
        "total_study_days": progress.get("total_study_days", 0) + 1,
    }


# 공부한 날이 정해진 일수(기본 3일)를 채웠는지 본다 (달력이 아니라 공부한 날 기준)
def is_set_finished(progress: dict) -> bool:
    current = progress["current_set"]
    if not current:
        return False
    return len(current["study_dates"]) >= progress["settings"]["study_days_per_set"]


# 이미 아는 단어로 체크한 것들을 바로 졸업 처리하고, 세트에서 빼고 그만큼 새 단어로 다시 채운다
def mark_known_words(progress: dict, known_words: list[str], bank: list[dict], today: str) -> dict:
    records = {**progress["words"]}
    for word in known_words:
        record = {**records.get(word, NEW_WORD_RECORD)}
        records[word] = {**record, "graduated": True, "next_review": None, "known_on": today}
    updated = {**progress, "words": records}
    if not progress["current_set"]:
        return updated
    kept = [word for word in progress["current_set"]["words"] if word not in known_words]
    refill = pick_new_words(updated, bank, progress["settings"]["set_size"] - len(kept))
    for word in refill:
        records.setdefault(word, dict(NEW_WORD_RECORD))
    return {**updated, "current_set": {**progress["current_set"], "words": kept + refill}}


# 이월된 단어를 먼저 넣고 남은 자리를 새 단어로 채운 새 세트를 시작한다
def start_new_set(progress: dict, bank: list[dict], today: str) -> dict:
    # 이월 목록에 있어도 이미 졸업한 단어는 다시 넣지 않는다 (아는 단어로 체크한 단어 등)
    carried = [word for word in progress["carry_over"] if not progress["words"].get(word, {}).get("graduated")]
    set_size = progress["settings"]["set_size"]
    words = carried + pick_new_words(progress, bank, set_size - len(carried))
    records = {**progress["words"]}
    for word in words:
        records.setdefault(word, dict(NEW_WORD_RECORD))
    # 세트를 마감하면 current_set이 비워지므로, 마지막 세트 번호를 기억해뒀다가 이어서 매긴다
    last_number = progress["current_set"]["number"] if progress["current_set"] else progress.get("last_set_number", 0)
    number = last_number + 1
    new_set = {"number": number, "words": words, "study_dates": []}
    return {**progress, "current_set": new_set, "words": records, "carry_over": []}
