# build_chain, make_quiz, make_quiz_verified 함수를 확인하는 테스트
import json
from ai import (
    DistractorCheck,
    GrammarCheck,
    MeaningBatch,
    Quiz,
    WordMeaning,
    build_chain,
    check_distractors,
    check_grammar,
    generate_all_meanings,
    generate_meanings,
    distractors_cluster,
    is_valid_quiz,
    make_quiz,
    make_quiz_verified,
    pregenerate_sentence_quizzes,
    similar_meaning,
)


class FakeChain:
    # 실제 LLM을 부르지 않고 미리 정해둔 Quiz를 리턴하는 가짜 체인
    def invoke(self, inputs: dict) -> Quiz:
        return Quiz(
            sentence="I ate an ___ for breakfast.",
            options=["apple", "banana", "car", "book"],
            answer="apple",
            explanation="아침 식사로 먹을 수 있는 과일은 apple(사과)입니다.",
        )


class SequentialFakeChain:
    # 호출할 때마다 미리 정해둔 Quiz를 순서대로 하나씩 리턴하는 가짜 체인 (재시도 확인용)
    def __init__(self, quizzes: list[Quiz]) -> None:
        self.quizzes = quizzes
        self.calls = 0

    def invoke(self, inputs: dict) -> Quiz:
        quiz = self.quizzes[self.calls]
        self.calls += 1
        return quiz


class SequentialFakeGrammarChain:
    # 호출할 때마다 미리 정해둔 GrammarCheck를 순서대로 하나씩 리턴하는 가짜 체인
    def __init__(self, results: list[GrammarCheck]) -> None:
        self.results = results
        self.calls = 0

    def invoke(self, inputs: dict) -> GrammarCheck:
        result = self.results[self.calls]
        self.calls += 1
        return result


class AlwaysGoodDistractorChain:
    # 오답 검사를 항상 통과시키는 가짜 체인 (다른 것을 확인하는 테스트에서 쓴다)
    def invoke(self, inputs: dict) -> "DistractorCheck":
        count = len(inputs["options"])
        return DistractorCheck(also_correct=[False] * count, too_unrelated=[False] * count)


BAD_QUIZ = Quiz(
    sentence="He was asked to ___ on his plan.",
    options=["describe", "summarize", "simplify", "elaborate"],
    answer="elaborate",
    explanation="on 때문에 elaborate만 문법적으로 맞다.",
)
GOOD_QUIZ = Quiz(
    sentence="Regarding his plan, he was asked to ___.",
    options=["describe", "summarize", "simplify", "elaborate"],
    answer="elaborate",
    explanation="네 보기 모두 문법적으로 자연스럽다.",
)
# 실제로 나왔던 버그: 정답(elaborate)이 보기 안에 없어서 보기만 보고는 맞힐 수 없는 문제
MISSING_ANSWER_QUIZ = Quiz(
    sentence="The scientist was asked to ___ on the findings.",
    options=["summarize", "explain", "expand", "describe"],
    answer="elaborate",
    explanation="정답이 보기에 없다.",
)


def test_is_valid_quiz_accepts_good_quiz() -> None:
    # 정답이 목표 단어이고 보기 안에 있으면 올바른 퀴즈다
    assert is_valid_quiz(GOOD_QUIZ, "elaborate") is True


def test_is_valid_quiz_rejects_answer_missing_from_options() -> None:
    # 정답이 보기 4개 중에 없으면 풀 수 없는 퀴즈다
    assert is_valid_quiz(MISSING_ANSWER_QUIZ, "elaborate") is False


def test_is_valid_quiz_rejects_answer_different_from_word() -> None:
    # 정답이 목표 단어가 아닌 다른 단어로 바뀌어 있으면 안 된다
    quiz = GOOD_QUIZ.model_copy(update={"answer": "describe"})
    assert is_valid_quiz(quiz, "elaborate") is False


def test_is_valid_quiz_rejects_word_leaked_in_sentence() -> None:
    # 예문에 정답 단어가 그대로 적혀 있으면 안 된다
    quiz = GOOD_QUIZ.model_copy(update={"sentence": "Please elaborate, he said, and ___."})
    assert is_valid_quiz(quiz, "elaborate") is False


def test_make_quiz_verified_retries_when_answer_missing_from_options() -> None:
    # 정답이 보기에 없는 퀴즈가 나오면 문법 검사도 안 하고 바로 다시 만든다
    chain = SequentialFakeChain([MISSING_ANSWER_QUIZ, GOOD_QUIZ])
    grammar_chain = SequentialFakeGrammarChain([GrammarCheck(fits_by_option=[True] * 4)])
    quiz = make_quiz_verified(
        "elaborate", "정교한", chain=chain, grammar_chain=grammar_chain,
        distractor_chain=AlwaysGoodDistractorChain(),
    )
    assert quiz is GOOD_QUIZ
    assert chain.calls == 2
    assert grammar_chain.calls == 1


def test_make_quiz_verified_never_returns_unsolvable_quiz() -> None:
    # 끝까지 정답이 보기에 없는 퀴즈만 나와도, 정답을 보기에 넣어서 풀 수 있게 만들어 돌려준다
    chain = SequentialFakeChain([MISSING_ANSWER_QUIZ] * 3)
    grammar_chain = SequentialFakeGrammarChain([])
    quiz = make_quiz_verified(
        "elaborate", "정교한", chain=chain, grammar_chain=grammar_chain, max_attempts=3
    )
    assert quiz.answer == "elaborate"
    assert "elaborate" in quiz.options
    assert len(quiz.options) == 4


def test_build_chain_returns_runnable_without_calling_api() -> None:
    # 체인 생성만으로는 실제 API를 호출하지 않고, invoke 가능한 객체가 만들어지는지 확인
    chain = build_chain()
    assert hasattr(chain, "invoke")


def test_returns_quiz_shape() -> None:
    # 결과가 Quiz 모양인지 확인
    quiz = make_quiz("apple", "사과", chain=FakeChain())
    assert isinstance(quiz, Quiz)


def test_options_has_four_items() -> None:
    # options가 4개인지 확인
    quiz = make_quiz("apple", "사과", chain=FakeChain())
    assert len(quiz.options) == 4


def test_answer_is_in_options() -> None:
    # answer가 options 안에 들어있는지 확인
    quiz = make_quiz("apple", "사과", chain=FakeChain())
    assert quiz.answer in quiz.options


def test_sentence_has_blank() -> None:
    # sentence에 ___ 가 들어있는지 확인
    quiz = make_quiz("apple", "사과", chain=FakeChain())
    assert "___" in quiz.sentence


ALL_FIT = GrammarCheck(fits_by_option=[True, True, True, True])
# BAD_QUIZ의 options 순서: describe, summarize, simplify, elaborate → elaborate만 자연스러움
ONLY_ANSWER_FITS = GrammarCheck(fits_by_option=[False, False, False, True])


def test_check_grammar_fails_when_only_one_option_fits() -> None:
    # 보기 중 하나만 자연스럽고 나머지는 아니면 False (전치사 노출 상황)
    grammar_chain = SequentialFakeGrammarChain([ONLY_ANSWER_FITS])
    assert check_grammar(BAD_QUIZ, grammar_chain=grammar_chain) is False


def test_check_grammar_passes_when_all_options_fit() -> None:
    # 보기 4개가 전부 자연스러우면 True
    grammar_chain = SequentialFakeGrammarChain([ALL_FIT])
    assert check_grammar(GOOD_QUIZ, grammar_chain=grammar_chain) is True


def test_make_quiz_verified_returns_first_try_when_grammar_ok() -> None:
    # 문법 검사를 처음부터 통과하면 재시도 없이 그 퀴즈를 그대로 돌려준다
    chain = SequentialFakeChain([GOOD_QUIZ])
    grammar_chain = SequentialFakeGrammarChain([ALL_FIT])
    quiz = make_quiz_verified(
        "elaborate", "정교한", chain=chain, grammar_chain=grammar_chain,
        distractor_chain=AlwaysGoodDistractorChain(),
    )
    assert quiz is GOOD_QUIZ
    assert chain.calls == 1


def test_make_quiz_verified_retries_when_grammar_check_fails() -> None:
    # 문법 검사에 실패하면 다시 생성해서, 통과하는 퀴즈가 나올 때까지 재시도한다
    chain = SequentialFakeChain([BAD_QUIZ, GOOD_QUIZ])
    grammar_chain = SequentialFakeGrammarChain([ONLY_ANSWER_FITS, ALL_FIT])
    quiz = make_quiz_verified(
        "elaborate", "정교한", chain=chain, grammar_chain=grammar_chain, max_attempts=3,
        distractor_chain=AlwaysGoodDistractorChain(),
    )
    assert quiz is GOOD_QUIZ
    assert chain.calls == 2


def test_make_quiz_verified_gives_up_after_max_attempts() -> None:
    # max_attempts를 다 써도 통과 못 하면, 마지막 시도 결과를 그대로 돌려준다 (최선의 결과)
    chain = SequentialFakeChain([BAD_QUIZ, BAD_QUIZ, BAD_QUIZ])
    grammar_chain = SequentialFakeGrammarChain([ONLY_ANSWER_FITS] * 3)
    quiz = make_quiz_verified(
        "elaborate", "정교한", chain=chain, grammar_chain=grammar_chain, max_attempts=3,
        distractor_chain=AlwaysGoodDistractorChain(),
    )
    assert quiz is BAD_QUIZ
    assert chain.calls == 3


class FakeMeaningChain:
    # 실제 LLM 대신, batch로 받은 입력을 기록하고 미리 정해둔 MeaningBatch를 순서대로 돌려주는 가짜 체인
    def __init__(self, responses: list[MeaningBatch]) -> None:
        self.responses = responses
        self.inputs: list[dict] = []
        self.batch_calls = 0

    def batch(self, inputs: list[dict], config: dict | None = None) -> list[MeaningBatch]:
        self.batch_calls += 1
        self.inputs.extend(inputs)
        return self.responses[: len(inputs)]


def meaning(word: str, meaning_ko: str, pos: str = "noun") -> WordMeaning:
    # 테스트용 WordMeaning을 짧게 만든다
    return WordMeaning(word=word, meaning_ko=meaning_ko, pos=pos)


def test_generate_meanings_sends_english_definition_as_reference() -> None:
    # 원본의 쉬운 영어 뜻을 AI에게 참고로 넘기고, 한국어 뜻과 품사를 돌려받는다
    chain = FakeMeaningChain([MeaningBatch(items=[meaning("abuse", "학대하다, 남용하다", "verb")])])
    result = generate_meanings([{"word": "abuse", "definition": "to treat badly"}], chain=chain)
    assert "to treat badly" in chain.inputs[0]["word_list"]
    assert result == {"abuse": {"meaning_ko": "학대하다, 남용하다", "pos": "verb"}}


def test_generate_meanings_marks_words_without_definition() -> None:
    # 영어 뜻이 없는 단어(e-book 등)는 뜻이 없다고 표시해서 넘긴다
    chain = FakeMeaningChain([MeaningBatch(items=[meaning("e-book", "전자책")])])
    generate_meanings([{"word": "e-book", "definition": ""}], chain=chain)
    assert "(영어 뜻 없음)" in chain.inputs[0]["word_list"]


def test_generate_meanings_splits_words_into_batches_in_one_parallel_call() -> None:
    # 5단어를 2개씩 묶으면 묶음 3개를 한 번의 batch 호출로 병렬 처리하고 결과를 합친다
    words = [{"word": w, "definition": "d"} for w in ["a1", "a2", "a3", "a4", "a5"]]
    responses = [
        MeaningBatch(items=[meaning("a1", "뜻1"), meaning("a2", "뜻2")]),
        MeaningBatch(items=[meaning("a3", "뜻3"), meaning("a4", "뜻4")]),
        MeaningBatch(items=[meaning("a5", "뜻5")]),
    ]
    chain = FakeMeaningChain(responses)
    result = generate_meanings(words, chain=chain, batch_size=2)
    assert chain.batch_calls == 1
    assert len(chain.inputs) == 3
    assert sorted(result) == ["a1", "a2", "a3", "a4", "a5"]


def test_generate_meanings_matches_changed_spelling_and_ignores_extra_words() -> None:
    # AI가 철자를 바꿔 돌려줘도(E-mail) 요청한 철자(e-mail)로 저장하고, 요청 안 한 단어는 버린다
    chain = FakeMeaningChain(
        [MeaningBatch(items=[meaning("E-mail", "이메일"), meaning("banana", "바나나")])]
    )
    result = generate_meanings([{"word": "e-mail", "definition": "a message"}], chain=chain)
    assert result == {"e-mail": {"meaning_ko": "이메일", "pos": "noun"}}


def test_generate_meanings_leaves_out_missing_or_blank_meanings() -> None:
    # AI가 빠뜨렸거나 뜻을 비워서 돌려준 단어는 결과에 넣지 않는다 (나중에 다시 요청할 수 있게)
    chain = FakeMeaningChain([MeaningBatch(items=[meaning("add", "  ")])])
    words = [{"word": "add", "definition": "d"}, {"word": "habit", "definition": "d"}]
    assert generate_meanings(words, chain=chain) == {}


class RoundFakeMeaningChain:
    # batch를 부를 때마다 그 회차에 정해둔 MeaningBatch 목록을 돌려주는 가짜 체인 (재요청 확인용)
    def __init__(self, rounds: list[list[MeaningBatch]]) -> None:
        self.rounds = rounds
        self.inputs_by_call: list[list[dict]] = []

    def batch(self, inputs: list[dict], config: dict | None = None) -> list[MeaningBatch]:
        responses = self.rounds[len(self.inputs_by_call)]
        self.inputs_by_call.append(inputs)
        return responses[: len(inputs)]


def test_generate_all_meanings_requests_again_only_missing_words() -> None:
    # 첫 요청에서 빠진 단어(habit)만 다시 요청해서, 결국 모든 단어의 뜻을 받는다
    chain = RoundFakeMeaningChain(
        [
            [MeaningBatch(items=[meaning("add", "더하다", "verb")])],
            [MeaningBatch(items=[meaning("habit", "습관")])],
        ]
    )
    words = [{"word": "add", "definition": "d"}, {"word": "habit", "definition": "d"}]
    result = generate_all_meanings(words, chain=chain)
    assert sorted(result) == ["add", "habit"]
    assert "add" not in chain.inputs_by_call[1][0]["word_list"]
    assert "habit" in chain.inputs_by_call[1][0]["word_list"]


def test_generate_all_meanings_gives_up_after_max_rounds() -> None:
    # 끝까지 뜻을 못 받으면 max_rounds번만 요청하고 멈춘다 (무한 반복 방지)
    chain = RoundFakeMeaningChain([[MeaningBatch(items=[])]] * 3)
    result = generate_all_meanings([{"word": "add", "definition": "d"}], chain=chain, max_rounds=3)
    assert result == {}
    assert len(chain.inputs_by_call) == 3


class WordFakeChain:
    # 요청한 단어에 맞는 Quiz를 돌려주는 가짜 체인 (여러 단어를 동시에 처리할 때 씀)
    def __init__(self, quizzes: dict) -> None:
        self.quizzes = quizzes
        self.words_asked: list[str] = []
        self.meanings_asked: list[str] = []

    def invoke(self, inputs: dict) -> Quiz:
        self.words_asked.append(inputs["word"])
        self.meanings_asked.append(inputs["meaning"])
        return self.quizzes[inputs["word"]]


class AlwaysFitGrammarChain:
    # 문법 검사를 항상 통과시키는 가짜 체인
    def invoke(self, inputs: dict) -> GrammarCheck:
        return GrammarCheck(fits_by_option=[True] * len(inputs["options"]))


def quiz_for(word: str) -> Quiz:
    # 테스트용 예문 퀴즈를 짧게 만든다 (예문에 정답 단어를 쓰면 안 되므로 빈칸만 둔다)
    return Quiz(
        sentence="Please sign the ___ before Friday.",
        options=[word, "aaa", "bbb", "ccc"],
        answer=word,
        explanation="해설",
    )


QUIZ_BANK = [
    {"word": "invoice", "meaning_ko": "송장, 청구서", "pos": "noun"},
    {"word": "warranty", "meaning_ko": "보증", "pos": "noun"},
]


def test_pregenerate_makes_a_quiz_for_each_word() -> None:
    # 준 단어마다 예문 퀴즈를 하나씩 만들어 단어별로 모아 돌려준다
    chain = WordFakeChain({"invoice": quiz_for("invoice"), "warranty": quiz_for("warranty")})
    quizzes = pregenerate_sentence_quizzes(
        ["invoice", "warranty"], QUIZ_BANK, chain=chain, grammar_chain=AlwaysFitGrammarChain(), distractor_chain=AlwaysGoodDistractorChain()
    )
    assert sorted(quizzes) == ["invoice", "warranty"]
    assert quizzes["invoice"]["answer"] == "invoice"


def test_pregenerate_sends_the_korean_meaning_from_the_bank() -> None:
    # 퀴즈를 만들 때 단어장에 있는 한국어 뜻을 같이 넘긴다
    chain = WordFakeChain({"invoice": quiz_for("invoice")})
    pregenerate_sentence_quizzes(
        ["invoice"], QUIZ_BANK, chain=chain, grammar_chain=AlwaysFitGrammarChain(), distractor_chain=AlwaysGoodDistractorChain()
    )
    assert chain.meanings_asked == ["송장, 청구서"]


def test_pregenerate_skips_words_that_are_not_in_the_bank() -> None:
    # 단어장에 없는 단어는 건너뛴다 (에러 없이)
    chain = WordFakeChain({"invoice": quiz_for("invoice")})
    quizzes = pregenerate_sentence_quizzes(
        ["invoice", "nosuchword"], QUIZ_BANK, chain=chain, grammar_chain=AlwaysFitGrammarChain(), distractor_chain=AlwaysGoodDistractorChain()
    )
    assert sorted(quizzes) == ["invoice"]


def test_pregenerate_returns_plain_data_that_can_be_saved_to_json() -> None:
    # 결과는 progress.json에 그대로 저장할 수 있는 단순한 자료여야 한다
    chain = WordFakeChain({"invoice": quiz_for("invoice")})
    quizzes = pregenerate_sentence_quizzes(
        ["invoice"], QUIZ_BANK, chain=chain, grammar_chain=AlwaysFitGrammarChain(), distractor_chain=AlwaysGoodDistractorChain()
    )
    assert json.loads(json.dumps(quizzes, ensure_ascii=False)) == quizzes
    assert sorted(quizzes["invoice"]) == ["answer", "explanation", "options", "sentence"]


def test_is_valid_quiz_rejects_option_that_already_appears_in_the_sentence() -> None:
    # 예문에 이미 나온 단어를 오답으로 쓰면 안 된다 (뜻을 몰라도 지울 수 있어서)
    quiz = Quiz(
        sentence="The renter reported a leak to the landlord, and the ___ signed the lease.",
        options=["tenant", "landlord", "inspector", "neighbor"],
        answer="tenant",
        explanation="해설",
    )
    assert is_valid_quiz(quiz, "tenant") is False


class FakeDistractorChain:
    # 오답 검사를 흉내내는 가짜 체인 (options 순서대로 판정 결과를 돌려준다)
    def __init__(self, results: list[DistractorCheck]) -> None:
        self.results = results
        self.calls = 0

    def invoke(self, inputs: dict) -> DistractorCheck:
        result = self.results[self.calls]
        self.calls += 1
        return result


# GOOD_QUIZ의 options 순서: describe, summarize, simplify, elaborate (정답은 마지막)
def distractor_check(also_correct: list[bool], too_unrelated: list[bool]) -> DistractorCheck:
    # 테스트용 오답 검사 결과를 짧게 만든다
    return DistractorCheck(also_correct=also_correct, too_unrelated=too_unrelated)


def test_distractors_pass_when_no_option_also_works_and_none_is_unrelated() -> None:
    # 오답을 넣었을 때 참이 되지도 않고, 뜬금없지도 않으면 통과
    chain = FakeDistractorChain([distractor_check([False] * 4, [False] * 4)])
    assert check_distractors(GOOD_QUIZ, distractor_chain=chain) is True


def test_distractors_fail_when_one_option_would_also_be_correct() -> None:
    # 오답 중 하나라도 넣어서 말이 되면 정답이 둘이 되므로 실패
    chain = FakeDistractorChain([distractor_check([True, False, False, False], [False] * 4)])
    assert check_distractors(GOOD_QUIZ, distractor_chain=chain) is False


def test_distractors_fail_when_one_option_is_too_unrelated() -> None:
    # 뜻을 몰라도 지워질 만큼 동떨어진 오답이 있으면 실패 (소거법으로 풀리는 문제)
    chain = FakeDistractorChain([distractor_check([False] * 4, [False, True, False, False])])
    assert check_distractors(GOOD_QUIZ, distractor_chain=chain) is False


def test_distractor_check_ignores_the_answer_itself() -> None:
    # 정답 자리에 '넣으면 맞는 말이 된다'고 표시돼도 그건 당연하므로 무시한다
    chain = FakeDistractorChain([distractor_check([False, False, False, True], [False] * 4)])
    assert check_distractors(GOOD_QUIZ, distractor_chain=chain) is True


def test_make_quiz_verified_retries_when_distractors_are_bad() -> None:
    # 오답 검사에 걸리면 퀴즈를 다시 만든다
    chain = SequentialFakeChain([GOOD_QUIZ, GOOD_QUIZ])
    grammar_chain = SequentialFakeGrammarChain([ALL_FIT, ALL_FIT])
    distractor_chain = FakeDistractorChain(
        [distractor_check([True, False, False, False], [False] * 4), distractor_check([False] * 4, [False] * 4)]
    )
    quiz = make_quiz_verified(
        "elaborate", "정교한", chain=chain, grammar_chain=grammar_chain, distractor_chain=distractor_chain
    )
    assert quiz is GOOD_QUIZ
    assert chain.calls == 2
    assert distractor_chain.calls == 2


def test_distractors_fail_when_they_all_mean_the_same_thing() -> None:
    # 오답끼리 같은 뜻으로 뭉쳐 있으면(charge/bill/invoice) 정답만 튀어서 소거법으로 풀린다
    chain = FakeDistractorChain(
        [DistractorCheck(also_correct=[False] * 4, too_unrelated=[False] * 4, distractors_are_synonyms=True)]
    )
    assert check_distractors(GOOD_QUIZ, distractor_chain=chain) is False


def test_distractors_fail_when_only_the_answer_is_a_hard_word() -> None:
    # 오답만 쉬운 기본 단어여서 어려운 정답이 튀어 보이면 안 된다 (punctual vs early/late/absent)
    chain = FakeDistractorChain(
        [DistractorCheck(also_correct=[False] * 4, too_unrelated=[False] * 4, answer_stands_out=True)]
    )
    assert check_distractors(GOOD_QUIZ, distractor_chain=chain) is False


def test_is_valid_quiz_rejects_sentence_sharing_the_answer_word_root() -> None:
    # 예문에 정답과 어근이 같은 단어(application ↔ applicant)가 있으면 철자만 보고 찍을 수 있다
    quiz = Quiz(
        sentence="The recruiter read the online application before calling the ___ for an interview.",
        options=["applicant", "supplier", "inspector", "volunteer"],
        answer="applicant",
        explanation="해설",
    )
    assert is_valid_quiz(quiz, "applicant") is False


class FailingChain:
    # 특정 단어에서만 API 오류가 나는 상황을 흉내내는 가짜 체인
    def __init__(self, quizzes: dict, failing_word: str) -> None:
        self.quizzes = quizzes
        self.failing_word = failing_word

    def invoke(self, inputs: dict) -> Quiz:
        if inputs["word"] == self.failing_word:
            raise RuntimeError("API 오류")
        return self.quizzes[inputs["word"]]


def test_pregenerate_skips_a_word_that_fails_instead_of_stopping_everything() -> None:
    # 단어 하나에서 오류가 나도 나머지 단어의 퀴즈는 만들어 돌려준다 (학습이 멈추지 않게)
    chain = FailingChain({"invoice": quiz_for("invoice")}, failing_word="warranty")
    quizzes = pregenerate_sentence_quizzes(
        ["invoice", "warranty"], QUIZ_BANK, chain=chain,
        grammar_chain=AlwaysFitGrammarChain(), distractor_chain=AlwaysGoodDistractorChain(),
    )
    assert sorted(quizzes) == ["invoice"]


# 뜻이 뭉치는지 코드로 확인할 때 쓰는 작은 단어장
CLUSTER_BANK = [
    {"word": "reimburse", "meaning_ko": "환급하다", "pos": "verb"},
    {"word": "charge", "meaning_ko": "요금을 청구하다, 요금, 담당", "pos": "verb"},
    {"word": "bill", "meaning_ko": "청구서, 계산서", "pos": "noun"},
    {"word": "invoice", "meaning_ko": "송장", "pos": "noun"},
    {"word": "postpone", "meaning_ko": "연기하다", "pos": "verb"},
    {"word": "hire", "meaning_ko": "고용하다", "pos": "verb"},
]


def cluster_quiz(options: list[str], answer: str = "reimburse") -> Quiz:
    # 뜻 뭉침 검사에 넣을 퀴즈 하나를 만든다
    return Quiz(sentence="The company will ___ your travel costs.", options=options, answer=answer, explanation="")


def test_similar_meaning_sees_through_endings_and_particles() -> None:
    # '요금을 청구하다'와 '청구서'는 같은 뜻으로 본다 (조사와 '~하다'는 떼고 비교한다)
    assert similar_meaning("요금을 청구하다, 요금, 담당", "청구서, 계산서") is True
    assert similar_meaning("환급하다", "송장") is False
    # '~하다'만 같다고 비슷하다고 보면 안 된다 (연기하다 vs 고용하다)
    assert similar_meaning("연기하다", "고용하다") is False


def test_distractors_cluster_when_two_of_them_mean_the_same() -> None:
    # 오답 3개 중 둘이 같은 뜻이면(charge/bill) 뭉친 것으로 보고 걸러낸다
    quiz = cluster_quiz(["reimburse", "charge", "bill", "invoice"])
    assert distractors_cluster(quiz, CLUSTER_BANK) is True


def test_distractors_do_not_cluster_when_meanings_are_all_different() -> None:
    # 오답끼리 뜻이 서로 다르면 통과한다
    quiz = cluster_quiz(["reimburse", "postpone", "hire", "invoice"])
    assert distractors_cluster(quiz, CLUSTER_BANK) is False


def test_words_missing_from_the_bank_are_not_treated_as_clustered() -> None:
    # 단어장에 없는 보기는 뜻을 모르니 뭉쳤다고 단정하지 않는다
    quiz = cluster_quiz(["reimburse", "aaa", "bbb", "ccc"])
    assert distractors_cluster(quiz, CLUSTER_BANK) is False


def test_make_quiz_verified_retries_when_distractor_meanings_cluster() -> None:
    # AI 검사를 통과해도 오답 뜻이 뭉쳐 있으면 코드가 걸러서 다시 만든다
    clustered = cluster_quiz(["reimburse", "charge", "bill", "invoice"])
    clean = cluster_quiz(["reimburse", "postpone", "hire", "invoice"])
    chain = SequentialFakeChain([clustered, clean])
    quiz = make_quiz_verified(
        "reimburse", "환급하다", chain=chain,
        grammar_chain=AlwaysFitGrammarChain(), distractor_chain=AlwaysGoodDistractorChain(),
        bank=CLUSTER_BANK,
    )
    assert quiz is clean
    assert chain.calls == 2


def test_quiz_is_not_cluster_checked_without_a_bank() -> None:
    # 단어장을 안 넘기면(예전처럼 부를 때) 뜻 뭉침 검사는 건너뛴다
    clustered = cluster_quiz(["reimburse", "charge", "bill", "invoice"])
    chain = SequentialFakeChain([clustered])
    quiz = make_quiz_verified(
        "reimburse", "환급하다", chain=chain,
        grammar_chain=AlwaysFitGrammarChain(), distractor_chain=AlwaysGoodDistractorChain(),
    )
    assert quiz is clustered


def test_only_sharing_a_negative_ending_is_not_the_same_meaning() -> None:
    # '결석한'과 '신뢰할 수 없는'은 '없는'만 같을 뿐 같은 뜻이 아니다
    assert similar_meaning("없는, 결석한", "신뢰할 수 없는") is False
    assert similar_meaning("믿을 수 있는", "먹을 수 있는") is False


def test_fallback_prefers_a_quiz_whose_distractors_do_not_cluster() -> None:
    # 끝까지 다 통과하는 퀴즈를 못 만들면, 그래도 뜻이 안 뭉친 쪽을 돌려준다
    clustered = cluster_quiz(["reimburse", "charge", "bill", "invoice"])
    clean = cluster_quiz(["reimburse", "postpone", "hire", "invoice"])
    chain = SequentialFakeChain([clustered, clean, clustered])
    quiz = make_quiz_verified(
        "reimburse", "환급하다", chain=chain,
        grammar_chain=AlwaysFitGrammarChain(), distractor_chain=AlwaysBadDistractorChain(),
        bank=CLUSTER_BANK,
    )
    assert quiz is clean


class AlwaysBadDistractorChain:
    # 오답 검사를 항상 떨어뜨리는 가짜 체인 (되돌림 동작을 확인할 때 쓴다)
    def invoke(self, inputs: dict) -> DistractorCheck:
        count = len(inputs["options"])
        return DistractorCheck(
            also_correct=[False] * count, too_unrelated=[False] * count, distractors_are_synonyms=True
        )
