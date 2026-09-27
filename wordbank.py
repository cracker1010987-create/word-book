# 원본 단어에 순위를 붙이고, NGSL과 TSL을 하나의 단어장으로 합치고, 완성된 단어장을 불러오는 함수들
import json
import unicodedata
from pathlib import Path

SOURCES = ("NGSL", "TSL")
# 어느 폴더에서 실행하든 이 파일 옆의 data/word_bank.json을 찾도록 이 파일 위치를 기준으로 잡는다
DEFAULT_BANK_PATH = Path(__file__).resolve().parent / "data" / "word_bank.json"
# AI가 만든 뜻 중 아쉬운 것을 손으로 고쳐두는 파일 (단어장을 다시 만들어도 이 고침은 남는다)
DEFAULT_FIXES_PATH = Path(__file__).resolve().parent / "data" / "meaning_fixes.json"
FIXABLE_FIELDS = ("meaning_ko", "pos")


# 외울 순서를 만든다: 토익(TSL) 단어를 먼저, 그다음 기초를 뺀 NGSL 단어
# (섞어두면 1일차에 the/say 같은 기초 단어가 절반이라 토익·수능 준비에는 헛돈다)
def study_order(bank: list[dict], skip_basic_rank: int) -> list[dict]:
    toeic = [entry for entry in bank if "TSL" in entry.get("sources", [])]
    rest = [
        entry
        for entry in bank
        if "TSL" not in entry.get("sources", [])
        # 순위를 모르는 단어(내 단어 등)는 건너뛸지 판단할 수 없으니 남긴다
        and (entry.get("ngsl_rank") is None or entry["ngsl_rank"] > skip_basic_rank)
    ]
    return toeic + rest


# 손으로 고쳐둔 뜻 목록을 읽는다. 파일이 없으면 고칠 게 없다는 뜻이다
def load_meaning_fixes(path: str | None = None) -> dict:
    fixes_path = Path(path) if path else DEFAULT_FIXES_PATH
    if not fixes_path.exists():
        return {}
    return json.loads(fixes_path.read_text(encoding="utf-8"))


# 단어장 뜻 중에 손으로 고쳐둔 것이 있으면 바꿔 끼운다 (단어장에 없는 단어는 무시한다)
def apply_meaning_fixes(entries: list[dict], fixes: dict) -> list[dict]:
    fixed = []
    for entry in entries:
        fix = fixes.get(entry["word"], {})
        changes = {field: fix[field] for field in FIXABLE_FIELDS if field in fix}
        fixed.append({**entry, **changes})
    return fixed


# 완성된 단어장 파일을 읽어 순서 그대로 돌려준다. 파일이 없으면 만드는 방법을 알려준다
def load_word_bank(path: str | None = None, fixes_path: str | None = None) -> list[dict]:
    bank_path = Path(path) if path else DEFAULT_BANK_PATH
    if not bank_path.exists():
        raise FileNotFoundError(
            f"단어장 파일({bank_path})이 없습니다. "
            "먼저 '.venv\\Scripts\\python.exe scripts\\build_word_bank.py'로 만들어주세요."
        )
    entries = json.loads(bank_path.read_text(encoding="utf-8"))
    return apply_meaning_fixes(entries, load_meaning_fixes(fixes_path))


# 악센트를 뗀 철자로 바꾼다 (café → cafe)
def strip_accents(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


# 같은 단어인지 비교하기 위한 키를 만든다 (대소문자·앞뒤 공백·악센트·하이픈 차이 무시)
def normalize_word(word: str) -> str:
    return strip_accents(word.strip().lower()).replace("-", "")


# 뜻이 있는 단어 목록에 순위를 붙이고, 순위 목록에만 있는 단어는 뜻 없이 뒤에 추가한다
def attach_ranks(words: list[dict], ranked: list[dict]) -> list[dict]:
    rank_by_key = {normalize_word(item["word"]): item["rank"] for item in ranked}
    result = [{**item, "rank": rank_by_key.get(normalize_word(item["word"]))} for item in words]
    known = {normalize_word(item["word"]) for item in words}
    for item in ranked:
        if normalize_word(item["word"]) not in known:
            result.append({"word": strip_accents(item["word"]), "definition": "", "rank": item["rank"]})
    return result


# 목록 안에서의 상대 순위(순위 / 단어 수)를 구한다. 순위가 없으면 그 목록의 맨 뒤로 보낸다
def relative_position(rank: int | None, total: int) -> float:
    if rank is None:
        return (total + 1) / total
    return rank / total


# 합친 단어장의 한 칸을 새로 만든다 (출처와 순위는 add_source로 채운다)
def new_entry(item: dict) -> dict:
    return {
        "word": item["word"],
        "definition": item["definition"],
        "sources": [],
        "ngsl_rank": None,
        "tsl_rank": None,
        "position": float("inf"),
    }


# 합친 단어장의 한 칸에 출처·순위를 기록하고, 더 앞선 상대 순위와 비어있지 않은 뜻을 남긴다
def add_source(entry: dict, source: str, item: dict, total: int) -> None:
    entry["sources"].append(source)
    entry[f"{source.lower()}_rank"] = item["rank"]
    entry["position"] = min(entry["position"], relative_position(item["rank"], total))
    if not entry["definition"]:
        entry["definition"] = item["definition"]


# NGSL과 TSL을 합친다: 같은 단어는 하나로, 상대 순위로 섞어 정렬 (같으면 NGSL 먼저)
def merge_word_lists(ngsl: list[dict], tsl: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for source, words in zip(SOURCES, (ngsl, tsl)):
        for item in words:
            entry = merged.setdefault(normalize_word(item["word"]), new_entry(item))
            add_source(entry, source, item, len(words))
    ordered = sorted(merged.values(), key=lambda e: (e["position"], e["sources"][0] != "NGSL"))
    return [{key: value for key, value in e.items() if key != "position"} for e in ordered]


# 합친 단어 목록과 AI가 만든 한국어 뜻을 묶어 최종 단어장 항목을 만든다 (뜻을 못 받은 단어는 뺀다)
def make_bank_entries(merged: list[dict], meanings: dict[str, dict]) -> list[dict]:
    entries = []
    for item in merged:
        meaning = meanings.get(item["word"])
        if not meaning:
            continue
        entries.append(
            {
                "word": item["word"],
                "meaning_ko": meaning["meaning_ko"],
                "pos": meaning["pos"],
                "definition_en": item["definition"],
                "sources": item["sources"],
                "ngsl_rank": item["ngsl_rank"],
                "tsl_rank": item["tsl_rank"],
            }
        )
    return entries
