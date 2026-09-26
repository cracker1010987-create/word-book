from datetime import date, timedelta


# 단어장 전체 대비 지금까지의 진도와, 지금 속도로 갔을 때의 예상 완주일을 계산한다
def calculate_progress(progress: dict, bank: list[dict], today: str) -> dict:
    records = progress["words"]
    graduated = sum(1 for record in records.values() if record["graduated"])
    reviewing = sum(1 for record in records.values() if not record["graduated"] and record["stage"] >= 1)
    in_set = sum(1 for record in records.values() if not record["graduated"] and record["stage"] == 0)
    total = len(bank)
    started = graduated + reviewing + in_set
    days = progress.get("total_study_days", 0)
    return {
        "total": total,
        "graduated": graduated,
        "reviewing": reviewing,
        "in_set": in_set,
        "not_started": total - started,
        "percent": round(graduated / total * 100, 1) if total else 0.0,
        **estimate_finish(total - started, started / days if days else 0, today),
    }


# 남은 단어 수와 하루 속도로 완주까지 며칠 걸릴지, 그날이 언제인지 어림잡는다
def estimate_finish(remaining: int, pace: float, today: str) -> dict:
    if pace <= 0:
        return {"days_left": None, "finish_date": None}
    days_left = -(-remaining // pace)  # 올림 나눗셈
    days_left = int(days_left)
    return {"days_left": days_left, "finish_date": (date.fromisoformat(today) + timedelta(days=days_left)).isoformat()}


# 단어 데이터로 총 단어 수·총 틀린 횟수·완전히 외운 단어 수를 계산하는 함수
def calculate_stats(words: dict) -> dict:
    wrong_counts = [word["wrong_count"] for word in words.values()]
    return {
        "total_words": len(words),
        "total_wrong_count": sum(wrong_counts),
        "mastered_words": sum(1 for count in wrong_counts if count == 0),
    }
