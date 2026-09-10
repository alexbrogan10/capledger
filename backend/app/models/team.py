from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(4), unique=True, nullable=False, index=True)
    conference: Mapped[str] = mapped_column(String(3), nullable=False)  # AFC / NFC
    division: Mapped[str] = mapped_column(String(16), nullable=False)  # North/South/East/West

    players: Mapped[list["Player"]] = relationship(back_populates="team")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="team")
    cap_sheets: Mapped[list["TeamCap"]] = relationship(back_populates="team")
