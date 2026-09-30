from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# The fixtures are real timetable tables (fetched 2026-09-30) with the empty
# grid cells replaced by two-character tokens to keep the files small.
_CELLS = {
    "§a": "week_smallseparatorcell_black",
    "§b": "week_emptycell_black",
    "§c": "week_separatorcell_black",
    "§d": "week_smallseparatorcell",
    "§e": "week_emptycell",
    "§f": "week_separatorcell",
}


def load_page(name: str, kurs: str = "HOR-TINF2024") -> str:
    table = (FIXTURES / f"{name}.min.html").read_text(encoding="utf-8")
    for token, cls in _CELLS.items():
        table = table.replace(token, f'<td class="{cls}">&nbsp;</td>')
    return (
        "<html><body><form></form>"
        f'<h2 class="title"> {kurs} </h2><div id="calendar">{table}</div>'
        "</body></html>"
    )


LOGIN_PAGE = (
    '<html><body><form method="post" action="/intranet?cHash=abc">'
    '<input type="hidden" name="pid" value="1@x">'
    '<input type="text" name="user"><input type="password" name="pass">'
    '<input type="hidden" name="logintype" value="login">'
    "</form></body></html>"
)


@pytest.fixture
def kw40() -> str:
    return load_page("kw40")


@pytest.fixture
def kw51() -> str:
    return load_page("kw51")
