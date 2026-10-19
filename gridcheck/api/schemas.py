"""Request and response bodies of the API."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field


class RequestStatus(StrEnum):
    """Mirrors the ``request_status`` type in ``db/schema.sql``.

    There is no ``running`` status: a request stays ``pending`` while it is checked.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class ConnectionRequestCreate(BaseModel):
    grid_id: str
    bus_id: int
    # Same range and precision as the column NUMERIC(8, 2), so nothing is rounded.
    p_kw: Annotated[Decimal, Field(gt=0, le=1000, decimal_places=2)]


class ConnectionRequest(BaseModel):
    """A row of ``connection_requests``. ``result`` is set once a verdict exists."""

    request_id: int
    grid_id: str
    bus_id: int
    p_kw: float
    status: RequestStatus
    submitted_at: datetime
    finished_at: datetime | None
    result: dict[str, Any] | None
    error: str | None
