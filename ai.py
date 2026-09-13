# 단어와 뜻을 받아 AI가 객관식 퀴즈 문제를 만들어주는 함수들
import re
from typing import Any

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()


class Quiz(BaseModel):
    # AI가 만든 퀴즈 문제 하나를 담는 모델
    sentence: str = Field(
        description=(
            "반드시 영어로 된 예문. 목표 영어 단어가 들어갈 자리를 ___ 로 가린다. "
            "정답 단어(또는 그 변형)가 그대로 노출되면 안 된다."
        )
    )
    options: list[str] = Field(
        description="영어 단어 보기 4개 (동의어/유사 품사 위주). 이 중 하나가 정답이다. 한국어 번역을 보기로 쓰지 않는다."
    )
    answer: str = Field(
        description="정답인 영어 단어. 목표로 주어진 영어 단어와 정확히 같아야 하고, options 안에 그대로 있어야 한다."
    )
    explanation: str = Field(
        description=(
            "왜 이 문맥에서 이 답이 맞고 다른 보기들은 왜 틀렸는지, "
            "예문 속 단서와 연결해서 설명하는 한국어 해설 한 줄"
        )
    )


def build_chain() -> Any:
    # 단어와 뜻을 받아 Quiz를 만들어내는 LCEL 체인을 만들어 리턴하는 함수
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "너는 영어 단어 퀴즈를 만드는 선생님이다. "
                "학생은 한국인이고, 목표는 영어 단어를 영어 문장 속에서 배우는 것이다.\n\n"
                "다음 규칙을 모두 지켜서 퀴즈를 만들어라. 하나라도 어기면 안 된다.\n"
                "1. sentence는 반드시 영어 문장이다. 목표 영어 단어가 들어갈 자리를 ___ 로 가린다.\n"
                "2. 목표 영어 단어(또는 그 변형: 복수형, 시제 변화 등)를 sentence 어디에도 그대로 쓰지 않는다.\n"
                "3. answer의 값은 반드시 사용자가 준 '목표 영어 단어'와 글자 그대로 동일하다. "
                "동의어나 다른 단어로 바꾸지 않는다.\n"
                "4. options는 영어 단어 4개의 리스트이고, 그 중 하나는 반드시 answer와 글자 그대로 "
                "동일한 원소여야 한다 (즉 목표 단어가 options 안에 그대로 포함된다). "
                "나머지 3개는 한국어 번역이 아닌 그럴듯한 영어 오답 단어다.\n"
                "5. 문법 규칙: ___ 바로 뒤에 오는 표현(전치사, 부사 등)은 반드시 options 4개 "
                "전부와 문법적으로 자연스럽게 결합해야 한다. 오직 정답 단어 하나만 그 표현과 "
                "결합하고 나머지 3개는 비문법적이 되면 안 된다.\n"
                "나쁜 예 (금지, 'on'은 elaborate만 문법적으로 성립): \"He was asked to ___ on his "
                "plan.\" (describe/summarize/simplify + on 은 비문법적)\n"
                "좋은 예 (금지 아님, 'with'가 4개 보기 모두와 자연스러움): \"She is known for being "
                "___ with her time.\" (stingy/frugal/generous/selfish 모두 'with'와 결합 가능)\n"
                "6. 의미 규칙: sentence에는 정답의 '의미'를 콕 집어 가리키는 구체적인 행동/결과/상황이 "
                "들어가야 한다. 반의어를 4개 늘어놓기만 하고 문맥은 밋밋하게 두면(예: \"그녀는 "
                "___한 것으로 유명하다\"처럼 어떤 성격이든 다 들어맞는 문장), 학생이 의미를 몰라도 "
                "찍을 수 있으므로 안 된다.\n"
                "나쁜 예 (금지, 모든 보기가 다 자연스러움): \"She is known for being ___ with her "
                "time and resources.\"\n"
                "좋은 예 (구체적 행동이 정답만 가리킴): \"Even though she barely knew him, she "
                "___ gave up her weekend to help him move, asking for nothing in return.\"\n"
                "7. explanation은 한국어로 쓰되, 사전적 정의나 반의어 나열이 아니라 sentence 안의 "
                "구체적인 단서(문구)를 직접 인용하며 왜 정답이 맞고 나머지가 왜 안 맞는지 설명한다.\n\n"
                "출력하기 전에 스스로 다시 확인해라: "
                "(a) 목표 단어가 options 안에 그대로 있는가 (4번 규칙) "
                "(b) answer가 목표 단어와 정확히 같은가 (3번 규칙) "
                "(c) ___ 바로 뒤 표현이 나머지 3개 보기와도 문법적으로 자연스러운가 (5번 규칙) "
                "(d) sentence에 정답의 의미만을 가리키는 구체적 단서가 있는가, 아니면 보기 4개가 "
                "다 들어맞는 밋밋한 문장인가 (6번 규칙) "
                "— 하나라도 아니라면 문장을 처음부터 다시 써라.",
            ),
            ("human", "목표 영어 단어: {word}\n한국어 뜻(참고용, 문제에 그대로 쓰지 말 것): {meaning}"),
        ]
    )
    return prompt | llm.with_structured_output(Quiz)


def make_quiz(word: str, meaning: str, chain: Any = None) -> Quiz:
    # 단어와 뜻으로 퀴즈를 하나 만드는 함수. chain을 안 넘기면 기본 체인을 새로 만든다.
    if chain is None:
        chain = build_chain()
    return chain.invoke({"word": word, "meaning": meaning})


class GrammarCheck(BaseModel):
    # options 리스트와 같은 순서로, 각 보기가 빈칸 자리에 자연스러운지 하나씩 담는 모델
    fits_by_option: list[bool] = Field(
        description="options와 같은 순서의 리스트. 각 보기를 ___ 자리에 넣었을 때, 원어민이 "
        "실제로 그렇게 말하는 자연스러운 표현이면 True, 어색하거나 실제로 그렇게 쓰지 않으면 "
        "False. 이론적으로 문법 구조가 성립해도 그 동사/형용사가 뒤따르는 전치사·표현과 "
        "실제로 잘 어울려 쓰이지 않으면 False로 판단해라."
    )


def build_grammar_check_chain() -> Any:
    # 퀴즈 하나가 문법적으로 정답만 노출하는지 검사하는 체인을 만들어 리턴하는 함수
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "너는 깐깐한 영어 원어민 문법 검사관이다. 의미는 신경 쓰지 말고 오직 "
                "'실제로 원어민이 그렇게 쓰는가'만 봐라. "
                "주어진 문장의 ___ 자리에 보기를 하나씩 넣어봤을 때, 각각이 실제로 쓰이는 "
                "자연스러운 표현인지 하나씩 판단해라. "
                "특히 동사 뒤에 오는 전치사(on, at, for, about 등)와 궁합이 맞는 동사만 "
                "자연스럽고, 궁합이 안 맞는 동사는 이론적으로 문장이 되어 보여도 실제로는 "
                "안 쓰는 어색한 표현이니 False로 판단해라. 절대 관대하게 봐주지 마라.",
            ),
            ("human", "문장: {sentence}\n보기 (이 순서 그대로 판단): {options}"),
        ]
    )
    return prompt | llm.with_structured_output(GrammarCheck)


def check_grammar(quiz: Quiz, grammar_chain: Any = None) -> bool:
    # 퀴즈의 보기 4개가 문법적으로 전부 자연스러운지 검사한다
    if grammar_chain is None:
        grammar_chain = build_grammar_check_chain()
    result = grammar_chain.invoke({"sentence": quiz.sentence, "options": quiz.options})
    return all(result.fits_by_option)


def is_valid_quiz(quiz: Quiz, word: str) -> bool:
    # 퀴즈가 풀 수 있는 모양인지 코드로 확인한다 (정답=목표 단어, 정답이 보기에 있음, 빈칸 있음, 정답 노출 없음)
    target = word.strip().lower()
    options = [option.strip().lower() for option in quiz.options]
    return (
        quiz.answer.strip().lower() == target
        and target in options
        and len(options) == 4
        and "___" in quiz.sentence
        and re.search(rf"\b{re.escape(target)}\b", quiz.sentence.lower()) is None
    )


def put_answer_in_options(quiz: Quiz, word: str) -> Quiz:
    # 정답이 보기에 없으면 마지막 보기를 정답으로 바꿔서, 최소한 풀 수 있는 퀴즈로 만든다
    options = list(quiz.options[:4])
    if word.lower() not in [option.lower() for option in options]:
        options[-1] = word
    return quiz.model_copy(update={"answer": word, "options": options})


def make_quiz_verified(
    word: str,
    meaning: str,
    chain: Any = None,
    grammar_chain: Any = None,
    max_attempts: int = 3,
) -> Quiz:
    # 퀴즈 모양 확인과 문법 검사를 둘 다 통과할 때까지(최대 max_attempts번) 다시 만든다
    quiz = None
    valid_fallback = None
    for _ in range(max_attempts):
        quiz = make_quiz(word, meaning, chain=chain)
        if not is_valid_quiz(quiz, word):
            continue
        valid_fallback = quiz
        if check_grammar(quiz, grammar_chain=grammar_chain):
            return quiz
    return valid_fallback or put_answer_in_options(quiz, word)
