# load_words 함수가 파일이 있을 때/없을 때 모두 잘 동작하는지 확인하는 테스트
import json
from pathlib import Path

from storage import add_word, load_words, save_words


def test_load_words_returns_empty_dict_when_file_missing(tmp_path: Path) -> None:
    # 파일이 없으면 빈 딕셔너리를 돌려준다
    missing_path = tmp_path / "words.json"
    assert load_words(str(missing_path)) == {}


def test_load_words_returns_saved_content(tmp_path: Path) -> None:
    # 파일이 있으면 그 내용을 그대로 돌려준다
    path = tmp_path / "words.json"
    data = {"apple": {"meaning": "사과", "wrong_count": 0}}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert load_words(str(path)) == data


def test_save_words_then_load_words_returns_same_content(tmp_path: Path) -> None:
    # 저장한 뒤 다시 읽으면 같은 내용이 나온다
    path = tmp_path / "words.json"
    data = {"apple": {"meaning": "사과", "wrong_count": 1}}
    save_words(data, str(path))
    assert load_words(str(path)) == data


def test_save_words_preserves_korean_text(tmp_path: Path) -> None:
    # 한국어 뜻이 깨지지 않고 그대로 저장된다
    path = tmp_path / "words.json"
    data = {"generous": {"meaning": "관대한", "wrong_count": 0}}
    save_words(data, str(path))
    saved_text = path.read_text(encoding="utf-8")
    assert "관대한" in saved_text


def test_add_word_to_empty_file(tmp_path: Path) -> None:
    # 파일이 없을 때 단어를 추가하면 wrong_count 0으로 새로 생긴다
    path = tmp_path / "words.json"
    add_word("apple", "사과", str(path))
    assert load_words(str(path)) == {"apple": {"meaning": "사과", "wrong_count": 0}}


def test_add_word_keeps_existing_words(tmp_path: Path) -> None:
    # 이미 있던 단어는 지워지지 않고 새 단어가 추가된다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 2}}, str(path))
    add_word("banana", "바나나", str(path))
    words = load_words(str(path))
    assert words["apple"] == {"meaning": "사과", "wrong_count": 2}
    assert words["banana"] == {"meaning": "바나나", "wrong_count": 0}


def test_add_word_returns_true_for_brand_new_word(tmp_path: Path) -> None:
    # 새 단어를 추가하면 True를 돌려준다
    path = tmp_path / "words.json"
    assert add_word("apple", "사과", str(path)) is True


def test_add_word_for_existing_word_preserves_progress(tmp_path: Path) -> None:
    # 이미 있는 단어를 다시 추가하면 wrong_count/last_wrong_date는 그대로 두고 뜻만 바뀐다
    path = tmp_path / "words.json"
    save_words(
        {"apple": {"meaning": "사과", "wrong_count": 3, "last_wrong_date": "2026-01-01"}}, str(path)
    )
    is_new = add_word("apple", "사과(고친 뜻)", str(path))
    words = load_words(str(path))
    assert is_new is False
    assert words["apple"] == {
        "meaning": "사과(고친 뜻)",
        "wrong_count": 3,
        "last_wrong_date": "2026-01-01",
    }
