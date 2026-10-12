"""API models. These Pydantic classes are the service's contract: requests are
validated against them and responses are shaped by them."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

CapCondition = Literal["good", "worn", "missing"]
WorkOrderKind = Literal["repair", "flush", "paint", "replace_cap", "flow_test", "other"]
Priority = Literal["low", "normal", "high", "urgent"]
WorkOrderStatus = Literal["open", "assigned", "closed"]
HydrantStatus = Literal["in_service", "out_of_service"]


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    size: int
    total: int


class HydrantSummary(BaseModel):
    hydrant_id: str
    street: str
    alt_street: str
    jurisdiction: str
    lat: float
    lng: float
    status: HydrantStatus
    last_inspected_at: datetime | None = None


class Hydrant(HydrantSummary):
    elevation_ft: float | None
    municipality: str
    subdivision: str
    county: str
    state: str
    hydrant_type: str
    gps_quality: int | None
    survey_date: str | None
    status_reason: str


class InspectionCreate(BaseModel):
    """One field inspection of one hydrant, as a crew would report it."""

    model_config = ConfigDict(extra="forbid")

    hydrant_id: str = Field(description="Auditor hydrant id, e.g. '1001523'.")
    inspected_at: datetime = Field(description="When the inspection happened. Include a time-zone offset.")
    inspector: str = Field(min_length=1, max_length=80)
    static_psi: float | None = Field(default=None, ge=0, le=250, description="Static pressure, psi.")
    residual_psi: float | None = Field(default=None, ge=0, le=250, description="Residual pressure while flowing, psi.")
    flow_gpm: float | None = Field(default=None, ge=0, le=5000, description="Measured flow, gallons per minute.")
    cap_condition: CapCondition
    operable: bool = Field(description="True if the hydrant opened and closed fully.")
    leaking: bool
    notes: str = Field(default="", max_length=2000)


class Inspection(InspectionCreate):
    model_config = ConfigDict(extra="ignore")

    id: int
    source: str


class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hydrant_id: str
    kind: WorkOrderKind
    priority: Priority = "normal"
    description: str = Field(min_length=3, max_length=2000)


class WorkOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: WorkOrderStatus | None = None
    assigned_to: str | None = Field(default=None, max_length=80)
    priority: Priority | None = None


class WorkOrder(BaseModel):
    id: int
    hydrant_id: str
    kind: WorkOrderKind
    priority: Priority
    status: WorkOrderStatus
    assigned_to: str
    description: str
    created_at: datetime
    created_by: str
    closed_at: datetime | None


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)


class Jurisdiction(BaseModel):
    jurisdiction: str
    hydrants: int
    out_of_service: int


class AuditEntry(BaseModel):
    id: int
    at: datetime
    actor: str
    action: str
    entity: str
    entity_id: str
    before: dict | None
    after: dict | None
    trace_id: str
