# wordbook add 명령어가 main()을 통해 실제로 단어를 저장하는지 확인하는 테스트
# 주의: 파일명이 __main__.py라서 그냥 import하면 pytest 자신의 __main__.py가
# 잡혀버린다(sys.modules["__main__"]을 이미 pytest가 선점하고 있기 때문).
# 그래서 importlib으로 파일 경로를 직접 지정해서 불러온다.
import importlib.util
from pathlib import Path

from ai import GrammarCheck, Quiz
from storage import load_words, save_words

_main_path = Path(__file__).resolve().parent.parent / "__main__.py"
_spec = importlib.util.spec_from_file_location("wordbook_cli", _main_path)
wordbook_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wordbook_cli)
main = wordbook_cli.main


class FakeChain:
    # 실제 LLM을 부르지 않고 미리 정해둔 Quiz를 리턴하는 가짜 체인
    def invoke(self, inputs: dict) -> Quiz:
        return Quiz(
            sentence="I ate an ___ for breakfast.",
            options=["apple", "banana", "car", "book"],
            answer="apple",
            explanation="아침 식사로 먹을 수 있는 과일은 apple(사과)입니다.",
        )


class FakeGrammarChain:
    # 실제 LLM을 부르지 않고 항상 문법 통과(전부 True)를 리턴하는 가짜 문법 검사 체인
    def invoke(self, inputs: dict) -> GrammarCheck:
        return GrammarCheck(fits_by_option=[True] * len(inputs["options"]))


def test_add_command_saves_word(tmp_path: Path) -> None:
    # wordbook add apple 사과 실행 시 words.json에 반영된다
    path = tmp_path / "words.json"
    main(["add", "apple", "사과"], path=str(path))
    assert load_words(str(path)) == {"apple": {"meaning": "사과", "wrong_count": 0}}


def test_add_command_tells_user_when_word_is_new(tmp_path, capsys) -> None:
    # 새 단어를 추가하면 새로 추가됐다고 알려준다
    path = tmp_path / "words.json"
    main(["add", "apple", "사과"], path=str(path))
    assert "추가" in capsys.readouterr().out


def test_add_command_tells_user_and_preserves_progress_when_word_exists(tmp_path, capsys) -> None:
    # 이미 있는 단어를 다시 추가하면 업데이트됐다고 알려주고 wrong_count는 보존한다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 3}}, str(path))
    main(["add", "apple", "사과(고친 뜻)"], path=str(path))
    output = capsys.readouterr().out
    assert "이미" in output
    words = load_words(str(path))
    assert words["apple"]["wrong_count"] == 3
    assert words["apple"]["meaning"] == "사과(고친 뜻)"


def test_quiz_command_records_correct_answer(tmp_path: Path) -> None:
    # 정답을 맞히면 wrong_count가 그대로다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 0}}, str(path))
    main(
        ["quiz"],
        path=str(path),
        chain=FakeChain(),
        grammar_chain=FakeGrammarChain(),
        input_func=lambda prompt: "apple",
        today="2026-01-01",
    )
    assert load_words(str(path))["apple"]["wrong_count"] == 0


def test_quiz_command_records_wrong_answer(tmp_path: Path) -> None:
    # 틀리면 wrong_count가 늘고 last_wrong_date가 기록된다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 0}}, str(path))
    main(
        ["quiz"],
        path=str(path),
        chain=FakeChain(),
        grammar_chain=FakeGrammarChain(),
        input_func=lambda prompt: "banana",
        today="2026-01-01",
    )
    words = load_words(str(path))
    assert words["apple"]["wrong_count"] == 1
    assert words["apple"]["last_wrong_date"] == "2026-01-01"


def test_quiz_command_with_no_words_shows_message_instead_of_crashing(tmp_path, capsys) -> None:
    # 단어가 하나도 없을 때 quiz를 실행하면 에러 없이 안내 메시지만 나온다
    path = tmp_path / "words.json"
    main(["quiz"], path=str(path))
    output = capsys.readouterr().out
    assert "단어" in output
    assert load_words(str(path)) == {}


def test_stats_command_prints_calculated_stats(tmp_path, capsys) -> None:
    # wordbook stats 실행 시 calculate_stats 결과가 화면에 출력된다
    path = tmp_path / "words.json"
    save_words(
        {
            "apple": {"meaning": "사과", "wrong_count": 0},
            "banana": {"meaning": "바나나", "wrong_count": 2},
        },
        str(path),
    )
    main(["stats"], path=str(path))
    output = capsys.readouterr().out
    assert "총 단어 수: 2" in output
    assert "틀린 횟수 합계: 2" in output
    assert "완전히 외운 단어 수: 1" in output


CLEAR_MARK = "<<CLEAR>>"


def fake_clear() -> None:
    # 테스트에서 진짜로 화면을 지우는 대신, 지운 위치를 표시만 해둔다
    print(CLEAR_MARK)


def test_interactive_menu_add_then_quit(tmp_path: Path) -> None:
    # 1번(단어 추가) → 엔터(메뉴로) → 5번(종료)으로 단어를 추가할 수 있다
    path = tmp_path / "words.json"
    answers = iter(["1", "apple", "사과", "", "5"])
    main([], path=str(path), input_func=lambda prompt: next(answers), clear_func=fake_clear)
    assert load_words(str(path)) == {"apple": {"meaning": "사과", "wrong_count": 0}}


def test_interactive_menu_quiz_then_quit(tmp_path: Path) -> None:
    # 메뉴에서 2번(퀴즈)을 고르면 run_quiz와 똑같이 동작한다 (오답으로 실제 변화가 있는지 확인)
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 0}}, str(path))
    answers = iter(["2", "banana", "", "5"])
    main(
        [],
        path=str(path),
        chain=FakeChain(),
        grammar_chain=FakeGrammarChain(),
        input_func=lambda prompt: next(answers),
        today="2026-01-01",
        clear_func=fake_clear,
    )
    words = load_words(str(path))
    assert words["apple"]["wrong_count"] == 1
    assert words["apple"]["last_wrong_date"] == "2026-01-01"


def test_interactive_menu_stats_then_quit(tmp_path, capsys) -> None:
    # 메뉴에서 3번(통계)을 고르면 통계가 화면에 출력된다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 0}}, str(path))
    answers = iter(["3", "", "5"])
    main([], path=str(path), input_func=lambda prompt: next(answers), clear_func=fake_clear)
    output = capsys.readouterr().out
    assert "총 단어 수: 1" in output


def test_interactive_menu_list_then_quit(tmp_path, capsys) -> None:
    # 메뉴에서 4번(목록 보기)을 고르면 단어 목록이 화면에 출력된다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 2}}, str(path))
    answers = iter(["4", "", "5"])
    main([], path=str(path), input_func=lambda prompt: next(answers), clear_func=fake_clear)
    output = capsys.readouterr().out
    assert "apple" in output
    assert "사과" in output


def test_quiz_after_list_starts_on_cleared_screen(tmp_path, capsys) -> None:
    # 목록 보기 다음에 퀴즈를 풀면, 목록을 지운 뒤에 문제가 나와서 단어/뜻을 보고 풀 수 없다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 0}}, str(path))
    answers = iter(["4", "", "2", "apple", "", "5"])
    main(
        [],
        path=str(path),
        chain=FakeChain(),
        grammar_chain=FakeGrammarChain(),
        input_func=lambda prompt: next(answers),
        today="2026-01-01",
        clear_func=fake_clear,
    )
    output = capsys.readouterr().out
    list_pos = output.index("틀린 횟수: 0")
    quiz_pos = output.index("I ate an ___")
    last_clear_before_quiz = output.rfind(CLEAR_MARK, 0, quiz_pos)
    assert list_pos < last_clear_before_quiz


def test_interactive_quiz_shows_explanation_with_label(tmp_path, capsys) -> None:
    # 퀴즈 결과에서 해설이 '해설' 제목 아래에 따로 나온다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 0}}, str(path))
    answers = iter(["2", "apple", "", "5"])
    main(
        [],
        path=str(path),
        chain=FakeChain(),
        grammar_chain=FakeGrammarChain(),
        input_func=lambda prompt: next(answers),
        today="2026-01-01",
        clear_func=fake_clear,
    )
    assert "해설" in capsys.readouterr().out


def test_interactive_menu_invalid_choice_shows_message(tmp_path, capsys) -> None:
    # 메뉴에 없는 번호를 입력하면 화면이 조용히 다시 그려지지 않고 안내가 나온다
    path = tmp_path / "words.json"
    answers = iter(["9", "", "5"])
    main([], path=str(path), input_func=lambda prompt: next(answers), clear_func=fake_clear)
    assert "1~5" in capsys.readouterr().out


def test_list_command_shows_word_and_meaning(tmp_path, capsys) -> None:
    # wordbook list 실행 시 단어와 뜻이 화면에 출력된다
    path = tmp_path / "words.json"
    save_words({"apple": {"meaning": "사과", "wrong_count": 1}}, str(path))
    main(["list"], path=str(path))
    output = capsys.readouterr().out
    assert "apple" in output
    assert "사과" in output


def test_list_command_with_no_words_shows_message(tmp_path, capsys) -> None:
    # 단어가 없을 때 wordbook list를 실행하면 안내 메시지가 나온다
    path = tmp_path / "words.json"
    main(["list"], path=str(path))
    assert "단어" in capsys.readouterr().out
