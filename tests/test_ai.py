# build_chain, make_quiz, make_quiz_verified 함수를 확인하는 테스트
from ai import (
    GrammarCheck,
    Quiz,
    build_chain,
    check_grammar,
    is_valid_quiz,
    make_quiz,
    make_quiz_verified,
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
    quiz = make_quiz_verified("elaborate", "정교한", chain=chain, grammar_chain=grammar_chain)
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
    quiz = make_quiz_verified("elaborate", "정교한", chain=chain, grammar_chain=grammar_chain)
    assert quiz is GOOD_QUIZ
    assert chain.calls == 1


def test_make_quiz_verified_retries_when_grammar_check_fails() -> None:
    # 문법 검사에 실패하면 다시 생성해서, 통과하는 퀴즈가 나올 때까지 재시도한다
    chain = SequentialFakeChain([BAD_QUIZ, GOOD_QUIZ])
    grammar_chain = SequentialFakeGrammarChain([ONLY_ANSWER_FITS, ALL_FIT])
    quiz = make_quiz_verified(
        "elaborate", "정교한", chain=chain, grammar_chain=grammar_chain, max_attempts=3
    )
    assert quiz is GOOD_QUIZ
    assert chain.calls == 2


def test_make_quiz_verified_gives_up_after_max_attempts() -> None:
    # max_attempts를 다 써도 통과 못 하면, 마지막 시도 결과를 그대로 돌려준다 (최선의 결과)
    chain = SequentialFakeChain([BAD_QUIZ, BAD_QUIZ, BAD_QUIZ])
    grammar_chain = SequentialFakeGrammarChain([ONLY_ANSWER_FITS] * 3)
    quiz = make_quiz_verified(
        "elaborate", "정교한", chain=chain, grammar_chain=grammar_chain, max_attempts=3
    )
    assert quiz is BAD_QUIZ
    assert chain.calls == 3
