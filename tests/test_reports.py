# "이 문제 이상해요" 신고를 기록하는 함수들을 확인하는 테스트
from progress import default_progress, fill_missing_parts
from reports import report_problem, reported_words


def test_report_is_recorded_with_word_kind_and_date() -> None:
    # 신고하면 어떤 단어의 어떤 문제를 언제 신고했는지 기록에 남는다
    progress = report_problem(default_progress(), "reimburse", "sentence", "2026-01-01")
    assert progress["reports"] == [{"word": "reimburse", "kind": "sentence", "date": "2026-01-01"}]


def test_reporting_a_sentence_quiz_throws_away_the_cached_quiz() -> None:
    # 예문 퀴즈를 신고하면 미리 만들어둔 퀴즈를 버려서 다음에 새로 만들게 한다
    progress = default_progress()
    progress["quiz_cache"] = {"reimburse": {"answer": "reimburse"}, "invoice": {"answer": "invoice"}}
    after = report_problem(progress, "reimburse", "sentence", "2026-01-01")
    assert "reimburse" not in after["quiz_cache"]
    assert "invoice" in after["quiz_cache"]


def test_reporting_a_meaning_quiz_keeps_the_quiz_cache() -> None:
    # 뜻 고르기를 신고한 것은 뜻 문제이므로 예문 퀴즈 캐시는 건드리지 않는다
    progress = default_progress()
    progress["quiz_cache"] = {"present": {"answer": "present"}}
    after = report_problem(progress, "present", "meaning_choice", "2026-01-01")
    assert after["quiz_cache"] == {"present": {"answer": "present"}}
    assert after["reports"][0]["kind"] == "meaning_choice"


def test_same_word_can_be_reported_more_than_once() -> None:
    # 같은 단어를 또 신고하면 기록이 쌓인다 (몇 번 신고됐는지 알 수 있게)
    progress = report_problem(default_progress(), "charge", "meaning_choice", "2026-01-01")
    progress = report_problem(progress, "charge", "sentence", "2026-01-05")
    assert len(progress["reports"]) == 2


def test_reported_words_counts_each_word_once() -> None:
    # 신고된 단어 목록은 중복 없이 보여준다 (나중에 뜻이나 퀴즈를 고칠 때 쓴다)
    progress = report_problem(default_progress(), "charge", "meaning_choice", "2026-01-01")
    progress = report_problem(progress, "charge", "sentence", "2026-01-05")
    progress = report_problem(progress, "present", "meaning_choice", "2026-01-05")
    assert reported_words(progress) == ["charge", "present"]


def test_old_progress_file_without_reports_still_loads() -> None:
    # 신고 기능이 없던 시절의 기록 파일을 열어도 reports 항목이 생긴다
    assert fill_missing_parts({"words": {}, "carry_over": []})["reports"] == []
