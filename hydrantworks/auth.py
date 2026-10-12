"""API keys with two scopes.

    X-API-Key: <read key>   ->  GET endpoints
    X-API-Key: <write key>  ->  GET endpoints and every write

The key's role becomes the actor recorded in the audit log.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status


@dataclass(frozen=True)
class Caller:
    actor: str
    can_write: bool


def caller(request: Request, x_api_key: str | None = Header(default=None)) -> Caller:
    settings = request.app.state.settings
    if x_api_key == settings.write_key:
        return Caller(actor="writer", can_write=True)
    if x_api_key == settings.read_key:
        return Caller(actor="reader", can_write=False)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or unknown API key. Send it in the X-API-Key header.",
    )


def reader(c: Caller = Depends(caller)) -> Caller:
    return c


def writer(c: Caller = Depends(caller)) -> Caller:
    if not c.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This key is read-only. Writes need the write key.",
        )
    return c
