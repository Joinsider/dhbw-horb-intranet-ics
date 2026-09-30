from datetime import date, datetime

import pytest

from dhbw_ics.intranet import _login_form
from dhbw_ics.parser import ParseError, SessionExpired, parse_week

from conftest import LOGIN_PAGE

KURS = "HOR-TINF2024"


def test_week_with_lectures_holiday_and_parallel_blocks(kw40):
    page = parse_week(kw40, KURS)

    assert page.days[0] == date(2026, 9, 28)
    assert page.days[-1] == date(2026, 10, 3)
    assert len(page.events) == 10

    by_day = {}
    for e in page.events:
        by_day.setdefault(e.start.date(), []).append(e)
    assert {d: len(v) for d, v in by_day.items()} == {
        date(2026, 9, 28): 2,
        date(2026, 9, 30): 3,
        date(2026, 10, 1): 1,
        date(2026, 10, 2): 3,
        date(2026, 10, 3): 1,
    }

    first = min(by_day[date(2026, 9, 28)], key=lambda e: e.start)
    assert first.start == datetime(2026, 9, 28, 8, 30)
    assert first.end == datetime(2026, 9, 28, 12, 0)
    assert first.title == "GL K. Intelligenz"
    assert first.person == "Prof. Dr. Markus Kaupp"
    assert first.room == "HOR-121"
    assert first.kind == "lecture"

    parallel = [e for e in by_day[date(2026, 10, 2)] if e.title == "Advanced SWE"]
    assert sorted(e.room for e in parallel) == ["HOR-121", "HOR-ONLINE"]

    (holiday,) = by_day[date(2026, 10, 3)]
    assert holiday.kind == "holiday"


def test_exam_week(kw51):
    page = parse_week(kw51, KURS)

    assert len(page.events) == 6
    assert {e.kind for e in page.events} == {"exam"}
    ki = next(e for e in page.events if e.title == "GL K. Intelligenz")
    assert ki.start == datetime(2026, 12, 16, 8, 30)
    assert ki.end == datetime(2026, 12, 16, 9, 30)
    assert ki.room == "HOR-135, HOR-136"
    recht = next(e for e in page.events if e.title == "Recht")
    assert recht.start.date() == date(2026, 12, 17)


def test_login_page_is_session_expired():
    with pytest.raises(SessionExpired):
        parse_week(LOGIN_PAGE, KURS)


def test_wrong_course_is_rejected(kw40):
    with pytest.raises(ParseError):
        parse_week(kw40, "HOR-TINF2025")


def test_login_form_fields():
    action, fields = _login_form(LOGIN_PAGE)
    assert action == "/intranet?cHash=abc"
    assert fields == {"pid": "1@x", "user": "", "pass": "", "logintype": "login"}
    assert _login_form("<html><body><form></form></body></html>") is None
