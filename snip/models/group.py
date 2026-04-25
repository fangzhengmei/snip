from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Group:
    name: str
    parent_id: str | None = None
    color: str = ""
    description: str = ""
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
