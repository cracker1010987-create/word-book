# 단어와 뜻을 받아 AI가 객관식 퀴즈 문제를 만들어주는 함수들
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from wordbank import normalize_word

load_dotenv()

# 이 파일의 모든 LLM 호출이 쓰는 모델 (CLAUDE.md의 기술 스택과 같게 유지한다)
MODEL = "gpt-5.6-luna"


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
    llm = ChatOpenAI(model=MODEL, temperature=0.7)
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
                "7. 오답 3개 고르는 법: 정답과 같은 범주(같은 품사, 비슷한 상황에서 쓰는 말)에서 고르되, "
                "그 문맥에서 정답과 바꿔 써도 말이 되는 '동의어'는 절대 넣지 마라. 정답이 둘이 되어버린다.\n"
                "  나쁜 예) 정답 warranty인데 오답에 guarantee / 정답 itinerary인데 오답에 schedule "
                "→ 둘 다 맞는 말이라 답을 하나로 고를 수 없다.\n"
                "  나쁜 예) 정답 defective(불량의)인데 오답이 portable, compact, rechargeable "
                "→ '문제 있다'는 뜻이 정답 하나뿐이라 뜻을 몰라도 소거법으로 풀린다.\n"
                "  좋은 예) 정답 defective, 오답 discontinued, counterfeit, unauthorized "
                "→ 같은 '문제 있는 상품' 범주이지만 문맥(과열되어 꺼짐)은 defective만 가리킨다.\n"
                "  오답은 정답과 같은 '의미 축' 위에 있어야 한다. 정답이 돈을 돌려주는 동사라면 오답도 "
                "돈이 오가는 동사(청구하다, 미리 주다 등)로, 정답이 속도를 뜻하는 부사라면 오답도 "
                "속도를 뜻하는 부사(늦게, 점점)로 골라라. 태도나 감정처럼 축이 다른 단어를 넣으면 "
                "뜻을 몰라도 소거법으로 풀린다.\n"
                "  예문에 이미 나온 단어는 오답으로 쓰지 마라. 바로 지워지기 때문이다.\n"
                "8. explanation은 한국어로 쓰되, 사전적 정의나 반의어 나열이 아니라 sentence 안의 "
                "구체적인 단서(문구)를 직접 인용하며 왜 정답이 맞고 나머지가 왜 안 맞는지 설명한다.\n\n"
                "출력하기 전에 스스로 다시 확인해라: "
                "(a) 목표 단어가 options 안에 그대로 있는가 (4번 규칙) "
                "(b) answer가 목표 단어와 정확히 같은가 (3번 규칙) "
                "(c) ___ 바로 뒤 표현이 나머지 3개 보기와도 문법적으로 자연스러운가 (5번 규칙) "
                "(d) sentence에 정답의 의미만을 가리키는 구체적 단서가 있는가, 아니면 보기 4개가 "
                "다 들어맞는 밋밋한 문장인가 (6번 규칙) "
                "(e) 오답 3개를 빈칸에 하나씩 넣어 문장을 끝까지 읽어봐라. 그 문장이 사실로 말이 되면 "
                "그 오답은 버리고 다른 것으로 바꿔라. 반대로 뜻을 몰라도 소거법으로 풀릴 만큼 엉뚱한 "
                "오답이 있어도 바꿔라. 오답은 '문맥에서만' 틀려야 한다 (7번 규칙) "
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
    llm = ChatOpenAI(model=MODEL, temperature=0)
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


# 그 단어가 예문 안에 이미 나오는지 본다 (보기에 있으면 뜻을 몰라도 지울 수 있어서 문제가 된다)
def appears_in_sentence(word: str, sentence: str) -> bool:
    return re.search(rf"\b{re.escape(word.strip().lower())}\b", sentence.lower()) is not None


# 예문에 정답과 어근이 같은 단어가 있는지 본다 (application ↔ applicant처럼 철자만 보고 찍을 수 있다)
def shares_root_with_sentence(word: str, sentence: str) -> bool:
    target = word.strip().lower()
    if len(target) < 6:
        return False
    return any(other.lower().startswith(target[:5]) for other in re.findall(r"[A-Za-z]+", sentence))


# 뜻을 비교하기 전에 떼어내는 꼬리말 (이것까지 같다고 보면 '연기하다'와 '고용하다'가 같은 뜻이 된다)
MEANING_ENDINGS = ("하다", "되다", "시키다", "스럽다", "롭다", "적인")
MEANING_PARTICLES = ("에서", "으로", "을", "를", "의", "이", "가", "은", "는", "에", "로")
# 뜻이 아니라 말버릇에 가까운 낱말들. 이것까지 비교하면 '결석한'과 '신뢰할 수 없는'이 같은 뜻이 된다
MEANING_STOPWORDS = ("수", "것", "등", "있는", "없는", "않은", "않는", "있다", "없다", "같은")


# 뜻 한 조각에서 조사와 '~하다' 같은 꼬리를 뗀다 ("요금을 청구하다" → "요금청구")
def clean_sense(sense: str) -> str:
    cleaned = []
    for word in sense.strip().split():
        if word in MEANING_STOPWORDS:
            continue
        for tail in MEANING_ENDINGS + MEANING_PARTICLES:
            if word.endswith(tail) and len(word) > len(tail) + 1:
                word = word[: -len(tail)]
                break
        cleaned.append(word)
    return "".join(cleaned)


# 한국어 뜻을 쉼표로 쪼개서 비교하기 좋게 다듬는다
def split_senses(meaning_ko: str) -> list[str]:
    return [clean_sense(piece) for piece in meaning_ko.split(",") if clean_sense(piece)]


# 두 낱말이 두 글자 이상 겹치는지 본다 ("요금청구"와 "청구서"는 "청구"가 겹친다)
def shares_two_letters(one: str, other: str) -> bool:
    pairs = {one[i : i + 2] for i in range(len(one) - 1)}
    return any(other[i : i + 2] in pairs for i in range(len(other) - 1))


# 두 단어의 한국어 뜻이 사실상 같은 뜻인지 본다 (뜻 조각끼리 하나라도 겹치면 같다고 본다)
def similar_meaning(one: str, other: str) -> bool:
    return any(
        shares_two_letters(mine, yours) for mine in split_senses(one) for yours in split_senses(other)
    )


# 오답 3개가 서로 같은 뜻으로 뭉쳐 있는지 단어장 뜻으로 확인한다 (단어장에 없는 보기는 건너뛴다)
def distractors_cluster(quiz: Quiz, bank: list[dict]) -> bool:
    meanings = {entry["word"].lower(): entry["meaning_ko"] for entry in bank}
    known = [
        meanings[option.lower()]
        for option in quiz.options
        if option.lower() != quiz.answer.lower() and option.lower() in meanings
    ]
    return any(similar_meaning(one, other) for i, one in enumerate(known) for other in known[i + 1 :])


class DistractorCheck(BaseModel):
    # 오답 보기가 제 역할을 하는지(정답이 둘이 되지 않는지, 너무 뜬금없지 않은지) 판정하는 모델
    also_correct: list[bool] = Field(
        description="options와 같은 순서. 그 보기를 ___ 자리에 넣어 문장을 끝까지 읽었을 때 "
        "사실로 말이 되면 True, 문맥상 틀린 말이 되면 False."
    )
    too_unrelated: list[bool] = Field(
        description="options와 같은 순서. 그 보기가 문맥과 너무 동떨어져서, 단어 뜻을 몰라도 "
        "바로 지울 수 있으면 True. 그럴듯해서 헷갈릴 만하면 False."
    )
    distractors_are_synonyms: bool = Field(
        default=False,
        description="정답을 뺀 오답 3개가 서로 거의 같은 뜻이거나 한 방향으로 뭉쳐 있으면 True "
        "(예: 정답 reimburse에 오답이 charge, bill, invoice → 셋 다 '청구하다'라 정답만 튄다).",
    )
    answer_stands_out: bool = Field(
        default=False,
        description="정답만 유독 어렵거나 격식 있는 단어이고 오답은 다 쉬운 기본 단어여서, "
        "뜻을 몰라도 '튀는 하나'를 고르면 맞힐 수 있으면 True.",
    )


def build_distractor_check_chain() -> Any:
    # 오답 3개가 제 역할을 하는지 검사하는 체인을 만든다
    llm = ChatOpenAI(model=MODEL, temperature=0)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "너는 영어 시험 문제를 검토하는 출제 위원이다. 4지선다 빈칸 문제를 받아서 "
                "보기 하나하나를 빈칸에 넣어보고 두 가지를 판정해라.\n"
                "1) also_correct: 그 보기를 넣어 문장을 끝까지 읽었을 때 사실로 말이 되는가? "
                "말이 되면 True (정답이 둘이 되는 문제라서 걸러내야 한다).\n"
                "2) too_unrelated: 그 보기가 문맥과 너무 동떨어져서, 단어 뜻을 몰라도 바로 "
                "지울 수 있는가? 그렇다면 True (소거법으로 풀리는 문제라서 걸러내야 한다).\n"
                "3) distractors_are_synonyms: 정답을 뺀 오답 3개가 서로 거의 같은 뜻이거나 한 방향으로 "
                "뭉쳐 있는가? 그렇다면 True (정답만 튀어서 소거법으로 풀린다).\n"
                "4) answer_stands_out: 정답만 유독 어려운 단어이고 오답은 다 쉬운 기본 단어인가? "
                "그렇다면 True.\n"
                "좋은 오답은 '그럴듯해 보이지만 문맥을 읽으면 틀린' 것이다. "
                "둘 다 False가 좋은 오답이다. 정답 보기도 순서대로 판정하되, 정답은 "
                "also_correct가 True인 게 당연하다. 관대하게 봐주지 마라.",
            ),
            ("human", "문장: {sentence}\n보기 (이 순서 그대로 판정): {options}\n정답: {answer}\n{meanings}"),
        ]
    )
    return prompt | llm.with_structured_output(DistractorCheck)


# 보기 단어들의 한국어 뜻을 판정 AI에게 같이 알려줄 문장으로 만든다 (뜻을 보여줘야 뭉침을 잘 잡는다)
def options_meanings_text(quiz: Quiz, bank: list[dict] | None) -> str:
    if not bank:
        return ""
    meanings = {entry["word"].lower(): entry["meaning_ko"] for entry in bank}
    known = [f"{option}={meanings[option.lower()]}" for option in quiz.options if option.lower() in meanings]
    return ("보기의 한국어 뜻: " + ", ".join(known)) if known else ""


def check_distractors(quiz: Quiz, distractor_chain: Any = None, bank: list[dict] | None = None) -> bool:
    # 오답 3개가 모두 제 역할을 하는지 확인한다 (정답 보기는 판정에서 뺀다)
    if distractor_chain is None:
        distractor_chain = build_distractor_check_chain()
    result = distractor_chain.invoke(
        {
            "sentence": quiz.sentence,
            "options": quiz.options,
            "answer": quiz.answer,
            "meanings": options_meanings_text(quiz, bank),
        }
    )
    if result.distractors_are_synonyms or result.answer_stands_out:
        return False
    for index, option in enumerate(quiz.options):
        if option == quiz.answer:
            continue
        if result.also_correct[index] or result.too_unrelated[index]:
            return False
    return True


def is_valid_quiz(quiz: Quiz, word: str) -> bool:
    # 퀴즈가 풀 수 있는 모양인지 코드로 확인한다 (정답=목표 단어, 정답이 보기에 있음, 빈칸 있음,
    # 정답 노출 없음, 보기 단어가 예문에 이미 나오지 않음)
    target = word.strip().lower()
    options = [option.strip().lower() for option in quiz.options]
    return (
        quiz.answer.strip().lower() == target
        and target in options
        and len(options) == 4
        and "___" in quiz.sentence
        and not any(appears_in_sentence(option, quiz.sentence) for option in options)
        and not shares_root_with_sentence(target, quiz.sentence)
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
    distractor_chain: Any = None,
    max_attempts: int = 3,
    bank: list[dict] | None = None,
) -> Quiz:
    # 모양 확인 → 뜻 뭉침 검사 → 문법 검사 → 오답 검사를 통과할 때까지(최대 max_attempts번) 다시 만든다
    quiz = None
    valid_fallback = None
    unclustered_fallback = None
    for _ in range(max_attempts):
        quiz = make_quiz(word, meaning, chain=chain)
        if not is_valid_quiz(quiz, word):
            continue
        valid_fallback = quiz
        # 단어장 뜻으로 먼저 걸러낸다 (AI를 부르기 전이라 돈도 시간도 안 든다)
        if bank and distractors_cluster(quiz, bank):
            continue
        unclustered_fallback = quiz
        if not check_grammar(quiz, grammar_chain=grammar_chain):
            continue
        if check_distractors(quiz, distractor_chain=distractor_chain, bank=bank):
            return quiz
    # 다 통과한 퀴즈가 없으면, 그나마 오답이 안 뭉친 퀴즈를 먼저 돌려준다
    return unclustered_fallback or valid_fallback or put_answer_in_options(quiz, word)


class WordMeaning(BaseModel):
    # 단어 하나의 한국어 뜻과 품사를 담는 모델 (서로 다른 뜻을 영어로 먼저 나열한 뒤 한국어를 쓰게 한다)
    word: str = Field(description="요청받은 영어 단어를 철자 그대로")
    senses_en: list[str] = Field(
        default_factory=list,
        description="이 단어의 서로 다른 뜻을 짧은 영어로 먼저 나열한다. 토익에서 쓰이는 뜻을 먼저, 최대 3개. "
        "같은 뜻을 다른 말로 바꿔 여러 번 쓰지 않는다.",
    )
    meaning_ko: str = Field(
        description="senses_en의 뜻마다 대표 한국어를 딱 하나씩, 같은 순서로 쉼표로 구분해 쓴다. "
        "한 뜻에 동의어를 여러 개 붙이지 않는다."
    )
    pos: Literal["noun", "verb", "adjective", "adverb", "other"] = Field(
        description="가장 대표적인 품사 하나"
    )


class MeaningBatch(BaseModel):
    # 여러 단어의 한국어 뜻을 한 번에 담는 모델
    items: list[WordMeaning] = Field(description="요청받은 단어마다 하나씩. 한 단어도 빠뜨리지 않는다.")


def build_meaning_chain() -> Any:
    # 여러 영어 단어를 받아 한국어 뜻과 품사를 한 번에 돌려주는 LCEL 체인을 만든다
    llm = ChatOpenAI(model=MODEL, temperature=0)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "너는 토익을 준비하는 한국인 학생을 위한 영어 단어장 편집자다. "
                "주어진 영어 단어마다 아래 순서대로 정리해라.\n"
                "각 줄은 '단어: 쉬운 영어 뜻' 형식이다. 영어 뜻은 참고용이고, (영어 뜻 없음)이면 네가 아는 뜻을 쓴다.\n\n"
                "1) senses_en: 이 단어가 토익 지문(회사, 거래, 여행, 쇼핑, 일상 업무)과 일상에서 쓰이는 "
                "'서로 다른 뜻'을 짧은 영어로 나열한다. 뜻이 하나뿐이면 1개, 여러 개면 중요한 순서로 최대 3개.\n"
                "   - 명사와 동사처럼 품사가 달라 뜻이 달라지면 서로 다른 뜻으로 센다.\n"
                "   - 같은 뜻을 다른 영어 표현으로 반복하지 않는다.\n"
                "2) meaning_ko: senses_en의 뜻마다 대표 한국어를 딱 하나씩, 같은 순서로 쉼표로 구분해 쓴다.\n\n"
                "예시)\n"
                "- meeting → senses_en: [a gathering to discuss work] / meaning_ko: 회의\n"
                "- order → senses_en: [a request to buy something, to request to buy, arrangement in sequence] "
                "/ meaning_ko: 주문, 주문하다, 순서\n"
                "- bill → senses_en: [a document showing money owed, paper money] / meaning_ko: 청구서, 지폐\n"
                "- address → senses_en: [where someone lives, to deal with a problem] / meaning_ko: 주소, (문제를) 다루다\n"
                "- madam → senses_en: [polite way to address a woman] / meaning_ko: (여성 호칭) ~님\n\n"
                "나쁜 예) criticize: 비판하다, 혹평하다, 비난하다 ← 같은 뜻의 동의어 반복이라 틀림 → 비판하다\n"
                "나쁜 예) interest: 관심 ← 토익에 자주 나오는 '이자'를 빠뜨려서 틀림 → 관심, 이자\n\n"
                "3) pos: 가장 대표적인 품사 하나를 고른다. 전치사·접속사·관사 등은 other.\n"
                "word에는 받은 단어를 철자 그대로 쓰고, 한 단어도 빠뜨리지 마라.",
            ),
            ("human", "{word_list}"),
        ]
    )
    return prompt | llm.with_structured_output(MeaningBatch)


def format_word_list(words: list[dict]) -> str:
    # 단어 묶음을 AI에게 보낼 '단어: 영어 뜻' 줄들로 만든다 (영어 뜻이 없으면 없다고 표시)
    return "\n".join(f"{item['word']}: {item['definition'] or '(영어 뜻 없음)'}" for item in words)


def remove_duplicate_meanings(meaning_ko: str) -> str:
    # 쉼표로 구분된 한국어 뜻에서 똑같은 뜻이 두 번 나오면 한 번만 남긴다
    parts = [part.strip() for part in meaning_ko.split(",") if part.strip()]
    return ", ".join(dict.fromkeys(parts))


def generate_meanings(
    words: list[dict], chain: Any = None, batch_size: int = 20, max_concurrency: int = 5
) -> dict[str, dict]:
    # 단어들을 묶음으로 나눠 병렬로 한국어 뜻을 받고, 요청한 철자 기준으로 모아 돌려준다
    if chain is None:
        chain = build_meaning_chain()
    chunks = [words[i : i + batch_size] for i in range(0, len(words), batch_size)]
    inputs = [{"word_list": format_word_list(chunk)} for chunk in chunks]
    results = chain.batch(inputs, config={"max_concurrency": max_concurrency})
    requested = {normalize_word(item["word"]): item["word"] for item in words}
    meanings = {}
    for result in results:
        for item in result.items:
            word = requested.get(normalize_word(item.word))
            if word and item.meaning_ko.strip():
                meanings[word] = {"meaning_ko": remove_duplicate_meanings(item.meaning_ko), "pos": item.pos}
    return meanings


def generate_all_meanings(
    words: list[dict], chain: Any = None, max_rounds: int = 3, batch_size: int = 20
) -> dict[str, dict]:
    # 뜻을 못 받은 단어만 골라 다시 요청하기를 max_rounds번까지 반복해서, 최대한 모든 단어의 뜻을 받는다
    if chain is None:
        chain = build_meaning_chain()
    meanings: dict[str, dict] = {}
    remaining = list(words)
    for _ in range(max_rounds):
        if not remaining:
            break
        meanings.update(generate_meanings(remaining, chain=chain, batch_size=batch_size))
        remaining = [item for item in remaining if item["word"] not in meanings]
    return meanings


# 연달아 이만큼 실패하면 키나 인터넷 문제로 보고 그만 시도한다
FAILURES_BEFORE_GIVING_UP = 5


# 못 만든 단어들을 한 번에 정리해서 알려준다 (단어마다 오류를 쏟지 않는다)
def summarize_failures(failures: list[tuple[str, str]], total: int) -> None:
    if not failures:
        return
    if len(failures) >= total:
        print(f"\n예문 퀴즈 {total}개 모두 만들지 못했습니다. .env의 OPENAI_API_KEY와 인터넷 연결을 확인해주세요.")
    else:
        print(f"\n예문 퀴즈 {len(failures)}개를 못 만들었습니다. 그 단어는 영어 쓰기로 대신 냅니다.")
    for word, error in failures[:2]:
        print(f"  ({word}: {error})")


def pregenerate_sentence_quizzes(
    words: list[str],
    bank: list[dict],
    chain: Any = None,
    grammar_chain: Any = None,
    distractor_chain: Any = None,
    max_workers: int = 5,
) -> dict[str, dict]:
    # 세트 단어들의 예문 퀴즈를 동시에 여러 개씩 미리 만들어, 저장할 수 있는 형태로 모아 돌려준다
    if chain is None:
        chain = build_chain()
    if grammar_chain is None:
        grammar_chain = build_grammar_check_chain()
    if distractor_chain is None:
        distractor_chain = build_distractor_check_chain()
    meanings = {entry["word"]: entry["meaning_ko"] for entry in bank}
    targets = [word for word in words if word in meanings]
    # 단어 하나에서 API 오류가 나도 나머지는 만들어야 하므로, 실패한 단어만 건너뛴다
    failures: list[tuple[str, str]] = []
    made_any = False

    def make_one(word: str) -> tuple[str, dict | None]:
        nonlocal made_any
        # 계속 실패하는 중이면 더 부르지 않는다 (키가 없으면 50번 다 기다릴 이유가 없다)
        if len(failures) >= FAILURES_BEFORE_GIVING_UP and not made_any:
            return word, None
        try:
            quiz = make_quiz_verified(
                word, meanings[word], chain=chain, grammar_chain=grammar_chain,
                distractor_chain=distractor_chain, bank=bank,
            )
            made_any = True
            return word, quiz.model_dump()
        except Exception as error:
            failures.append((word, str(error)))
            return word, None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        made = {word: quiz for word, quiz in pool.map(make_one, targets) if quiz}
    summarize_failures(failures, len(targets))
    return made
