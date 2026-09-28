# 메뉴 모드(main)가 화면과 파일을 제대로 다루는지 확인하는 테스트
# 주의: 파일명이 __main__.py라서 그냥 import하면 pytest 자신의 __main__.py가
# 잡혀버린다(sys.modules["__main__"]을 이미 pytest가 선점하고 있기 때문).
# 그래서 importlib으로 파일 경로를 직접 지정해서 불러온다.
import importlib.util
import json
from pathlib import Path


_main_path = Path(__file__).resolve().parent.parent / "__main__.py"
_spec = importlib.util.spec_from_file_location("wordbook_cli", _main_path)
wordbook_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wordbook_cli)
main = wordbook_cli.main


def write_old_words(words: dict, path: str) -> None:
    # v1 시절의 words.json을 만든다 (옮겨오기 테스트용)
    Path(path).write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")


CLEAR_MARK = "<<CLEAR>>"


def fake_clear() -> None:
    # 테스트에서 진짜로 화면을 지우는 대신, 지운 위치를 표시만 해둔다
    print(CLEAR_MARK)


def test_interactive_menu_progress_then_quit(tmp_path, capsys, monkeypatch) -> None:
    # 메뉴에서 3번(진도 보기)을 고르면 단어장 전체 진도가 화면에 출력된다
    monkeypatch.chdir(tmp_path)
    answers = iter(["3", "", "6"])
    main([], path="words.json", input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    output = capsys.readouterr().out
    assert "전체 4059단어" in output
    assert "공부한 날" in output


def test_interactive_menu_list_then_quit(tmp_path, capsys, monkeypatch) -> None:
    # 메뉴에서 2번(내 단어)을 고르면 예전 words.json에서 옮겨온 단어가 화면에 출력된다
    monkeypatch.chdir(tmp_path)
    write_old_words({"apple": {"meaning": "사과", "wrong_count": 2}}, "words.json")
    answers = iter(["2", "", "", "6"])
    main([], path="words.json", input_func=lambda prompt: next(answers), clear_func=fake_clear)
    output = capsys.readouterr().out
    assert "apple" in output
    assert "사과" in output


def test_next_menu_screen_starts_after_clearing_the_previous_one(tmp_path, capsys, monkeypatch) -> None:
    # 목록 보기 다음에 다른 메뉴로 가면, 목록을 지운 뒤에 새 화면이 나온다 (앞 화면이 남지 않는다)
    monkeypatch.chdir(tmp_path)
    write_old_words({"apple": {"meaning": "사과", "wrong_count": 0}}, "words.json")
    answers = iter(["2", "", "", "9", "", "6"])
    main([], path="words.json", input_func=lambda prompt: next(answers), clear_func=fake_clear)
    output = capsys.readouterr().out
    list_pos = output.index("1. apple - 사과")
    next_screen_pos = output.index("1~6 중에서")
    assert list_pos < output.rfind(CLEAR_MARK, 0, next_screen_pos)


def test_interactive_menu_invalid_choice_shows_message(tmp_path, capsys) -> None:
    # 메뉴에 없는 번호를 입력하면 화면이 조용히 다시 그려지지 않고 안내가 나온다
    path = tmp_path / "words.json"
    answers = iter(["9", "", "6"])
    main([], path=str(path), input_func=lambda prompt: next(answers), clear_func=fake_clear)
    assert "1~6" in capsys.readouterr().out


def test_menu_add_my_word_saves_into_the_progress_file(tmp_path, capsys, monkeypatch) -> None:
    # 메뉴 2번(내 단어 추가)은 새 구조(progress.json)에 저장하고, 다음 세트에 먼저 나오게 한다
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "a", "brisk", "활기찬, 빠른", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress
    progress = load_progress()
    assert progress["my_words"]["brisk"] == "활기찬, 빠른"
    assert progress["carry_over"] == ["brisk"]


def test_old_words_file_is_moved_into_the_progress_file_once(tmp_path, capsys, monkeypatch) -> None:
    # 예전 words.json이 있으면 처음 실행할 때 내 단어로 옮긴다
    monkeypatch.chdir(tmp_path)
    write_old_words({"elaborate": {"meaning": "정교한", "wrong_count": 2}}, "words.json")
    answers = iter(["3", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress
    assert load_progress()["my_words"]["elaborate"] == "정교한"


def test_menu_list_shows_words_added_through_the_menu(tmp_path, capsys, monkeypatch) -> None:
    # 메뉴 2번으로 넣은 단어는 메뉴 4번(목록 보기)에 나와야 한다
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "a", "brisk", "활기찬", "", "2", "", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    output = capsys.readouterr().out
    assert "1. brisk - 활기찬" in output


def test_menu_list_with_no_my_words_shows_message(tmp_path, capsys, monkeypatch) -> None:
    # 내 단어가 하나도 없으면 목록 보기에서 안내 메시지가 나온다
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    assert "직접 넣은 단어가 없습니다" in capsys.readouterr().out


def test_progress_view_shows_how_many_problems_i_reported(tmp_path, capsys, monkeypatch) -> None:
    # 진도 보기에서 내가 신고한 문제가 몇 개인지 보여준다
    monkeypatch.chdir(tmp_path)
    from progress import default_progress, save_progress
    from reports import report_problem
    save_progress(report_problem(default_progress(), "reimburse", "sentence", "2026-01-01"))
    answers = iter(["3", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-02", clear_func=fake_clear)
    assert "신고한 문제: 1개" in capsys.readouterr().out


def test_empty_word_is_not_added_as_my_word(tmp_path, capsys, monkeypatch) -> None:
    # 메뉴 2번에서 그냥 엔터를 치면 빈 단어가 저장되면 안 된다
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "a", "", "", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress
    assert load_progress()["my_words"] == {}
    assert "단어를 입력" in capsys.readouterr().out


def test_zero_cancels_adding_a_word(tmp_path, capsys, monkeypatch) -> None:
    # 단어 추가 화면에서 0을 치면 아무것도 저장하지 않고 메뉴로 돌아간다
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "a", "0", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress
    assert load_progress()["my_words"] == {}
    assert "취소" in capsys.readouterr().out


def test_zero_cancels_at_the_meaning_step_too(tmp_path, capsys, monkeypatch) -> None:
    # 뜻을 적는 칸에서 0을 쳐도 저장하지 않는다 (단어를 잘못 친 걸 그때 알아챌 수 있다)
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "a", "brisk", "0", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress
    assert load_progress()["my_words"] == {}


def test_menu_list_can_delete_a_word_by_number(tmp_path, capsys, monkeypatch) -> None:
    # 목록 보기에서 번호를 치면 그 단어를 지운다
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "a", "brisk", "활기찬", "", "2", "a", "d", "d", "", "2", "2", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress
    assert list(load_progress()["my_words"]) == ["brisk"]
    assert "지웠습니다" in capsys.readouterr().out


def test_menu_list_enter_goes_back_without_deleting(tmp_path, capsys, monkeypatch) -> None:
    # 목록 보기에서 그냥 엔터를 치면 아무것도 지우지 않고 돌아간다
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "a", "brisk", "활기찬", "", "2", "", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress
    assert list(load_progress()["my_words"]) == ["brisk"]


def test_settings_menu_can_change_the_set_size(tmp_path, capsys, monkeypatch) -> None:
    # 설정 메뉴(4번)에서 세트 크기를 바꿀 수 있다
    monkeypatch.chdir(tmp_path)
    answers = iter(["5", "1", "20", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress
    assert load_progress()["settings"]["set_size"] == 20
    assert "20" in capsys.readouterr().out


def test_settings_menu_enter_leaves_settings_alone(tmp_path, capsys, monkeypatch) -> None:
    # 설정 메뉴에서 그냥 엔터를 치면 설정은 그대로다
    monkeypatch.chdir(tmp_path)
    answers = iter(["5", "", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    from progress import load_progress, DEFAULT_SETTINGS
    assert load_progress()["settings"] == DEFAULT_SETTINGS


def test_my_words_screen_shows_list_and_add_and_delete_in_one_place(tmp_path, capsys, monkeypatch) -> None:
    # 2번 한 곳에서 목록을 보고, a로 추가하고, 번호로 지울 수 있다
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "a", "brisk", "활기찬", "", "2", "", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01", clear_func=fake_clear)
    output = capsys.readouterr().out
    assert "1. brisk - 활기찬" in output
    assert "단어 추가" in output


def make_bank_file(folder, name: str, lines: str) -> str:
    # 테스트용 단어장 파일을 임시 폴더에 만든다
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.csv").write_text(lines, encoding="utf-8")
    return str(folder)


SCHOOL_CSV = "apple,사과\nbrave,용감한\ncandid,솔직한\ndiligent,성실한\n"


def test_bank_menu_lists_banks_and_switches_by_number(tmp_path, capsys, monkeypatch) -> None:
    # 4번 단어장 메뉴에서 번호를 치면 그 단어장으로 바뀐다
    monkeypatch.chdir(tmp_path)
    banks_dir = make_bank_file(tmp_path / "banks", "내신1과", SCHOOL_CSV)
    answers = iter(["", "4", "2", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=banks_dir)
    from progress import load_book
    assert load_book()["current_bank"] == "내신1과"
    assert "내신1과" in capsys.readouterr().out


def test_progress_view_counts_only_the_chosen_bank(tmp_path, capsys, monkeypatch) -> None:
    # 단어장을 바꾸면 진도 보기의 전체 단어 수도 그 단어장 기준이 된다
    monkeypatch.chdir(tmp_path)
    banks_dir = make_bank_file(tmp_path / "banks", "내신1과", SCHOOL_CSV)
    answers = iter(["", "4", "2", "", "3", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=banks_dir)
    assert "전체 4단어" in capsys.readouterr().out


def test_bank_menu_can_delete_a_bank(tmp_path, capsys, monkeypatch) -> None:
    # d와 번호를 함께 치면 그 단어장을 지운다
    monkeypatch.chdir(tmp_path)
    banks_dir = make_bank_file(tmp_path / "banks", "내신1과", SCHOOL_CSV)
    answers = iter(["", "4", "d2", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=banks_dir)
    from banks import bank_names
    assert bank_names(banks_dir=banks_dir) == ["토익"]


def test_bank_menu_cannot_delete_the_builtin_bank(tmp_path, capsys, monkeypatch) -> None:
    # 기본 단어장(1번)은 지울 수 없다고 알려준다
    monkeypatch.chdir(tmp_path)
    answers = iter(["4", "d1", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=str(tmp_path / "banks"))
    assert "지울 수 없습니다" in capsys.readouterr().out


def test_bank_menu_adds_a_bank_from_a_file(tmp_path, capsys, monkeypatch) -> None:
    # a를 치고 파일 경로와 이름을 주면 단어장으로 등록된다
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "교과서.csv"
    source.write_text(SCHOOL_CSV, encoding="utf-8")
    banks_dir = str(tmp_path / "banks")
    answers = iter(["4", "a", str(source), "내신2과", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=banks_dir)
    from banks import bank_names
    assert "내신2과" in bank_names(banks_dir=banks_dir)
    assert "4단어" in capsys.readouterr().out


def test_adding_a_bank_from_a_missing_file_shows_a_message(tmp_path, capsys, monkeypatch) -> None:
    # 없는 파일을 주면 앱이 죽지 않고 안내만 한다
    monkeypatch.chdir(tmp_path)
    answers = iter(["4", "a", str(tmp_path / "없는파일.csv"), "내신", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=str(tmp_path / "banks"))
    assert "파일이 없습니다" in capsys.readouterr().out


def test_app_asks_which_bank_to_use_when_there_are_several(tmp_path, capsys, monkeypatch) -> None:
    # 단어장이 두 개 이상이면 앱을 켤 때 어떤 단어장으로 공부할지 물어본다
    monkeypatch.chdir(tmp_path)
    banks_dir = make_bank_file(tmp_path / "banks", "내신1과", SCHOOL_CSV)
    answers = iter(["2", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=banks_dir)
    from progress import load_book
    assert "어떤 단어장" in capsys.readouterr().out
    assert load_book()["current_bank"] == "내신1과"


def test_app_does_not_ask_when_there_is_only_one_bank(tmp_path, capsys, monkeypatch) -> None:
    # 단어장이 하나뿐이면 묻지 않고 바로 메뉴로 간다
    monkeypatch.chdir(tmp_path)
    answers = iter(["6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=str(tmp_path / "banks"))
    assert "어떤 단어장" not in capsys.readouterr().out


def test_adding_a_bank_with_a_name_already_used_asks_first(tmp_path, capsys, monkeypatch) -> None:
    # 같은 이름이 이미 있으면 덮어쓸지 물어보고, 아니라고 하면 그대로 둔다
    monkeypatch.chdir(tmp_path)
    banks_dir = make_bank_file(tmp_path / "banks", "내신1과", SCHOOL_CSV)
    source = tmp_path / "새파일.csv"
    source.write_text("apple,사과\nbrave,용감한\ncandid,솔직한\neager,열성적인\n", encoding="utf-8")
    answers = iter(["", "4", "a", str(source), "내신1과", "n", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=banks_dir)
    from banks import load_bank
    assert len(load_bank("내신1과", banks_dir=banks_dir)) == 4
    assert "이미 있습니다" in capsys.readouterr().out


def test_answering_yes_overwrites_the_bank(tmp_path, capsys, monkeypatch) -> None:
    # 덮어쓰겠다고 하면 새 파일로 바뀐다
    monkeypatch.chdir(tmp_path)
    banks_dir = make_bank_file(tmp_path / "banks", "내신1과", SCHOOL_CSV)
    source = tmp_path / "새파일.csv"
    source.write_text("apple,사과\nbrave,용감한\ncandid,솔직한\neager,열성적인\n", encoding="utf-8")
    answers = iter(["", "4", "a", str(source), "내신1과", "y", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=banks_dir)
    from banks import load_bank
    assert len(load_bank("내신1과", banks_dir=banks_dir)) == 4


def test_a_bad_bank_name_shows_a_message(tmp_path, capsys, monkeypatch) -> None:
    # 이름에 폴더 기호가 들어가면 안내만 하고 넘어간다
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "새파일.csv"
    source.write_text("apple,사과\nbrave,용감한\ncandid,솔직한\neager,열성적인\n", encoding="utf-8")
    answers = iter(["4", "a", str(source), "../바깥", "", "6"])
    main([], input_func=lambda prompt: next(answers), today="2026-01-01",
         clear_func=fake_clear, banks_dir=str(tmp_path / "banks"))
    assert "쓸 수 없습니다" in capsys.readouterr().out
    assert not (tmp_path / "바깥.csv").exists()
