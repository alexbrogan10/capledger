from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TeamRoster(Base):
    """Links a player to a team for a given season with a roster status.

    Kept separate from ``players.team_id`` (the player's *current* team) so
    historical season-by-season rosters can be reconstructed even after a
    player has moved on.
    """

    __tablename__ = "team_rosters"
    __table_args__ = (UniqueConstraint("team_id", "player_id", "season", name="uq_roster_season"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    season: Mapped[int] = mapped_column(nullable=False, index=True)
    roster_status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    # active | practice_squad | injured_reserve | released | retired

    team: Mapped["Team"] = relationship()
    player: Mapped["Player"] = relationship()
