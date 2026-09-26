# 내 학습 기록(progress.json)을 읽고 쓰는 함수들
import json
from pathlib import Path

DEFAULT_PROGRESS_PATH = "progress.json"
DEFAULT_SETTINGS = {"set_size": 50, "study_days_per_set": 3, "daily_review_limit": 30}


# 학습 기록이 아직 없을 때 쓰는 기본값을 만든다
def default_progress() -> dict:
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "current_set": None,
        "words": {},
        "carry_over": [],
        "quiz_cache": {},
        "my_words": {},
    }


# 내가 직접 추가한 단어를 학습 기록에 넣는다 (뜻은 보관하고, 다음 세트에 먼저 나오도록 이월 목록에)
def add_my_word(progress: dict, word: str, meaning: str) -> dict:
    return migrate_words({word: {"meaning": meaning}}, progress)


# 예전 words.json의 단어를 새 구조로 옮긴다. 내가 적어둔 뜻은 my_words에 보관하고,
# 다음 세트에 먼저 나오도록 이월 목록에 넣는다 (이미 학습 중인 단어는 그대로 둔다)
def migrate_words(old_words: dict, progress: dict) -> dict:
    records = {**progress["words"]}
    my_words = {**progress.get("my_words", {})}
    carry_over = list(progress["carry_over"])
    for word, info in old_words.items():
        my_words[word] = info.get("meaning", "")
        if word in records:
            continue
        records[word] = {"stage": 0, "next_review": None, "recent_results": [], "graduated": False}
        if word not in carry_over:
            carry_over.append(word)
    return {**progress, "words": records, "my_words": my_words, "carry_over": carry_over}


# 저장된 기록에 빠진 항목이 있으면 기본값으로 채운다 (예전 파일에도 새 항목이 생기도록)
def fill_missing_parts(saved: dict) -> dict:
    progress = default_progress()
    progress.update(saved)
    progress["settings"] = {**DEFAULT_SETTINGS, **saved.get("settings", {})}
    return progress


# 학습 기록 파일을 읽는다. 파일이 없으면 기본값을 돌려준다
def load_progress(path: str = DEFAULT_PROGRESS_PATH) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return default_progress()
    return fill_missing_parts(json.loads(file_path.read_text(encoding="utf-8")))


# 학습 기록을 파일에 저장한다. 한국어가 깨지지 않게 ensure_ascii=False로 저장한다
def save_progress(progress: dict, path: str = DEFAULT_PROGRESS_PATH) -> None:
    Path(path).write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
