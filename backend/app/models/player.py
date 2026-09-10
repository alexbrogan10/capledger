from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

POSITIONS = (
    "QB", "RB", "FB", "WR", "TE",
    "LT", "LG", "C", "RG", "RT",
    "EDGE", "DT", "LB", "CB", "S",
    "K", "P", "LS",
)

# Coarse position-group buckets used throughout position-spending analytics.
POSITION_GROUPS = {
    "QB": "QB",
    "RB": "RB", "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
    "EDGE": "DL/EDGE", "DT": "DL/EDGE",
    "LB": "LB",
    "CB": "DB", "S": "DB",
    "K": "ST", "P": "ST", "LS": "ST",
}


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    age: Mapped[int] = mapped_column(nullable=False)
    experience: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    # active | injured_reserve | released | retired | free_agent

    team: Mapped["Team"] = relationship(back_populates="players")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="player")

    @property
    def position_group(self) -> str:
        return POSITION_GROUPS.get(self.position, "OTHER")
