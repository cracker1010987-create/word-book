# 내 학습 기록(progress.json)을 읽고 쓰는 함수들
import json
from pathlib import Path

DEFAULT_PROGRESS_PATH = "progress.json"
# 처음 쓰는 단어장 이름 (banks.BUILTIN_BANK_NAME과 같아야 한다)
FIRST_BANK_NAME = "토익"
DEFAULT_SETTINGS = {
    "set_size": 50,
    "study_days_per_set": 3,
    "daily_review_limit": 30,
    # NGSL 빈도 순위가 이 안에 드는 기초 단어는 아예 건너뛴다 (0이면 안 건너뜀)
    "skip_basic_rank": 1500,
}
# 설정마다 허용하는 가장 작은 값 (기초 건너뛰기는 0 = 안 건너뜀이 말이 된다)
SMALLEST_VALUES = {"skip_basic_rank": 0}


# 학습 기록이 아직 없을 때 쓰는 기본값을 만든다
def default_progress() -> dict:
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "current_set": None,
        "words": {},
        "carry_over": [],
        "quiz_cache": {},
        "my_words": {},
        "reports": [],
    }


# 내가 직접 추가한 단어를 학습 기록에 넣는다 (뜻은 보관하고, 다음 세트에 먼저 나오도록 이월 목록에)
def add_my_word(progress: dict, word: str, meaning: str) -> dict:
    return migrate_words({word: {"meaning": meaning}}, progress)


# 설정값 하나를 바꾼다. 없는 이름이나 말이 안 되는 값(0 이하)은 그냥 무시한다
def change_setting(progress: dict, name: str, value: int) -> dict:
    if name not in DEFAULT_SETTINGS or value < SMALLEST_VALUES.get(name, 1):
        return progress
    return {**progress, "settings": {**progress["settings"], name: value}}


# 내 단어를 지운다. 목록·대기줄·학습 기록에서 빼되, 이미 이번 세트에 들어간 단어는 세트에 그대로 둔다
def remove_my_word(progress: dict, word: str) -> dict:
    current = progress["current_set"]
    in_this_set = word in current["words"] if current else False
    records = {w: r for w, r in progress["words"].items() if w != word or in_this_set}
    return {
        **progress,
        "my_words": {w: m for w, m in progress.get("my_words", {}).items() if w != word},
        "carry_over": [w for w in progress["carry_over"] if w != word],
        "words": records,
        "quiz_cache": {w: q for w, q in progress["quiz_cache"].items() if w != word or in_this_set},
    }


# 예전 words.json의 단어를 새 구조로 옮긴다. 내가 적어둔 뜻은 my_words에 보관하고,
# 다음 세트에 먼저 나오도록 이월 목록에 넣는다 (이미 학습 중인 단어는 그대로 둔다)
def migrate_words(old_words: dict, progress: dict) -> dict:
    records = {**progress["words"]}
    my_words = {**progress.get("my_words", {})}
    carry_over = list(progress["carry_over"])
    for word, info in old_words.items():
        if not word.strip():  # 예전 파일에 실수로 들어간 빈 단어는 건너뛴다
            continue
        my_words[word] = info.get("meaning", "")
        if word in records:
            continue
        records[word] = {"stage": 0, "next_review": None, "recent_results": [], "graduated": False}
        if word not in carry_over:
            carry_over.append(word)
    return {**progress, "words": records, "my_words": my_words, "carry_over": carry_over}


# 단어장별 기록을 모아 담은 통째 기록을 만든다 (파일에 저장되는 모양)
def default_book() -> dict:
    return {"current_bank": FIRST_BANK_NAME, "banks": {FIRST_BANK_NAME: default_progress()}}


# 지금 고른 단어장의 학습 기록을 꺼낸다
def current_bank_progress(book: dict) -> dict:
    return book["banks"][book["current_bank"]]


# 지금 고른 단어장의 학습 기록을 바꿔 끼운 통째 기록을 돌려준다
def put_bank_progress(book: dict, progress: dict) -> dict:
    return {**book, "banks": {**book["banks"], book["current_bank"]: progress}}


# 쓸 단어장을 바꾼다 (처음 고르는 단어장은 빈 기록으로 시작한다)
def switch_bank(book: dict, name: str) -> dict:
    banks = {**book["banks"]}
    banks.setdefault(name, default_progress())
    return {**book, "current_bank": name, "banks": banks}


# 파일에서 읽은 기록을 통째 기록 모양으로 맞춘다
# (단어장이 하나였던 시절의 평평한 파일은 첫 단어장 기록으로 옮긴다)
def fill_book(saved: dict) -> dict:
    if "banks" not in saved:
        return {"current_bank": FIRST_BANK_NAME, "banks": {FIRST_BANK_NAME: fill_missing_parts(saved)}}
    banks = {name: fill_missing_parts(record) for name, record in saved["banks"].items()}
    current = saved.get("current_bank") or next(iter(banks), FIRST_BANK_NAME)
    banks.setdefault(current, default_progress())
    return {"current_bank": current, "banks": banks}


# 저장된 기록에 빠진 항목이 있으면 기본값으로 채운다 (예전 파일에도 새 항목이 생기도록)
def fill_missing_parts(saved: dict) -> dict:
    progress = default_progress()
    progress.update(saved)
    progress["settings"] = {**DEFAULT_SETTINGS, **saved.get("settings", {})}
    return progress


# 학습 기록 파일을 읽는다. 파일이 없으면 기본값을 돌려준다 (단어장별 기록을 모두 담은 모양)
def load_book(path: str = DEFAULT_PROGRESS_PATH) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return default_book()
    return fill_book(json.loads(file_path.read_text(encoding="utf-8")))


# 지금 고른 단어장의 학습 기록만 읽는다
def load_progress(path: str = DEFAULT_PROGRESS_PATH) -> dict:
    return current_bank_progress(load_book(path))


# 통째 기록을 파일에 저장한다. 한국어가 깨지지 않게 ensure_ascii=False로 저장한다
def save_book(book: dict, path: str = DEFAULT_PROGRESS_PATH) -> None:
    Path(path).write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8")


# 지금 고른 단어장의 학습 기록을 저장한다 (다른 단어장 기록은 그대로 둔다)
def save_progress(progress: dict, path: str = DEFAULT_PROGRESS_PATH) -> None:
    save_book(put_bank_progress(load_book(path), progress), path)
