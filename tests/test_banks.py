# 단어장 여러 개를 파일로 관리하는 함수들을 확인하는 테스트
from pathlib import Path

import pytest

from banks import (
    BUILTIN_BANK_NAME,
    bank_exists,
    add_bank,
    bank_names,
    delete_bank,
    load_bank,
    read_csv_bank,
)

CSV = """word,meaning
apple,사과
brave,용감한,adjective
"""


def test_csv_with_word_and_meaning_becomes_bank_entries() -> None:
    # apple,사과 형식을 단어장 항목으로 바꾼다 (품사는 안 적으면 other)
    entries = read_csv_bank(CSV)
    assert entries[0] == {"word": "apple", "meaning_ko": "사과", "pos": "other", "sources": [], "definition_en": ""}


def test_csv_third_column_is_used_as_part_of_speech() -> None:
    # 세 번째 칸에 품사를 적으면 그대로 쓴다
    assert read_csv_bank(CSV)[1]["pos"] == "adjective"


def test_csv_header_row_is_skipped() -> None:
    # 첫 줄이 word,meaning 같은 제목 줄이면 단어로 세지 않는다
    assert [entry["word"] for entry in read_csv_bank(CSV)] == ["apple", "brave"]


def test_csv_ignores_blank_lines_and_rows_without_a_meaning() -> None:
    # 빈 줄이나 뜻이 없는 줄은 건너뛴다
    entries = read_csv_bank("apple,사과\n\nbrave\n  \ncandid,솔직한\n")
    assert [entry["word"] for entry in entries] == ["apple", "candid"]


def test_csv_written_by_excel_with_a_bom_still_reads() -> None:
    # 엑셀로 저장한 CSV(맨 앞에 BOM이 붙는다)도 읽는다
    assert read_csv_bank("\ufeffapple,사과\n")[0]["word"] == "apple"


def test_bank_names_starts_with_the_builtin_bank(tmp_path: Path) -> None:
    # 기본 단어장(토익)이 항상 목록 맨 앞에 있다
    assert bank_names(banks_dir=str(tmp_path)) == [BUILTIN_BANK_NAME]


def test_bank_names_includes_files_in_the_banks_folder(tmp_path: Path) -> None:
    # data/banks 폴더에 넣은 파일이 단어장 목록에 나온다 (파일 이름이 단어장 이름)
    (tmp_path / "내신1과.csv").write_text("apple,사과\n", encoding="utf-8")
    assert bank_names(banks_dir=str(tmp_path)) == [BUILTIN_BANK_NAME, "내신1과"]


def test_load_bank_reads_the_words_of_that_bank(tmp_path: Path) -> None:
    # 단어장 이름으로 그 단어장의 단어를 읽는다
    (tmp_path / "내신1과.csv").write_text("apple,사과\n", encoding="utf-8")
    entries = load_bank("내신1과", banks_dir=str(tmp_path))
    assert entries[0]["word"] == "apple"


def test_load_bank_without_a_name_reads_the_builtin_bank(tmp_path: Path) -> None:
    # 이름을 안 주거나 기본 단어장을 고르면 원래 4,059단어 단어장을 읽는다
    assert len(load_bank(BUILTIN_BANK_NAME, banks_dir=str(tmp_path))) > 4000


def test_add_bank_copies_the_file_and_tells_how_many_words(tmp_path: Path) -> None:
    # CSV 파일을 주면 단어장 폴더로 복사하고 몇 단어인지 알려준다
    source = tmp_path / "원본.csv"
    source.write_text(CSV, encoding="utf-8")
    banks_dir = tmp_path / "banks"
    count = add_bank(str(source), "내신2과", banks_dir=str(banks_dir))
    assert count == 2
    assert "내신2과" in bank_names(banks_dir=str(banks_dir))


def test_add_bank_refuses_a_file_with_no_words(tmp_path: Path) -> None:
    # 단어가 하나도 없는 파일은 단어장으로 만들지 않는다
    empty = tmp_path / "빈파일.csv"
    empty.write_text("word,meaning\n", encoding="utf-8")
    with pytest.raises(ValueError):
        add_bank(str(empty), "빈단어장", banks_dir=str(tmp_path / "banks"))


def test_add_bank_refuses_a_missing_file(tmp_path: Path) -> None:
    # 없는 파일 경로를 주면 알려준다
    with pytest.raises(FileNotFoundError):
        add_bank(str(tmp_path / "없는파일.csv"), "내신", banks_dir=str(tmp_path / "banks"))


def test_delete_bank_removes_the_file(tmp_path: Path) -> None:
    # 단어장을 지우면 파일이 없어진다
    (tmp_path / "내신1과.csv").write_text("apple,사과\n", encoding="utf-8")
    delete_bank("내신1과", banks_dir=str(tmp_path))
    assert bank_names(banks_dir=str(tmp_path)) == [BUILTIN_BANK_NAME]


def test_delete_bank_refuses_to_remove_the_builtin_bank(tmp_path: Path) -> None:
    # 기본 단어장은 지울 수 없다 (앱이 쓸 단어가 없어진다)
    with pytest.raises(ValueError):
        delete_bank(BUILTIN_BANK_NAME, banks_dir=str(tmp_path))


def test_bank_name_with_a_folder_mark_is_refused(tmp_path: Path) -> None:
    # 이름에 ../ 나 / 가 들어가면 엉뚱한 폴더에 파일이 생기므로 막는다
    source = tmp_path / "원본.csv"
    source.write_text("apple,사과\n", encoding="utf-8")
    for bad_name in ["../바깥", "내신/1과", "내신" + chr(92) + "1과", "내신" + chr(1)]:
        with pytest.raises(ValueError):
            add_bank(str(source), bad_name, banks_dir=str(tmp_path / "banks"))
    assert not (tmp_path / "바깥.csv").exists()


def test_empty_bank_name_is_refused(tmp_path: Path) -> None:
    # 이름 없이 단어장을 만들 수 없다
    source = tmp_path / "원본.csv"
    source.write_text("apple,사과\n", encoding="utf-8")
    with pytest.raises(ValueError):
        add_bank(str(source), "   ", banks_dir=str(tmp_path / "banks"))


def test_bank_exists_tells_whether_that_name_is_taken(tmp_path: Path) -> None:
    # 같은 이름이 이미 있는지 미리 알 수 있다 (덮어쓰기 전에 물어보려고)
    source = tmp_path / "원본.csv"
    source.write_text("apple,사과\n", encoding="utf-8")
    banks_dir = str(tmp_path / "banks")
    assert bank_exists("내신", banks_dir=banks_dir) is False
    add_bank(str(source), "내신", banks_dir=banks_dir)
    assert bank_exists("내신", banks_dir=banks_dir) is True
