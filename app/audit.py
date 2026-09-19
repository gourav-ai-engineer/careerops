from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit(db: Session, *, entity_type: str, action: str, entity_id: int | None = None,
                 actor: str = "system", metadata: dict | None = None) -> AuditEvent:
    event = AuditEvent(
        entity_type=entity_type, entity_id=entity_id, action=action, actor=actor,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
