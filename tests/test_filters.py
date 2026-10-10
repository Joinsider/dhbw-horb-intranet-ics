import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from icalendar import Calendar

from dhbw_ics.app import create_app
from dhbw_ics.filters import EventFilter, FilterError, parse_rules
from dhbw_ics.parser import parse_week

from conftest import load_page
from test_service import KW40, FakeClient, make


def kw40_events():
    return [e for e in parse_week(load_page("kw40"), "HOR-TINF2024").events if e.kind != "holiday"]


def titles(events):
    return sorted(e.title for e in events)


def write(path, text):
    path.write_text(text, encoding="utf-8")
    # Make sure the reload sees a new mtime even on coarse file systems.
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))


def test_exact_titles_ignore_case_and_whitespace(tmp_path):
    path = tmp_path / "filters.toml"
    write(path, '[[exclude]]\ntitle = ["übung_  f. progamm", "Funktionale Programm"]\n')

    shown = EventFilter(str(path)).apply(kw40_events())

    assert "Übung_ F. Progamm" not in titles(shown)
    assert "Funktionale Programm" not in titles(shown)
    assert len(shown) == 9 - 2


def test_fields_of_a_rule_must_all_match(tmp_path):
    path = tmp_path / "filters.toml"
    write(path, '[[exclude]]\ntitle_contains = "Programm"\nperson = "Plümicke"\nkind = "exam"\n')

    assert len(EventFilter(str(path)).apply(kw40_events())) == 9  # no exam in KW 40


def test_rules_are_combined_with_or(tmp_path):
    path = tmp_path / "filters.toml"
    write(path, '[[exclude]]\ntitle_regex = "^GL "\n\n[[exclude]]\nroom = "HOR-121"\n')

    shown = EventFilter(str(path)).apply(kw40_events())

    assert not any(e.title.startswith("GL ") or "HOR-121" in e.room for e in shown)


def test_missing_file_means_no_filter(tmp_path):
    assert len(EventFilter(str(tmp_path / "none.toml")).apply(kw40_events())) == 9


@pytest.mark.parametrize("text", [
    "[[exclude]]\n",
    '[[exclude]]\ntitel = "Recht"\n',
    '[[exclude]]\nkind = "klausur"\n',
    '[[exclude]]\ntitle_regex = "("\n',
    '[[exclude]]\ntitle = ""\n',
    '[exclude]\ntitle = "Recht"\n',
    'exclude = "Recht"\n',
])
def test_invalid_rules_are_rejected(text):
    with pytest.raises(FilterError):
        parse_rules(text)


def test_invalid_file_fails_at_startup_but_not_on_reload(tmp_path):
    path = tmp_path / "filters.toml"
    write(path, "[[exclude]\n")
    with pytest.raises(FilterError):
        EventFilter(str(path))

    write(path, '[[exclude]]\ntitle = "Recht"\n')
    event_filter = EventFilter(str(path))
    write(path, "[[exclude]\n")
    assert "Recht" not in titles(event_filter.apply(kw40_events()))


def test_changes_are_picked_up_without_restart(tmp_path):
    path = tmp_path / "filters.toml"
    event_filter = EventFilter(str(path))
    assert len(event_filter.apply(kw40_events())) == 9

    write(path, '[[exclude]]\ntitle = "Recht"\n')
    assert len(event_filter.apply(kw40_events())) == 8

    path.unlink()
    assert len(event_filter.apply(kw40_events())) == 9


def test_endpoint_hides_filtered_events_and_lists_titles(tmp_path):
    path = tmp_path / "filters.toml"
    write(path, '[[exclude]]\ntitle = ["Übung_ F. Progamm", "Funktionale Programm"]\n')
    settings, service, _ = make(tmp_path, FakeClient({KW40: load_page("kw40")}))
    http = TestClient(create_app(settings, service, EventFilter(str(path))))

    response = http.get("/calendar.ics?api_key=secret")
    summaries = {str(e["SUMMARY"]) for e in Calendar.from_ical(response.content).walk("VEVENT")}
    assert len(summaries) == 6  # 7 events, "Advanced SWE" twice
    assert "Funktionale Programm" not in summaries
    assert response.headers["x-filtered-events"] == "2"

    assert http.get("/titles").status_code == 401
    listed = {t["title"]: t for t in http.get("/titles?api_key=secret").json()["titles"]}
    assert listed["Funktionale Programm"] == {
        "title": "Funktionale Programm", "kind": "lecture", "count": 1, "excluded": 1,
    }
    assert listed["Advanced SWE"]["excluded"] == 0
