# 단어장을 여러 개 두고 고르는 함수들 (기본 단어장 + data/banks 폴더의 내 단어장들)
import csv
import json
import shutil
from pathlib import Path

from wordbank import load_word_bank

# 앱에 들어 있는 기본 단어장의 이름 (data/word_bank.json)
BUILTIN_BANK_NAME = "토익"
# 내가 넣은 단어장 파일들이 있는 폴더
DEFAULT_BANKS_DIR = Path(__file__).resolve().parent / "data" / "banks"
BANK_SUFFIXES = (".csv", ".json")
# 뜻 고르기 문제는 보기 4개가 필요하므로 단어장도 최소 4단어는 있어야 한다
MIN_BANK_WORDS = 4
# 이보다 적으면 보기가 늘 비슷해져서 한 번 알려준다
SMALL_BANK_WORDS = 10
HEADER_WORDS = ("word", "단어", "english")
# 파일 이름에 쓰면 안 되는 글자들 (이게 들어가면 엉뚱한 폴더에 파일이 생긴다)
BAD_NAME_MARKS = ("/", "\\", "..", ":", "*", "?", '"', "<", ">", "|")


# 단어장 폴더 경로를 정한다 (테스트에서는 임시 폴더를 넘긴다)
def banks_path(banks_dir: str | None = None) -> Path:
    return Path(banks_dir) if banks_dir else DEFAULT_BANKS_DIR


# CSV 한 줄을 단어장 항목으로 바꾼다 (apple,사과 또는 apple,사과,adjective)
def csv_row_to_entry(row: list[str]) -> dict | None:
    cells = [cell.strip() for cell in row]
    if len(cells) < 2 or not cells[0] or not cells[1]:
        return None
    pos = cells[2] if len(cells) > 2 and cells[2] else "other"
    return {"word": cells[0], "meaning_ko": cells[1], "pos": pos, "sources": [], "definition_en": ""}


# "apple,사과" 형식의 글을 단어장 항목 목록으로 바꾼다 (제목 줄·빈 줄·뜻 없는 줄은 건너뛴다)
def read_csv_bank(text: str) -> list[dict]:
    entries = []
    for row in csv.reader(text.lstrip("﻿").splitlines()):
        entry = csv_row_to_entry(row)
        if not entry:
            continue
        if not entries and entry["word"].lower() in HEADER_WORDS:
            continue
        entries.append(entry)
    return entries


# 단어장 파일 하나를 읽는다 (.csv는 두 칸 형식, .json은 만들어진 단어장 형식)
def read_bank_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    return json.loads(text) if path.suffix == ".json" else read_csv_bank(text)


# 쓸 수 있는 단어장 이름을 돌려준다 (기본 단어장이 맨 앞, 그다음 내가 넣은 것들)
def bank_names(banks_dir: str | None = None) -> list[str]:
    folder = banks_path(banks_dir)
    if not folder.exists():
        return [BUILTIN_BANK_NAME]
    mine = sorted(path.stem for path in folder.iterdir() if path.suffix in BANK_SUFFIXES)
    return [BUILTIN_BANK_NAME] + mine


# 단어장 이름으로 쓸 수 있는지 본다 (폴더를 건너뛰는 글자가 있으면 안 된다)
def check_bank_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("단어장 이름을 입력해주세요.")
    if any(letter < " " for letter in cleaned):
        raise ValueError("단어장 이름에 이상한 글자가 들어 있습니다.")
    if any(mark in cleaned for mark in BAD_NAME_MARKS):
        raise ValueError("단어장 이름에 / \ .. : * ? \" < > | 는 쓸 수 없습니다.")
    return cleaned


# 그 이름의 단어장이 이미 있는지 본다 (덮어쓰기 전에 물어보려고)
def bank_exists(name: str, banks_dir: str | None = None) -> bool:
    return find_bank_file(name, banks_dir) is not None


# 그 단어장 파일의 경로를 찾는다 (없으면 None)
def find_bank_file(name: str, banks_dir: str | None = None) -> Path | None:
    for suffix in BANK_SUFFIXES:
        path = banks_path(banks_dir) / f"{name}{suffix}"
        if path.exists():
            return path
    return None


# 단어장 이름으로 그 단어장의 단어들을 읽는다
def load_bank(name: str | None = None, banks_dir: str | None = None) -> list[dict]:
    if not name or name == BUILTIN_BANK_NAME:
        return load_word_bank()
    path = find_bank_file(name, banks_dir)
    if not path:
        raise FileNotFoundError(f"'{name}' 단어장 파일을 찾을 수 없습니다.")
    return read_bank_file(path)


# CSV 파일을 단어장으로 등록한다 (폴더로 복사하고 몇 단어인지 돌려준다)
def add_bank(source_path: str, name: str, banks_dir: str | None = None) -> int:
    name = check_bank_name(name)
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"'{source_path}' 파일이 없습니다.")
    entries = read_bank_file(source)
    if not entries:
        raise ValueError("단어를 하나도 읽지 못했습니다. 'apple,사과' 처럼 한 줄에 단어와 뜻을 적어주세요.")
    if len(entries) < MIN_BANK_WORDS:
        raise ValueError(
            f"단어가 {len(entries)}개뿐입니다. 뜻 고르기 문제를 내려면 최소 {MIN_BANK_WORDS}단어가 필요합니다."
        )
    folder = banks_path(banks_dir)
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, folder / f"{name}{source.suffix or '.csv'}")
    return len(entries)


# 단어장을 지운다 (기본 단어장은 지울 수 없다)
def delete_bank(name: str, banks_dir: str | None = None) -> None:
    name = check_bank_name(name)
    if name == BUILTIN_BANK_NAME:
        raise ValueError(f"기본 단어장('{BUILTIN_BANK_NAME}')은 지울 수 없습니다.")
    path = find_bank_file(name, banks_dir)
    if not path:
        raise FileNotFoundError(f"'{name}' 단어장이 없습니다.")
    path.unlink()
