import logging
import time
from datetime import date
from urllib.parse import urljoin

import httpx
from selectolax.lexbor import LexborHTMLParser

log = logging.getLogger(__name__)

BASE_URL = "https://www.hb.dhbw-stuttgart.de"
LOGIN_URL = f"{BASE_URL}/intranet"
TIMETABLE_URL = f"{BASE_URL}/intranet/digitaler-stundenplan"


class LoginFailed(Exception):
    pass


class IntranetClient:
    """Minimal client for the TYPO3 intranet. Requests are throttled."""

    def __init__(self, user: str, password: str, request_delay: float = 2.0):
        self._user = user
        self._password = password
        self._delay = request_delay
        self._last_request = 0.0
        self._http = httpx.Client(
            follow_redirects=True,
            timeout=30,
            headers={"User-Agent": "dhbw-intranet-ics/0.1"},
        )

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        wait = self._last_request + self._delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            response = self._http.request(method, url, **kwargs)
        finally:
            self._last_request = time.monotonic()
        response.raise_for_status()
        return response

    def login(self) -> None:
        """One login attempt. Raises LoginFailed if the intranet rejects it."""
        page = self._request("GET", LOGIN_URL)
        form = _login_form(page.text)
        if form is None:
            log.info("no login form shown, session is still valid")
            return
        action, fields = form
        fields["user"] = self._user
        fields["pass"] = self._password
        result = self._request("POST", urljoin(str(page.url), action), data=fields)
        if _login_form(result.text) is not None:
            raise LoginFailed("intranet still shows the login form after login")
        log.info("intranet login successful")

    def fetch_week(self, kurs: str, day: date) -> str:
        params = {
            "kurs": kurs,
            "day": day.day,
            "month": day.month,
            "year": day.year,
            "goto": "Datum anzeigen",
        }
        return self._request("GET", TIMETABLE_URL, params=params).text


def _login_form(html: str) -> tuple[str, dict[str, str]] | None:
    """Return action and all field values of the felogin form, if present.

    The hidden fields (pid, referer, __referrer, __trustedProperties) and the
    cHash in the action change, so they are read fresh for every login.
    """
    tree = LexborHTMLParser(html)
    for form in tree.css("form"):
        if form.css_first('input[name="pass"]') is None:
            continue
        fields = {
            inp.attributes["name"]: inp.attributes.get("value") or ""
            for inp in form.css("input")
            if inp.attributes.get("name")
        }
        return form.attributes.get("action") or LOGIN_URL, fields
    return None
