import re
from dataclasses import dataclass
from datetime import date, datetime, time

from selectolax.lexbor import LexborHTMLParser

# The block type is only visible through the background colour (see ADR 0005).
KIND_BY_COLOR = {
    "#a3ddff": "lecture",
    "#f79f81": "exam",
    "#cc00cc": "oral_exam",
    "#df0101": "holiday",
}

_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{2})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\D+(\d{1,2}):(\d{2})")
_COLOR_RE = re.compile(r"background-color:\s*(#[0-9a-fA-F]{6})")


class SessionExpired(Exception):
    """The response is not a timetable page (usually the login page)."""


class ParseError(Exception):
    pass


@dataclass(frozen=True)
class Event:
    start: datetime  # naive, Europe/Berlin wall time
    end: datetime
    title: str
    person: str
    room: str
    kind: str
    color: str


@dataclass(frozen=True)
class WeekPage:
    days: list[date]
    events: list[Event]


def _span(node) -> int:
    try:
        return max(1, int(node))
    except (TypeError, ValueError):
        return 1


def _text(node) -> str:
    return " ".join(node.text().replace("\xa0", " ").split()) if node else ""


def parse_week(html: str, kurs: str) -> WeekPage:
    tree = LexborHTMLParser(html)
    table = tree.css_first("table.week_table")
    if table is None:
        raise SessionExpired("no timetable in response")
    title = tree.css_first("h2.title")
    if title is None or _text(title) != kurs:
        raise ParseError(f"page does not show course {kurs}")

    # Column ranges per day. Column 0 is the time column.
    day_columns: list[tuple[int, int, date]] = []
    col = 1
    for header in table.css("td.week_header"):
        match = _DATE_RE.search(header.text())
        if not match:
            raise ParseError(f"unexpected day header: {header.text()!r}")
        day, month, year = (int(g) for g in match.groups())
        width = _span(header.attributes.get("colspan"))
        day_columns.append((col, col + width - 1, date(2000 + year, month, day)))
        col += width
    if not day_columns:
        raise ParseError("no day headers found")

    # The weekday of a block is only given by its column, so rebuild the grid
    # the way a browser lays it out (rowspan/colspan).
    events: list[Event] = []
    occupied: dict[int, set[int]] = {}
    for row_index, row in enumerate(table.css("tr")):
        taken = occupied.setdefault(row_index, set())
        col = 0
        for cell in row.iter():
            if cell.tag not in ("td", "th"):
                continue
            while col in taken:
                col += 1
            width = _span(cell.attributes.get("colspan"))
            height = _span(cell.attributes.get("rowspan"))
            for r in range(row_index, row_index + height):
                occupied.setdefault(r, set()).update(range(col, col + width))
            if "week_block" in (cell.attributes.get("class") or "").split():
                day = next((d for a, b, d in day_columns if a <= col <= b), None)
                if day is None:
                    raise ParseError(f"block in column {col} matches no day")
                events.append(_parse_block(cell, day, kurs))
            col += width

    return WeekPage(days=[d for _, _, d in day_columns], events=events)


def _parse_block(cell, day: date, kurs: str) -> Event:
    match = _TIME_RE.search(_text(cell.css_first("span.time")))
    if not match:
        raise ParseError(f"block without time on {day}")
    h1, m1, h2, m2 = (int(g) for g in match.groups())
    title = _text(cell.css_first("span.name"))
    resources = [_text(r) for r in cell.css("span.resource")]
    rooms = [r for r in resources if r and r != kurs]
    color_match = _COLOR_RE.search(cell.attributes.get("style") or "")
    color = color_match.group(1).lower() if color_match else ""
    kind = "holiday" if title == "Feiertag" else KIND_BY_COLOR.get(color, "other")
    return Event(
        start=datetime.combine(day, time(h1, m1)),
        end=datetime.combine(day, time(h2, m2)),
        title=title,
        person=_text(cell.css_first("span.person")),
        room=", ".join(p.strip() for r in rooms for p in r.split(";") if p.strip()),
        kind=kind,
        color=color,
    )
