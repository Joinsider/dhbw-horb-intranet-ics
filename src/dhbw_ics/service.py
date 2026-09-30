import logging
import threading
import time
from datetime import date, timedelta
from typing import Callable

from .config import Settings
from .db import Database
from .intranet import IntranetClient, LoginFailed
from .parser import Event, ParseError, SessionExpired, parse_week

log = logging.getLogger(__name__)

_LAST_FETCH_KEY = "last_fetch"


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


class ScheduleService:
    def __init__(
            self,
            settings: Settings,
            db: Database,
            client: IntranetClient,
            now: Callable[[], float] = time.time,
            today: Callable[[], date] = date.today,
    ):
        self._settings = settings
        self._db = db
        self._client = client
        self._now = now
        self._today = today
        self._lock = threading.Lock()
        self._login_blocked_until = 0.0

    def target_weeks(self) -> list[date]:
        """Current week plus WEEKS_AHEAD future weeks, as Mondays."""
        first = week_start(self._today())
        return [first + timedelta(weeks=i) for i in range(self._settings.weeks_ahead + 1)]

    def events(self) -> list[Event]:
        horizon = self.target_weeks()[-1] + timedelta(weeks=1)
        return self._db.events(self._settings.kurs, before=horizon)

    def refresh(self, force: bool = False) -> None:
        """Fetch stale current/future weeks. Past weeks are never fetched again."""
        with self._lock:
            kurs = self._settings.kurs
            now = self._now()
            fetched = self._db.fetched_at(kurs)
            weeks = [
                w for w in self.target_weeks()
                if force or now - fetched.get(w, 0.0) >= self._settings.cache_ttl
            ]
            if not weeks:
                return
            last_fetch = float(self._db.get_meta(_LAST_FETCH_KEY) or 0)
            if now - last_fetch < self._settings.min_fetch_interval:
                log.info("skipping intranet fetch, last one was %.0fs ago", now - last_fetch)
                return
            if now < self._login_blocked_until:
                log.warning("skipping intranet fetch, login is blocked after repeated failures")
                return
            # Set before fetching so that failed runs are rate limited as well.
            self._db.set_meta(_LAST_FETCH_KEY, str(now))

            logged_in = False
            for week in weeks:
                html = self._client.fetch_week(kurs, week)
                try:
                    page = parse_week(html, kurs)
                except SessionExpired:
                    if logged_in:
                        raise ParseError("no timetable although login succeeded")
                    self._login()
                    logged_in = True
                    page = parse_week(self._client.fetch_week(kurs, week), kurs)
                if week_start(page.days[0]) != week:
                    raise ParseError(f"asked for week {week}, got {page.days[0]}")
                events = [e for e in page.events if e.kind != "holiday"]
                self._db.replace_week(kurs, week, events, self._now())
                log.info("stored week %s with %d events", week, len(events))

    def _login(self) -> None:
        attempts = 1 + self._settings.login_retries
        for attempt in range(1, attempts + 1):
            try:
                self._client.login()
                return
            except LoginFailed as exc:
                log.warning("login attempt %d/%d failed: %s", attempt, attempts, exc)
        self._login_blocked_until = self._now() + self._settings.login_cooldown
        raise LoginFailed(f"giving up after {attempts} login attempts")
