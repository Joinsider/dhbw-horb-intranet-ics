import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from icalendar import Calendar
from icalendar import Event as IcsEvent

from .parser import Event

BERLIN = ZoneInfo("Europe/Berlin")

_SUMMARY_PREFIX = {"exam": "Klausur: "}
_CATEGORY = {
    "lecture": "Vorlesung",
    "exam": "Klausur",
    "oral_exam": "Mündliche Prüfung",
}


def build_calendar(events: list[Event], kurs: str) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//dhbw-intranet-ics//DE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"DHBW Horb {kurs}")
    cal.add("x-wr-timezone", "Europe/Berlin")
    cal.add("refresh-interval", timedelta(minutes=30), parameters={"value": "DURATION"})
    cal.add("x-published-ttl", timedelta(minutes=30))

    stamp = datetime.now(timezone.utc)
    for event in events:
        item = IcsEvent()
        item.add("uid", _uid(event, kurs))
        item.add("dtstamp", stamp)
        # UTC times need no VTIMEZONE block and work in every client.
        item.add("dtstart", event.start.replace(tzinfo=BERLIN).astimezone(timezone.utc))
        item.add("dtend", event.end.replace(tzinfo=BERLIN).astimezone(timezone.utc))
        item.add("summary", _SUMMARY_PREFIX.get(event.kind, "") + event.title)
        if event.room:
            item.add("location", event.room)
        if event.person:
            item.add("description", f"Dozent: {event.person}")
        if event.kind in _CATEGORY:
            item.add("categories", [_CATEGORY[event.kind]])
        cal.add_component(item)
    return cal.to_ical()


def _uid(event: Event, kurs: str) -> str:
    # The intranet has no event IDs, so the UID is derived from the content.
    raw = "|".join(
        [kurs, event.start.isoformat(), event.end.isoformat(),
         event.title, event.person, event.room, event.kind]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest() + "@dhbw-intranet-ics"
