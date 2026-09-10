from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CapProjection(Base):
    """A stored multi-year cap projection run for a team, under a specific
    (user-adjustable) set of assumptions — see the Cap Projection Engine
    (project brief section 11). Distinct from ``TeamCap``: ``TeamCap`` holds
    the single "current best assumption" sheet the rest of the app reads by
    default, while ``CapProjection`` rows are the audit trail of alternate
    what-if projections a user has run (e.g. "what if the cap only grows
    3%/year instead of 6%?").
    """

    __tablename__ = "cap_projections"
    __table_args__ = (UniqueConstraint("team_id", "season", "run_id", name="uq_projection_run_season"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    season: Mapped[int] = mapped_column(nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(nullable=False, index=True)
    """Groups every season row produced by one projection run together."""

    projected_cap: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    projected_commitments: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    projected_space: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    assumptions: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    team: Mapped["Team"] = relationship()
