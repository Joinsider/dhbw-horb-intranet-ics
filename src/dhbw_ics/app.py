import hmac
import logging
from collections import Counter

from fastapi import FastAPI, HTTPException, Query, Response

from .config import Settings
from .db import Database
from .filters import EventFilter
from .ics import build_calendar
from .intranet import IntranetClient
from .service import ScheduleService

log = logging.getLogger(__name__)

_FALSE = {"false", "0", "no", "off"}


def create_app(
        settings: Settings | None = None,
        service: ScheduleService | None = None,
        event_filter: EventFilter | None = None,
) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs full request URLs; keep them out of the logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = settings or Settings.from_env()
    if service is None:
        client = IntranetClient(
            settings.intranet_user, settings.intranet_password, settings.request_delay
        )
        service = ScheduleService(settings, Database(settings.db_path), client)
    if event_filter is None:
        event_filter = EventFilter(settings.filters_file or None)

    app = FastAPI(title="dhbw-intranet-ics", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    def check_key(api_key: str) -> None:
        if not hmac.compare_digest(api_key.encode(), settings.api_key.encode()):
            raise HTTPException(status_code=401, detail="invalid api_key")

    @app.get("/titles")
    def titles(api_key: str = Query(default="")) -> dict[str, list[dict]]:
        """Stored titles with their counts, to write filter rules against."""
        check_key(api_key)
        events = service.events()
        shown = Counter((e.title, e.kind) for e in event_filter.apply(events))
        total = Counter((e.title, e.kind) for e in events)
        return {
            "titles": [
                {"title": title, "kind": kind, "count": n, "excluded": n - shown[(title, kind)]}
                for (title, kind), n in sorted(total.items())
            ]
        }

    @app.get("/calendar.ics")
    def calendar(
            api_key: str = Query(default=""),
            cache: str = Query(default="true"),
    ) -> Response:
        check_key(api_key)

        stale = False
        try:
            service.refresh(force=cache.strip().lower() in _FALSE)
        except Exception:
            # Calendar clients should keep working from the stored data.
            log.exception("refresh failed, serving stored events")
            stale = True

        events = service.events()
        shown = event_filter.apply(events)
        body = build_calendar(shown, settings.kurs)
        return Response(
            content=body,
            media_type="text/calendar; charset=utf-8",
            headers={
                "Cache-Control": "no-store",
                "X-Refresh-Failed": "true" if stale else "false",
                "X-Filtered-Events": str(len(events) - len(shown)),
            },
        )

    return app
