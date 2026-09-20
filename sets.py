# 50단어 세트를 만들고 관리하는 함수들
NEW_WORD_RECORD = {"stage": 0, "next_review": None, "recent_results": [], "graduated": False}


# 아직 한 번도 세트에 넣은 적 없는 단어를 단어장 순서대로 고른다 (복습 중이거나 졸업한 단어는 건너뛴다)
def pick_new_words(progress: dict, bank: list[dict], count: int) -> list[str]:
    new_words = []
    for entry in bank:
        if len(new_words) >= count:
            break
        if entry["word"] not in progress["words"]:
            new_words.append(entry["word"])
    return new_words


# 이월된 단어를 먼저 넣고 남은 자리를 새 단어로 채운 새 세트를 시작한다
def start_new_set(progress: dict, bank: list[dict], today: str) -> dict:
    carried = list(progress["carry_over"])
    set_size = progress["settings"]["set_size"]
    words = carried + pick_new_words(progress, bank, set_size - len(carried))
    records = {**progress["words"]}
    for word in words:
        records.setdefault(word, dict(NEW_WORD_RECORD))
    number = progress["current_set"]["number"] + 1 if progress["current_set"] else 1
    new_set = {"number": number, "words": words, "study_dates": []}
    return {**progress, "current_set": new_set, "words": records, "carry_over": []}
