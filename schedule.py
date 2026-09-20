# 복습 단계를 올리고 내리며 다음 복습일을 계산하는 함수들
from datetime import date, timedelta

# 복습 단계별로 며칠 뒤에 다시 물어볼지 (prd.md 결정 6)
REVIEW_INTERVALS = {1: 3, 2: 7, 3: 14, 4: 30, 5: 60}
LAST_STAGE = 5
RECENT_RESULTS_KEPT = 2


# 오늘 날짜를 기준으로 그 단계의 다음 복습일을 구한다 (복습 단계 1~5만 가능)
def next_review_date(stage: int, today: str) -> str:
    if stage not in REVIEW_INTERVALS:
        raise ValueError(f"복습 단계는 {sorted(REVIEW_INTERVALS)} 중 하나여야 합니다. 받은 값: {stage}")
    return (date.fromisoformat(today) + timedelta(days=REVIEW_INTERVALS[stage])).isoformat()


# 최근 정답 여부를 기록하되 마지막 몇 개만 남긴다 (세트 통과 판정에 쓰임)
def add_recent_result(results: list[bool], is_correct: bool) -> list[bool]:
    return [*results, is_correct][-RECENT_RESULTS_KEPT:]


# 복습 결과를 반영한 새 기록을 돌려준다. 맞히면 단계를 올리고(5단계 통과 시 졸업),
# 틀리면 0단계로 내려 다음 세트에서 다시 외우게 한다
def update_after_review(entry: dict, is_correct: bool, today: str) -> dict:
    updated = {**entry, "recent_results": add_recent_result(entry["recent_results"], is_correct)}
    if not is_correct:
        return {**updated, "stage": 0, "next_review": None, "graduated": False}
    stage = entry["stage"] + 1
    if stage > LAST_STAGE:
        return {**updated, "stage": stage, "next_review": None, "graduated": True}
    return {**updated, "stage": stage, "next_review": next_review_date(stage, today), "graduated": False}


# 오늘 복습할 차례가 된 단어인지 본다 (졸업했거나 세트에서 외우는 중인 단어는 제외)
def is_due(entry: dict, today: str) -> bool:
    if entry.get("graduated") or not entry.get("next_review"):
        return False
    return entry["next_review"] <= today


# 오늘 복습할 단어를 오래 밀린 순서(같으면 단어 순서)로 상한까지 고른다
def due_review_words(progress: dict, today: str, limit: int | None = None) -> list[str]:
    if limit is None:
        limit = progress["settings"]["daily_review_limit"]
    due = [word for word, entry in progress["words"].items() if is_due(entry, today)]
    due.sort(key=lambda word: (progress["words"][word]["next_review"], word))
    return due[:limit]
