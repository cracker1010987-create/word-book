# AI 없이 단어장만으로 '영어 보고 뜻 고르기' 4지선다 문제를 만드는 함수들
import random

OPTION_COUNT = 4


# 단어장에서 그 단어의 항목을 찾는다
def find_entry(word: str, bank: list[dict]) -> dict:
    for entry in bank:
        if entry["word"] == word:
            return entry
    raise ValueError(f"단어장에 없는 단어입니다: {word}")


# 오답으로 쓸 다른 단어의 뜻을 모은다 (품사가 같은 것만 / 다른 것만 골라서)
def other_meanings(entry: dict, bank: list[dict], same_pos: bool) -> list[str]:
    meanings = []
    for other in bank:
        if other["word"] == entry["word"] or other["meaning_ko"] == entry["meaning_ko"]:
            continue
        if (other["pos"] == entry["pos"]) == same_pos:
            meanings.append(other["meaning_ko"])
    return meanings


# 오답 보기를 고른다. 같은 품사에서 먼저 고르고, 모자라면 다른 품사에서 채운다
def pick_wrong_meanings(entry: dict, bank: list[dict], rng: random.Random, count: int) -> list[str]:
    same_pos = other_meanings(entry, bank, same_pos=True)
    other_pos = other_meanings(entry, bank, same_pos=False)
    rng.shuffle(same_pos)
    rng.shuffle(other_pos)
    picked: list[str] = []
    for meaning in [*same_pos, *other_pos]:
        if len(picked) >= count:
            break
        if meaning not in picked:
            picked.append(meaning)
    return picked


# 영어 단어를 보고 한국어 뜻을 고르는 4지선다 문제를 만든다
def make_meaning_choice_quiz(word: str, bank: list[dict], rng: random.Random) -> dict:
    entry = find_entry(word, bank)
    options = [entry["meaning_ko"], *pick_wrong_meanings(entry, bank, rng, OPTION_COUNT - 1)]
    rng.shuffle(options)
    return {"word": word, "options": options, "answer": entry["meaning_ko"]}
