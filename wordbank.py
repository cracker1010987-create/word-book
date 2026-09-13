# 원본 단어에 순위를 붙이고, NGSL과 TSL을 하나의 단어장으로 합치는 함수들
import unicodedata

SOURCES = ("NGSL", "TSL")


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
