import hmac
import logging

from fastapi import FastAPI, HTTPException, Query, Response

from .config import Settings
from .db import Database
from .ics import build_calendar
from .intranet import IntranetClient
from .service import ScheduleService

log = logging.getLogger(__name__)

_FALSE = {"false", "0", "no", "off"}


def create_app(settings: Settings | None = None, service: ScheduleService | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs full request URLs; keep them out of the logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = settings or Settings.from_env()
    if service is None:
        client = IntranetClient(
            settings.intranet_user, settings.intranet_password, settings.request_delay
        )
        service = ScheduleService(settings, Database(settings.db_path), client)

    app = FastAPI(title="dhbw-intranet-ics", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/calendar.ics")
    def calendar(
            api_key: str = Query(default=""),
            cache: str = Query(default="true"),
    ) -> Response:
        if not hmac.compare_digest(api_key.encode(), settings.api_key.encode()):
            raise HTTPException(status_code=401, detail="invalid api_key")

        stale = False
        try:
            service.refresh(force=cache.strip().lower() in _FALSE)
        except Exception:
            # Calendar clients should keep working from the stored data.
            log.exception("refresh failed, serving stored events")
            stale = True

        body = build_calendar(service.events(), settings.kurs)
        return Response(
            content=body,
            media_type="text/calendar; charset=utf-8",
            headers={
                "Cache-Control": "no-store",
                "X-Refresh-Failed": "true" if stale else "false",
            },
        )

    return app
