# 학습 기록 파일(progress.json)을 읽고 쓰는 함수들을 확인하는 테스트
import json
from pathlib import Path

from progress import default_progress, load_progress, save_progress


def test_default_progress_has_settings_and_empty_records() -> None:
    # 처음 시작할 때의 기본값: 세트 50단어, 공부한 날 3일, 하루 복습 30개, 기록은 비어 있음
    progress = default_progress()
    assert progress["settings"] == {"set_size": 50, "study_days_per_set": 3, "daily_review_limit": 30}
    assert progress["current_set"] is None
    assert progress["words"] == {}
    assert progress["carry_over"] == []
    assert progress["quiz_cache"] == {}


def test_load_progress_returns_default_when_file_missing(tmp_path: Path) -> None:
    # 파일이 아직 없으면(처음 실행) 기본값을 돌려준다
    assert load_progress(str(tmp_path / "progress.json")) == default_progress()


def test_save_then_load_returns_same_record(tmp_path: Path) -> None:
    # 저장한 뒤 다시 읽으면 같은 내용이 나온다
    path = tmp_path / "progress.json"
    progress = default_progress()
    progress["words"]["client"] = {"stage": 1, "next_review": "2026-09-23", "recent_results": [True]}
    progress["carry_over"] = ["elaborate"]
    save_progress(progress, str(path))
    assert load_progress(str(path)) == progress


def test_load_progress_fills_in_missing_parts(tmp_path: Path) -> None:
    # 예전에 저장한 파일에 없는 항목이 생겨도, 기본값으로 채워서 읽는다 (설정은 저장된 값 유지)
    path = tmp_path / "progress.json"
    path.write_text(json.dumps({"settings": {"set_size": 20}, "words": {}}), encoding="utf-8")
    progress = load_progress(str(path))
    assert progress["settings"]["set_size"] == 20
    assert progress["settings"]["daily_review_limit"] == 30
    assert progress["current_set"] is None
    assert progress["quiz_cache"] == {}
