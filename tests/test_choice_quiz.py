# AI 없이 단어장만으로 만드는 '영어 보고 뜻 고르기' 4지선다 퀴즈를 확인하는 테스트
import random

import pytest

from choice_quiz import make_meaning_choice_quiz


def bank_entry(word: str, meaning_ko: str, pos: str = "noun") -> dict:
    # 테스트용 단어장 항목을 짧게 만든다
    return {"word": word, "meaning_ko": meaning_ko, "pos": pos, "definition_en": "", "sources": ["TSL"],
            "ngsl_rank": None, "tsl_rank": 1}


BANK = [
    bank_entry("client", "고객"),
    bank_entry("invoice", "송장"),
    bank_entry("warranty", "보증서"),
    bank_entry("refund", "환불"),
    bank_entry("assemble", "조립하다", "verb"),
    bank_entry("disrupt", "방해하다", "verb"),
]


def test_quiz_asks_the_english_word_and_answer_is_its_meaning() -> None:
    # 영어 단어를 묻고, 정답은 그 단어의 한국어 뜻이다
    quiz = make_meaning_choice_quiz("client", BANK, random.Random(1))
    assert quiz["word"] == "client"
    assert quiz["answer"] == "고객"
    assert quiz["answer"] in quiz["options"]


def test_quiz_has_four_options_that_do_not_repeat() -> None:
    # 보기는 4개이고 같은 뜻이 두 번 나오지 않는다
    quiz = make_meaning_choice_quiz("client", BANK, random.Random(2))
    assert len(quiz["options"]) == 4
    assert len(set(quiz["options"])) == 4


def test_wrong_options_come_from_other_words() -> None:
    # 오답 보기는 단어장에 있는 다른 단어의 뜻에서 가져온다
    quiz = make_meaning_choice_quiz("client", BANK, random.Random(3))
    others = {entry["meaning_ko"] for entry in BANK if entry["word"] != "client"}
    assert set(quiz["options"]) - {"고객"} <= others


def test_wrong_options_prefer_the_same_part_of_speech() -> None:
    # 오답도 같은 품사에서 고른다 (품사만 보고 답을 찍지 못하게)
    quiz = make_meaning_choice_quiz("client", BANK, random.Random(4))
    assert set(quiz["options"]) == {"고객", "송장", "보증서", "환불"}


def test_uses_other_parts_of_speech_when_not_enough_same_pos() -> None:
    # 같은 품사 단어가 모자라면 다른 품사에서 채운다 (보기 4개를 유지)
    quiz = make_meaning_choice_quiz("assemble", BANK, random.Random(5))
    assert len(quiz["options"]) == 4
    assert "조립하다" in quiz["options"]


def test_same_seed_gives_the_same_quiz() -> None:
    # 같은 rng를 주면 같은 문제가 나온다 (테스트와 재현을 위해)
    first = make_meaning_choice_quiz("client", BANK, random.Random(7))
    second = make_meaning_choice_quiz("client", BANK, random.Random(7))
    assert first == second


def test_small_bank_makes_a_shorter_quiz() -> None:
    # 단어장이 아주 작으면 있는 만큼만 보기로 만든다 (에러 없이)
    small = [bank_entry("client", "고객"), bank_entry("invoice", "송장")]
    quiz = make_meaning_choice_quiz("client", small, random.Random(8))
    assert sorted(quiz["options"]) == sorted(["고객", "송장"])


def test_unknown_word_raises_a_clear_error() -> None:
    # 단어장에 없는 단어로 문제를 만들려고 하면 바로 알려준다
    with pytest.raises(ValueError, match="없는 단어"):
        make_meaning_choice_quiz("nosuchword", BANK, random.Random(9))
