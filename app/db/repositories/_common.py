from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session


def serialize_payload(raw_payload: dict | str | None) -> str | None:
    if raw_payload is None:
        return None
    if isinstance(raw_payload, str):
        return raw_payload
    return json.dumps(raw_payload, ensure_ascii=False)


def persist_row(db: Session, row: Any, *, auto_commit: bool) -> Any:
    db.add(row)
    if auto_commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row
