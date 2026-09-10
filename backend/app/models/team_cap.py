from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TeamCap(Base):
    """A team's salary-cap sheet for a single season.

    ``salary_cap`` for a past/current season is the actual league cap limit;
    for future seasons it is a user-adjustable *assumption* (see
    ``cap_projections`` / the Cap Projection Engine) and must always be
    presented to the user as such, never as a guaranteed figure.
    """

    __tablename__ = "team_cap"
    __table_args__ = (UniqueConstraint("team_id", "season", name="uq_team_cap_season"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    season: Mapped[int] = mapped_column(nullable=False, index=True)

    salary_cap: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cap_commitments: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    top51_commitments: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    dead_cap: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cap_space: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    effective_cap_space: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    carryover: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    team: Mapped["Team"] = relationship(back_populates="cap_sheets")
