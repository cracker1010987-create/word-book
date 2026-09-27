# 원본 단어에 순위를 붙이고, NGSL과 TSL을 하나의 단어장으로 합치는 함수들을 확인하는 테스트
import json

import pytest

from wordbank import (
    apply_meaning_fixes,
    attach_ranks,
    load_meaning_fixes,
    load_word_bank,
    make_bank_entries,
    merge_word_lists,
    normalize_word,
    study_order,
)


def test_normalize_word_ignores_case_hyphen_and_accent() -> None:
    # 대소문자, 하이픈, 악센트 차이는 같은 단어로 본다 (e-mail=email, résumé=resume)
    assert normalize_word(" E-mail ") == normalize_word("email")
    assert normalize_word("résumé") == normalize_word("resume")


def test_attach_ranks_matches_spelling_variants() -> None:
    # 뜻 파일의 철자(e-mail)를 유지하면서 순위 파일(email)의 순위를 붙인다
    words = [{"word": "e-mail", "definition": "a message sent by computer"}]
    ranked = [{"word": "email", "rank": 5}]
    assert attach_ranks(words, ranked) == [
        {"word": "e-mail", "definition": "a message sent by computer", "rank": 5}
    ]


def test_attach_ranks_leaves_rank_empty_when_missing() -> None:
    # 순위 파일에 없는 단어(born)는 순위를 None으로 둔다
    words = [{"word": "born", "definition": "brought into life"}]
    assert attach_ranks(words, []) == [{"word": "born", "definition": "brought into life", "rank": None}]


def test_attach_ranks_adds_rank_only_words_without_accents() -> None:
    # 순위 파일에만 있는 단어(café)도 빠뜨리지 않고, 뜻은 비워둔 채 악센트 없는 철자로 추가한다
    assert attach_ranks([], [{"word": "café", "rank": 88}]) == [
        {"word": "cafe", "definition": "", "rank": 88}
    ]


def test_merge_combines_same_word_from_both_lists() -> None:
    # 두 목록에 모두 있는 단어는 하나로 합치고, 출처와 각 순위를 모두 남긴다
    ngsl = [{"word": "Client", "definition": "a customer", "rank": 3}]
    tsl = [{"word": "client", "definition": "someone who pays for a service", "rank": 1}]
    assert merge_word_lists(ngsl, tsl) == [
        {
            "word": "Client",
            "definition": "a customer",
            "sources": ["NGSL", "TSL"],
            "ngsl_rank": 3,
            "tsl_rank": 1,
        }
    ]


def test_merge_interleaves_lists_by_relative_rank() -> None:
    # 각 목록 안에서의 상대 순위(순위/단어 수)로 섞는다. 같으면 NGSL이 먼저
    ngsl = [{"word": f"n{i}", "definition": "", "rank": i} for i in range(1, 5)]
    tsl = [{"word": f"t{i}", "definition": "", "rank": i} for i in range(1, 3)]
    order = [entry["word"] for entry in merge_word_lists(ngsl, tsl)]
    assert order == ["n1", "n2", "t1", "n3", "n4", "t2"]


def test_merge_puts_unranked_words_last() -> None:
    # 순위가 없는 단어는 그 목록의 맨 뒤 순서로 간다
    ngsl = [
        {"word": "born", "definition": "", "rank": None},
        {"word": "the", "definition": "", "rank": 1},
    ]
    order = [entry["word"] for entry in merge_word_lists(ngsl, [])]
    assert order == ["the", "born"]


MERGED = [
    {"word": "client", "definition": "a customer", "sources": ["TSL"], "ngsl_rank": None, "tsl_rank": 3},
    {"word": "the", "definition": "used before nouns", "sources": ["NGSL"], "ngsl_rank": 1, "tsl_rank": None},
]


def test_make_bank_entries_combines_meaning_with_source_info() -> None:
    # 합친 단어 정보(영어 뜻·출처·순위)와 AI가 만든 한국어 뜻·품사를 한 항목으로 묶는다
    meanings = {"client": {"meaning_ko": "고객", "pos": "noun"}, "the": {"meaning_ko": "그", "pos": "other"}}
    assert make_bank_entries(MERGED, meanings)[0] == {
        "word": "client",
        "meaning_ko": "고객",
        "pos": "noun",
        "definition_en": "a customer",
        "sources": ["TSL"],
        "ngsl_rank": None,
        "tsl_rank": 3,
    }


def test_make_bank_entries_keeps_order_and_leaves_out_words_without_meaning() -> None:
    # 순서는 합친 목록 그대로 두고, 한국어 뜻을 끝내 못 받은 단어는 단어장에서 뺀다
    entries = make_bank_entries(MERGED, {"the": {"meaning_ko": "그", "pos": "other"}})
    assert [entry["word"] for entry in entries] == ["the"]


def test_load_word_bank_reads_entries_in_order(tmp_path) -> None:
    # 단어장 JSON 파일을 읽어 순서 그대로 항목 목록을 돌려준다
    path = tmp_path / "word_bank.json"
    entries = [
        {"word": "the", "meaning_ko": "그", "pos": "other", "definition_en": "", "sources": ["NGSL"], "ngsl_rank": 1, "tsl_rank": None},
        {"word": "client", "meaning_ko": "고객", "pos": "noun", "definition_en": "", "sources": ["TSL"], "ngsl_rank": None, "tsl_rank": 3},
    ]
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    assert load_word_bank(str(path)) == entries


def test_load_word_bank_explains_how_to_build_when_missing(tmp_path) -> None:
    # 단어장 파일이 없으면, 만드는 방법(스크립트 이름)을 알려주는 에러를 낸다
    with pytest.raises(FileNotFoundError, match="build_word_bank"):
        load_word_bank(str(tmp_path / "없는파일.json"))


def test_real_word_bank_file_is_complete() -> None:
    # 저장소에 들어있는 실제 단어장이 4,059개이고, 모든 항목에 한국어 뜻과 품사가 있다
    bank = load_word_bank()
    assert len(bank) == 4059
    assert all(entry["meaning_ko"].strip() and entry["pos"] for entry in bank)


FIX_ENTRIES = [
    {"word": "present", "meaning_ko": "선물, 현재의", "pos": "noun"},
    {"word": "invoice", "meaning_ko": "송장", "pos": "noun"},
]


def test_meaning_fix_replaces_the_meaning_of_that_word_only() -> None:
    # 손으로 고쳐둔 뜻이 있으면 그 단어의 뜻만 바뀌고 나머지는 그대로다
    fixed = apply_meaning_fixes(FIX_ENTRIES, {"present": {"meaning_ko": "선물, 현재의, 발표하다"}})
    assert fixed[0]["meaning_ko"] == "선물, 현재의, 발표하다"
    assert fixed[1]["meaning_ko"] == "송장"


def test_meaning_fix_can_also_fix_the_part_of_speech() -> None:
    # 품사가 틀린 단어는 품사도 같이 고칠 수 있다
    fixed = apply_meaning_fixes(FIX_ENTRIES, {"present": {"meaning_ko": "선물", "pos": "verb"}})
    assert fixed[0]["pos"] == "verb"


def test_meaning_fix_for_a_word_not_in_the_bank_is_ignored() -> None:
    # 단어장에 없는 단어를 고쳐두면 그냥 무시한다 (새 단어가 생기지 않는다)
    fixed = apply_meaning_fixes(FIX_ENTRIES, {"nosuchword": {"meaning_ko": "없는 단어"}})
    assert [entry["word"] for entry in fixed] == ["present", "invoice"]


def test_meaning_fix_keeps_the_other_fields() -> None:
    # 고침은 뜻만 바꾸고 출처·순위 같은 다른 항목은 건드리지 않는다
    entries = [{"word": "present", "meaning_ko": "선물", "pos": "noun", "ngsl_rank": 300}]
    fixed = apply_meaning_fixes(entries, {"present": {"meaning_ko": "발표하다"}})
    assert fixed[0]["ngsl_rank"] == 300


def test_load_meaning_fixes_returns_empty_when_there_is_no_file(tmp_path) -> None:
    # 고침 파일이 없으면 고칠 게 없다는 뜻으로 빈 목록을 돌려준다
    assert load_meaning_fixes(str(tmp_path / "없는파일.json")) == {}


def test_load_word_bank_applies_the_fix_file(tmp_path) -> None:
    # 단어장을 불러올 때 고침 파일이 자동으로 반영된다
    import json
    bank_path = tmp_path / "bank.json"
    bank_path.write_text(json.dumps(FIX_ENTRIES, ensure_ascii=False), encoding="utf-8")
    fixes_path = tmp_path / "fixes.json"
    fixes_path.write_text(json.dumps({"present": {"meaning_ko": "발표하다"}}, ensure_ascii=False), encoding="utf-8")
    bank = load_word_bank(str(bank_path), fixes_path=str(fixes_path))
    assert bank[0]["meaning_ko"] == "발표하다"


def test_real_word_bank_has_the_known_bad_meanings_fixed() -> None:
    # 24번에 적어둔 아쉬운 뜻들이 실제 단어장에서 고쳐져 나온다
    meanings = {entry["word"]: entry["meaning_ko"] for entry in load_word_bank()}
    assert "발표하다" in meanings["present"]
    assert "담당" in meanings["charge"]
    assert "쨍하는 소리" not in meanings["clap"]


ORDER_BANK = [
    {"word": "say", "sources": ["NGSL"], "ngsl_rank": 30, "meaning_ko": "말하다"},
    {"word": "supervisor", "sources": ["TSL"], "tsl_rank": 13, "meaning_ko": "감독자"},
    {"word": "asset", "sources": ["NGSL"], "ngsl_rank": 1501, "meaning_ko": "자산"},
    {"word": "report", "sources": ["NGSL", "TSL"], "ngsl_rank": 400, "tsl_rank": 50, "meaning_ko": "보고서"},
]


def test_study_order_puts_toeic_words_first() -> None:
    # 토익(TSL) 단어를 먼저 외우게 앞으로 보낸다
    order = [entry["word"] for entry in study_order(ORDER_BANK, 1500)]
    assert order[:2] == ["supervisor", "report"]


def test_study_order_drops_basic_words_below_the_line() -> None:
    # 기준 순위 안에 드는 기초 단어(say, NGSL 30위)는 아예 빼고, 그보다 어려운 단어는 남긴다
    order = [entry["word"] for entry in study_order(ORDER_BANK, 1500)]
    assert "say" not in order
    assert "asset" in order


def test_a_basic_word_that_is_also_a_toeic_word_stays() -> None:
    # NGSL 400위라도 토익 목록에 있으면 남긴다 (report)
    assert "report" in [entry["word"] for entry in study_order(ORDER_BANK, 1500)]


def test_study_order_keeps_words_with_no_rank_information() -> None:
    # 순위 정보가 없는 단어(내 단어 등)는 판단할 수 없으니 그대로 둔다
    plain = [{"word": "brisk", "meaning_ko": "활기찬"}]
    assert study_order(plain, 1500) == plain


def test_zero_means_do_not_skip_anything() -> None:
    # 0으로 두면 기초 단어를 건너뛰지 않는다 (순서만 토익 먼저)
    order = [entry["word"] for entry in study_order(ORDER_BANK, 0)]
    assert sorted(order) == sorted(entry["word"] for entry in ORDER_BANK)
