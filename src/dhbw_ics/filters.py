import logging
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .parser import KIND_BY_COLOR, Event

log = logging.getLogger(__name__)

KINDS = frozenset(KIND_BY_COLOR.values()) - {"holiday"} | {"other"}
_KEYS = {"title", "title_contains", "title_regex", "person", "room", "kind"}


class FilterError(Exception):
    pass


def _norm(value: str) -> str:
    return " ".join(value.split()).casefold()


def _values(rule: dict, key: str) -> list[str]:
    raw = rule.get(key, [])
    values = [raw] if isinstance(raw, str) else raw
    if not isinstance(values, list) or not all(isinstance(v, str) and v.strip() for v in values):
        raise FilterError(f"{key} must be a non-empty string or a list of them")
    return values


@dataclass(frozen=True)
class Rule:
    """All given fields must match; within a field, one of the values must match."""

    titles: frozenset[str] = frozenset()
    title_contains: tuple[str, ...] = ()
    title_regex: tuple[re.Pattern, ...] = ()
    persons: tuple[str, ...] = ()
    rooms: tuple[str, ...] = ()
    kinds: frozenset[str] = frozenset()

    @classmethod
    def parse(cls, rule: dict) -> "Rule":
        unknown = set(rule) - _KEYS
        if unknown:
            raise FilterError(f"unknown keys {sorted(unknown)}, allowed: {sorted(_KEYS)}")
        if not rule:
            raise FilterError("a rule needs at least one of " + ", ".join(sorted(_KEYS)))
        try:
            patterns = tuple(re.compile(p, re.IGNORECASE) for p in _values(rule, "title_regex"))
        except re.error as exc:
            raise FilterError(f"invalid title_regex: {exc}") from exc
        kinds = frozenset(_values(rule, "kind"))
        if not kinds <= KINDS:
            raise FilterError(f"unknown kind {sorted(kinds - KINDS)}, allowed: {sorted(KINDS)}")
        return cls(
            titles=frozenset(_norm(v) for v in _values(rule, "title")),
            title_contains=tuple(_norm(v) for v in _values(rule, "title_contains")),
            title_regex=patterns,
            persons=tuple(_norm(v) for v in _values(rule, "person")),
            rooms=tuple(_norm(v) for v in _values(rule, "room")),
            kinds=kinds,
        )

    def matches(self, event: Event) -> bool:
        title = _norm(event.title)
        person = _norm(event.person)
        room = _norm(event.room)
        return (
            (not self.titles or title in self.titles)
            and (not self.title_contains or any(v in title for v in self.title_contains))
            and (not self.title_regex or any(p.search(event.title) for p in self.title_regex))
            and (not self.persons or any(v in person for v in self.persons))
            and (not self.rooms or any(v in room for v in self.rooms))
            and (not self.kinds or event.kind in self.kinds)
        )


def parse_rules(text: str) -> tuple[Rule, ...]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise FilterError(f"invalid TOML: {exc}") from exc
    unknown = set(data) - {"exclude"}
    if unknown:
        raise FilterError(f"unknown sections {sorted(unknown)}, expected [[exclude]]")
    rules = data.get("exclude", [])
    if not isinstance(rules, list):
        raise FilterError("exclude must be written as [[exclude]]")
    parsed = []
    for index, rule in enumerate(rules, start=1):
        try:
            parsed.append(Rule.parse(rule))
        except FilterError as exc:
            raise FilterError(f"rule {index}: {exc}") from exc
    return tuple(parsed)


class EventFilter:
    """Exclude rules from a TOML file, reloaded when the file changes.

    A missing file means no filtering. An invalid file is an error at startup;
    later the last valid rules stay active so calendar clients keep working.
    """

    def __init__(self, path: str | None):
        self.path = path
        self._stamp: tuple[int, int] | None = None
        self._rules: tuple[Rule, ...] = ()
        self._load(strict=True)

    @classmethod
    def empty(cls) -> "EventFilter":
        return cls(None)

    def _load(self, strict: bool) -> None:
        if not self.path:
            return
        try:
            stat = os.stat(self.path)
            stamp = (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            stamp = None
        if stamp == self._stamp:
            return
        self._stamp = stamp
        if stamp is None:
            self._rules = ()
            log.info("no filter file at %s, all events are delivered", self.path)
            return
        try:
            self._rules = parse_rules(Path(self.path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, FilterError) as exc:
            if strict:
                raise FilterError(f"{self.path}: {exc}") from exc
            log.error("ignoring changed filter file %s, keeping previous rules: %s", self.path, exc)
            return
        log.info("loaded %d filter rules from %s", len(self._rules), self.path)

    def excludes(self, event: Event) -> bool:
        return any(rule.matches(event) for rule in self._rules)

    def apply(self, events: list[Event]) -> list[Event]:
        self._load(strict=False)
        return [e for e in events if not self.excludes(e)]
