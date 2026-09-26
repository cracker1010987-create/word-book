# 학습 기록 파일(progress.json)을 읽고 쓰는 함수들을 확인하는 테스트
import json
from pathlib import Path

from progress import add_my_word, default_progress, load_progress, migrate_words, save_progress


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


def test_migrate_words_adds_my_words_to_the_carry_over_queue() -> None:
    # 예전 words.json의 단어를 새 구조로 옮긴다: 다음 세트에 먼저 들어가도록 이월 목록에 넣는다
    old_words = {
        "elaborate": {"meaning": "정교한", "wrong_count": 2, "last_wrong_date": "2026-09-13"},
        "brisk": {"meaning": "활기찬", "wrong_count": 0},
    }
    progress = migrate_words(old_words, default_progress())
    assert sorted(progress["carry_over"]) == ["brisk", "elaborate"]
    assert progress["words"]["elaborate"]["stage"] == 0
    assert progress["words"]["elaborate"]["graduated"] is False


def test_migrate_words_keeps_my_own_meanings() -> None:
    # 내가 적어둔 뜻은 단어장에 없을 수 있으므로 학습 기록에 함께 보관한다
    progress = migrate_words({"brisk": {"meaning": "활기찬, 빠른", "wrong_count": 0}}, default_progress())
    assert progress["my_words"]["brisk"] == "활기찬, 빠른"


def test_migrate_words_does_not_touch_words_already_being_learned() -> None:
    # 이미 학습 기록에 있는 단어는 건드리지 않는다 (두 번 옮겨도 안전)
    before = default_progress()
    before["words"]["brisk"] = {"stage": 3, "next_review": "2026-10-01", "recent_results": [], "graduated": False}
    progress = migrate_words({"brisk": {"meaning": "활기찬", "wrong_count": 1}}, before)
    assert progress["words"]["brisk"]["stage"] == 3
    assert progress["carry_over"] == []


def test_migrate_words_with_nothing_to_move_changes_nothing() -> None:
    # 옮길 단어가 없으면 그대로 둔다
    before = default_progress()
    assert migrate_words({}, before) == before


def test_add_my_word_puts_it_at_the_front_of_the_next_set() -> None:
    # 내 단어를 추가하면 뜻을 보관하고, 다음 세트에 먼저 나오도록 이월 목록에 넣는다
    progress = add_my_word(default_progress(), "brisk", "활기찬, 빠른")
    assert progress["my_words"]["brisk"] == "활기찬, 빠른"
    assert progress["carry_over"] == ["brisk"]
    assert progress["words"]["brisk"]["stage"] == 0


def test_add_my_word_twice_only_updates_the_meaning() -> None:
    # 같은 단어를 다시 추가하면 뜻만 고치고 학습 기록은 건드리지 않는다
    progress = add_my_word(default_progress(), "brisk", "활기찬")
    progress["words"]["brisk"]["stage"] = 2
    progress = add_my_word(progress, "brisk", "활기찬, 빠른")
    assert progress["my_words"]["brisk"] == "활기찬, 빠른"
    assert progress["words"]["brisk"]["stage"] == 2
    assert progress["carry_over"] == ["brisk"]
