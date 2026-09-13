# NGSL/TSL 원본 엑셀(단어+뜻)과 통계 CSV(단어+순위)를 잘 읽는지 확인하는 테스트
from pathlib import Path

from openpyxl import Workbook

from scripts.build_word_bank import read_source_ranks, read_source_words


def make_xlsx(path: Path, rows: list[tuple]) -> str:
    # 테스트용 작은 엑셀 파일을 만들어 경로를 돌려준다 (첫 줄은 원본처럼 제목 줄)
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    return str(path)


def test_reads_word_and_definition_skipping_header(tmp_path: Path) -> None:
    # 제목 줄은 건너뛰고, A열 단어와 B열 영어 뜻을 순서대로 읽는다
    path = make_xlsx(
        tmp_path / "ngsl.xlsx",
        [("Word", "Definitons"), ("abuse", "to treat someone badly"), ("accident", "sudden unplanned event")],
    )
    assert read_source_words(path) == [
        {"word": "abuse", "definition": "to treat someone badly"},
        {"word": "accident", "definition": "sudden unplanned event"},
    ]


def test_strips_spaces_and_ignores_extra_empty_columns(tmp_path: Path) -> None:
    # TSL 원본처럼 뜻 끝에 공백이 있거나 빈 열이 더 붙어 있어도 깔끔하게 읽는다
    path = make_xlsx(
        tmp_path / "tsl.xlsx",
        [("TSL Word", "TSL Definition", None, None), ("actress", "a female actor ", None, None)],
    )
    assert read_source_words(path) == [{"word": "actress", "definition": "a female actor"}]


def test_keeps_multi_word_entries(tmp_path: Path) -> None:
    # 'ice cream'처럼 띄어쓰기가 들어간 단어도 하나의 단어로 읽는다
    path = make_xlsx(tmp_path / "tsl.xlsx", [("TSL Word", "TSL Definition"), ("ice cream", "a frozen dessert")])
    assert read_source_words(path)[0]["word"] == "ice cream"


def test_skips_rows_without_word(tmp_path: Path) -> None:
    # 단어 칸이 비어 있는 줄은 건너뛴다
    path = make_xlsx(
        tmp_path / "ngsl.xlsx",
        [("Word", "Definitons"), (None, None), ("   ", "blank word"), ("add", "to put together")],
    )
    assert read_source_words(path) == [{"word": "add", "definition": "to put together"}]


def test_read_source_ranks_reads_word_and_rank(tmp_path: Path) -> None:
    # 통계 CSV에서 제목 줄을 빼고 1열 단어와 2열 순위를 읽는다
    path = tmp_path / "ngsl.csv"
    path.write_text("Lemma,SFI Rank,SFI,U\nthe,1,87.85,60910\nbe,2,86.86,48575\n", encoding="utf-8")
    assert read_source_ranks(str(path)) == [{"word": "the", "rank": 1}, {"word": "be", "rank": 2}]


def test_read_source_ranks_reads_latin1_accents(tmp_path: Path) -> None:
    # TSL 통계 CSV처럼 latin-1로 저장된 résumé 같은 단어도 글자가 깨지지 않게 읽는다
    path = tmp_path / "tsl.csv"
    path.write_bytes("Word,TSL Rank,SFI,U\nrésumé,20,50.1,9.9\n".encode("latin-1"))
    assert read_source_ranks(str(path)) == [{"word": "résumé", "rank": 20}]


def test_read_source_ranks_keeps_rows_with_missing_frequency(tmp_path: Path) -> None:
    # SFI 칸이 #N/A여도 순위만 있으면 읽는다 (순위만 쓰기 때문)
    path = tmp_path / "tsl.csv"
    path.write_text("Word,TSL Rank,SFI,U\nbirthday,104,#N/A,#N/A\n", encoding="utf-8")
    assert read_source_ranks(str(path)) == [{"word": "birthday", "rank": 104}]
