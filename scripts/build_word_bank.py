# NGSL/TSL 원본 엑셀을 읽어 앱에서 쓸 단어장(data/word_bank.json)을 만드는 스크립트
# 실행: .venv\Scripts\python.exe scripts\build_word_bank.py
import csv
import json
import sys
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # 스크립트로 직접 실행할 때도 ai.py, wordbank.py를 찾을 수 있게 한다

from ai import generate_all_meanings  # noqa: E402
from wordbank import attach_ranks, make_bank_entries, merge_word_lists  # noqa: E402

SOURCE_DIR = ROOT / "data" / "source"
BANK_PATH = ROOT / "data" / "word_bank.json"
CACHE_PATH = ROOT / "data" / "meanings_cache.json"
SLICE_SIZE = 200


# 원본 엑셀의 첫 시트에서 제목 줄을 빼고, A열 단어와 B열 영어 뜻을 순서대로 읽어온다
def read_source_words(xlsx_path: str) -> list[dict]:
    sheet = load_workbook(xlsx_path, read_only=True).active
    words = []
    for row in list(sheet.iter_rows(values_only=True))[1:]:
        word = str(row[0] or "").strip()
        if not word:
            continue
        definition = str(row[1] or "").strip() if len(row) > 1 else ""
        words.append({"word": word, "definition": definition})
    return words


# 통계 CSV 파일의 모든 줄을 읽는다. utf-8로 안 읽히면(TSL 파일) latin-1로 다시 읽는다
def read_csv_rows(csv_path: str) -> list[list[str]]:
    try:
        with open(csv_path, encoding="utf-8", newline="") as f:
            return list(csv.reader(f))
    except UnicodeDecodeError:
        with open(csv_path, encoding="latin-1", newline="") as f:
            return list(csv.reader(f))


# 통계 CSV에서 제목 줄을 빼고 1열 단어와 2열 순위를 읽는다 (빈도 지수 열은 #N/A가 있어서 안 쓴다)
def read_source_ranks(csv_path: str) -> list[dict]:
    ranks = []
    for row in read_csv_rows(csv_path)[1:]:
        if len(row) < 2 or not row[0].strip() or not row[1].strip().isdigit():
            continue
        ranks.append({"word": row[0].strip(), "rank": int(row[1])})
    return ranks


# NGSL·TSL 원본 4개 파일을 읽어 순위를 붙이고 하나로 합친 단어 목록을 만든다
def load_merged_words() -> list[dict]:
    ngsl_words = read_source_words(str(SOURCE_DIR / "NGSL_12_with_English_definitions.xlsx"))
    tsl_words = read_source_words(str(SOURCE_DIR / "TSL_12_definitions.xlsx"))
    ngsl = attach_ranks(ngsl_words, read_source_ranks(str(SOURCE_DIR / "NGSL_12_stats.csv")))
    tsl = attach_ranks(tsl_words, read_source_ranks(str(SOURCE_DIR / "TSL_12_stats.csv")))
    return merge_word_lists(ngsl, tsl)


# JSON 파일을 읽는다. 파일이 없으면 기본값을 돌려준다
def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


# 데이터를 한국어가 깨지지 않게 JSON 파일로 저장한다
def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# 캐시에 없는 단어만 200개씩 뜻을 받고, 한 묶음이 끝날 때마다 캐시에 저장한다 (중간에 멈춰도 이어서 하게)
def fill_meaning_cache(words: list[dict]) -> dict[str, dict]:
    cache = read_json(CACHE_PATH, {})
    todo = [item for item in words if item["word"] not in cache]
    for start in range(0, len(todo), SLICE_SIZE):
        try:
            cache.update(generate_all_meanings(todo[start : start + SLICE_SIZE]))
        except Exception as error:  # API 오류가 나도 지금까지 받은 뜻은 저장하고 다음 묶음으로 넘어간다
            print(f"  오류로 이 묶음은 건너뜀 (다시 실행하면 이어서 받음): {error}")
        write_json(CACHE_PATH, cache)
        print(f"  진행: {min(start + SLICE_SIZE, len(todo))}/{len(todo)}", flush=True)
    return cache


# 원본을 합치고, 한국어 뜻을 받아, 최종 단어장 파일을 저장한다
def main() -> None:
    words = load_merged_words()
    meanings = fill_meaning_cache(words)
    entries = make_bank_entries(words, meanings)
    write_json(BANK_PATH, entries)
    missing = [item["word"] for item in words if item["word"] not in meanings]
    print(f"단어장 저장: {len(entries)}/{len(words)}개, 뜻 못 받은 단어 {len(missing)}개 {missing[:20]}")


if __name__ == "__main__":
    main()
