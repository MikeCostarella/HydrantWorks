"""Shared FastAPI dependencies."""

from __future__ import annotations

import sqlite3

from fastapi import Query, Request


def get_conn(request: Request) -> sqlite3.Connection:
    return request.app.state.conn


def trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", "")


class Paging:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number."),
        size: int = Query(50, ge=1, le=500, description="Items per page."),
    ):
        self.page = page
        self.size = size
