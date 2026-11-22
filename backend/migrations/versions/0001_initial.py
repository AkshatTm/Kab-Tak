"""initial schema + seeds

Revision ID: 0001
Revises:
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from app.db.types import UTCDateTime

revision = "0001"
down_revision = None


def _id() -> sa.Column[str]:
    return sa.Column("id", sa.String, primary_key=True)


def _fk(col: str, target: str, nullable: bool = False) -> sa.Column[str]:
    return sa.Column(col, sa.String, sa.ForeignKey(target), nullable=nullable)


def upgrade() -> None:
    created = sa.Column("created_at", UTCDateTime, nullable=False)
    categories = op.create_table(
        "categories",
        _id(),
        sa.Column("name", sa.String, nullable=False, unique=True),
        _fk("parent_id", "categories.id", True),
        created,
    )
    part_types = op.create_table(
        "part_types",
        _id(),
        sa.Column("key", sa.String, nullable=False, unique=True),
        sa.Column("unit", sa.String, nullable=False),
        sa.Column("label", sa.String, nullable=False),
    )
    op.create_table(
        "tasks",
        _id(),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("raw_text", sa.String),
        _fk("category_id", "categories.id", True),
        sa.Column("estimate_min", sa.Integer),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("outcome", sa.String),
        sa.Column("tentative", sa.Boolean, nullable=False),
        sa.Column("familiarity", sa.String),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("created_at", UTCDateTime, nullable=False),
        sa.Column("started_at", UTCDateTime),
        sa.Column("stopped_at", UTCDateTime),
        sa.Column("active_min", sa.Float),
        sa.Column("wall_min", sa.Float),
    )
    op.create_table(
        "task_parts",
        _id(),
        _fk("task_id", "tasks.id"),
        _fk("part_type_id", "part_types.id"),
        sa.Column("planned_qty", sa.Float, nullable=False),
        sa.Column("completed_qty", sa.Float),
        sa.Column("order", sa.Integer, nullable=False),
    )
    op.create_table(
        "sessions",
        _id(),
        _fk("task_id", "tasks.id"),
        sa.Column("start_at", UTCDateTime, nullable=False),
        sa.Column("end_at", UTCDateTime),
        sa.Column("end_reason", sa.String),
    )
    op.create_table(
        "predictions",
        _id(),
        _fk("task_id", "tasks.id"),
        sa.Column("model_level", sa.String, nullable=False),
        sa.Column("model_version", sa.String, nullable=False),
        sa.Column("point_min", sa.Float, nullable=False),
        sa.Column("low_min", sa.Float, nullable=False),
        sa.Column("high_min", sa.Float, nullable=False),
        sa.Column("shown", sa.Boolean, nullable=False),
        sa.Column("created_at", UTCDateTime, nullable=False),
    )
    op.create_table(
        "corrections",
        _id(),
        sa.Column("raw_text", sa.String, nullable=False),
        sa.Column("llm_output_json", sa.JSON, nullable=False),
        sa.Column("corrected_json", sa.JSON, nullable=False),
        sa.Column("created_at", UTCDateTime, nullable=False),
    )
    op.create_table(
        "llm_calls",
        _id(),
        sa.Column("provider", sa.String, nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("ok", sa.Boolean, nullable=False),
        sa.Column("error", sa.String),
        sa.Column("prompt_tokens", sa.Integer),
        sa.Column("completion_tokens", sa.Integer),
        sa.Column("created_at", UTCDateTime, nullable=False),
    )
    settings = op.create_table(
        "settings",
        sa.Column("key", sa.String, primary_key=True),
        sa.Column("value_json", sa.JSON, nullable=False),
    )
    op.create_table(
        "events",
        _id(),
        _fk("task_id", "tasks.id", True),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("payload_json", sa.JSON),
        sa.Column("created_at", UTCDateTime, nullable=False),
    )

    now = datetime.now(UTC)
    op.bulk_insert(
        part_types,
        [
            {"id": str(uuid4()), "key": k, "unit": u, "label": k.replace("_", " ").capitalize()}
            for k, u in [
                ("video_watch", "content_min"),
                ("read_theory", "units"),
                ("handwrite_code", "problems"),
                ("implement_code", "problems"),
                ("practice_problem", "problems"),
                ("notes", "pages"),
                ("assignment", "items"),
                ("project_coding", "items"),
                ("other", "items"),
            ]
        ],
    )
    op.bulk_insert(
        categories,
        [
            {"id": str(uuid4()), "name": n, "parent_id": None, "created_at": now}
            for n in ["DSA", "Theory subject", "Assignment", "Project coding", "Admin"]
        ],
    )
    op.bulk_insert(
        settings,
        [
            {"key": "day_starts_at", "value_json": "04:00"},
            {"key": "installed_at", "value_json": now.isoformat()},
        ],
    )
