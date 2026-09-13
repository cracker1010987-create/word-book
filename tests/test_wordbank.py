# 원본 단어에 순위를 붙이고, NGSL과 TSL을 하나의 단어장으로 합치는 함수들을 확인하는 테스트
from wordbank import attach_ranks, merge_word_lists, normalize_word


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
