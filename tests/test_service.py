from datetime import date

import pytest
from fastapi.testclient import TestClient
from icalendar import Calendar

from dhbw_ics.app import create_app
from dhbw_ics.config import Settings
from dhbw_ics.db import Database
from dhbw_ics.intranet import LoginFailed
from dhbw_ics.service import ScheduleService

from conftest import LOGIN_PAGE, load_page

KURS = "HOR-TINF2024"


class FakeClient:
    def __init__(self, pages, logged_in=True, login_ok=True):
        self.pages = pages  # Monday -> html
        self.logged_in = logged_in
        self.login_ok = login_ok
        self.fetches = []
        self.logins = 0

    def login(self):
        self.logins += 1
        if not self.login_ok:
            raise LoginFailed("rejected")
        self.logged_in = True

    def fetch_week(self, kurs, day):
        self.fetches.append(day)
        return self.pages[day] if self.logged_in else LOGIN_PAGE


class Clock:
    def __init__(self, now=1_000_000.0, today=date(2026, 9, 30)):
        self.now = now
        self.today = today


def make(tmp_path, client, weeks_ahead=0, clock=None):
    clock = clock or Clock()
    settings = Settings(
        api_key="secret", intranet_user="u", intranet_password="p",
        kurs=KURS, weeks_ahead=weeks_ahead, db_path=str(tmp_path / "db.sqlite"),
    )
    service = ScheduleService(
        settings, Database(settings.db_path), client,
        now=lambda: clock.now, today=lambda: clock.today,
    )
    return settings, service, clock


KW40 = date(2026, 9, 28)


def test_fetches_once_and_then_serves_from_cache(tmp_path):
    client = FakeClient({KW40: load_page("kw40")})
    _, service, clock = make(tmp_path, client)

    service.refresh()
    clock.now += 1800
    service.refresh()

    assert client.fetches == [KW40]
    events = service.events()
    assert len(events) == 9  # 10 blocks minus the holiday
    assert all(e.kind != "holiday" for e in events)


def test_cache_expires_after_ttl(tmp_path):
    client = FakeClient({KW40: load_page("kw40")})
    _, service, clock = make(tmp_path, client)

    service.refresh()
    clock.now += 3600
    service.refresh()

    assert client.fetches == [KW40, KW40]
    assert len(service.events()) == 9  # replaced, not duplicated


def test_force_respects_minimum_interval(tmp_path):
    client = FakeClient({KW40: load_page("kw40")})
    _, service, clock = make(tmp_path, client)

    service.refresh()
    clock.now += 299
    service.refresh(force=True)
    assert client.fetches == [KW40]

    clock.now += 1
    service.refresh(force=True)
    assert client.fetches == [KW40, KW40]


def test_only_requested_number_of_weeks(tmp_path):
    pages = {KW40: load_page("kw40"), date(2026, 12, 14): load_page("kw51")}
    client = FakeClient(pages)
    _, service, _ = make(tmp_path, client, weeks_ahead=0)
    service.refresh()
    assert client.fetches == [KW40]


def test_past_weeks_are_kept_but_not_fetched_again(tmp_path):
    pages = {KW40: load_page("kw40"), date(2026, 12, 14): load_page("kw51")}
    client = FakeClient(pages)
    _, service, clock = make(tmp_path, client)

    service.refresh()
    clock.today = date(2026, 12, 15)
    clock.now += 86400 * 76
    service.refresh()

    assert client.fetches == [KW40, date(2026, 12, 14)]
    assert len(service.events()) == 9 + 6


def test_logs_in_when_session_is_missing(tmp_path):
    client = FakeClient({KW40: load_page("kw40")}, logged_in=False)
    _, service, _ = make(tmp_path, client)

    service.refresh()

    assert client.logins == 1
    assert len(service.events()) == 9


def test_login_is_retried_at_most_twice_and_then_blocked(tmp_path):
    client = FakeClient({KW40: load_page("kw40")}, logged_in=False, login_ok=False)
    _, service, clock = make(tmp_path, client)

    with pytest.raises(LoginFailed):
        service.refresh()
    assert client.logins == 3

    clock.now += 3600
    service.refresh()  # blocked: no request, no login
    assert client.logins == 3
    assert client.fetches == [KW40]


def test_endpoint_requires_api_key_and_returns_ics(tmp_path):
    client = FakeClient({KW40: load_page("kw40")})
    settings, service, _ = make(tmp_path, client)
    http = TestClient(create_app(settings, service))

    assert http.get("/calendar.ics").status_code == 401
    assert http.get("/calendar.ics?api_key=wrong").status_code == 401

    response = http.get("/calendar.ics?api_key=secret")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    events = Calendar.from_ical(response.content).walk("VEVENT")
    assert len(events) == 9
    first = min(events, key=lambda e: e["DTSTART"].dt)
    assert str(first["SUMMARY"]) == "GL K. Intelligenz"
    assert str(first["LOCATION"]) == "HOR-121"
    assert "Kaupp" in str(first["DESCRIPTION"])
    assert first["DTSTART"].dt.isoformat() == "2026-09-28T06:30:00+00:00"  # 08:30 CEST

    http.get("/calendar.ics?api_key=secret&cache=false")
    assert client.fetches == [KW40]  # within the 5 minute minimum interval


def test_endpoint_serves_stored_events_when_refresh_fails(tmp_path):
    client = FakeClient({KW40: load_page("kw40")})
    settings, service, clock = make(tmp_path, client)
    http = TestClient(create_app(settings, service))
    http.get("/calendar.ics?api_key=secret")

    client.pages = {}
    clock.now += 7200
    response = http.get("/calendar.ics?api_key=secret")

    assert response.status_code == 200
    assert response.headers["x-refresh-failed"] == "true"
    assert len(Calendar.from_ical(response.content).walk("VEVENT")) == 9


def test_exams_get_a_prefix(tmp_path):
    client = FakeClient({date(2026, 12, 14): load_page("kw51")})
    settings, service, _ = make(tmp_path, client, clock=Clock(today=date(2026, 12, 14)))
    http = TestClient(create_app(settings, service))

    events = Calendar.from_ical(http.get("/calendar.ics?api_key=secret").content).walk("VEVENT")
    assert sorted(str(e["SUMMARY"]) for e in events)[0] == "Klausur: Consulting+tech.Vert"
