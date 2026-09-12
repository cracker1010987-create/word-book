# 단어 데이터를 JSON 파일 하나에 읽고 쓰는 함수들
import json


# 파일에서 단어 데이터를 읽어온다. 파일이 없으면 빈 딕셔너리를 돌려준다
def load_words(path: str = "words.json") -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# 단어 데이터를 파일에 저장한다. 한국어가 깨지지 않게 ensure_ascii=False로 저장한다
def save_words(words: dict, path: str = "words.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)


# 새 단어를 wrong_count 0으로 추가하고 파일에 저장한다. 기존 단어는 그대로 유지한다
def add_word(word: str, meaning: str, path: str = "words.json") -> None:
    words = load_words(path)
    words[word] = {"meaning": meaning, "wrong_count": 0}
    save_words(words, path)
