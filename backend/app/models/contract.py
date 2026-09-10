from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

CONTRACT_STATUSES = ("active", "released", "traded", "expired", "void")


class Contract(Base):
    """A player contract.

    ``current_salary`` and ``current_cap_hit`` are convenience caches of the
    contract's *most recent* ``ContractYear`` row. ``ContractYear`` is always
    the source of truth for year-by-year figures; these two columns exist so
    simple list views don't need a join, and are kept in sync by the data
    pipeline / cap engine whenever contract years are (re)computed.
    """

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)

    contract_start: Mapped[int] = mapped_column(nullable=False)  # season year, e.g. 2023
    contract_end: Mapped[int] = mapped_column(nullable=False)  # season year, e.g. 2026

    total_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    annual_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # AAV
    guaranteed_money: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    signing_bonus: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    current_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    current_cap_hit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    contract_status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    player: Mapped["Player"] = relationship(back_populates="contracts")
    team: Mapped["Team"] = relationship(back_populates="contracts")
    years: Mapped[list["ContractYear"]] = relationship(
        back_populates="contract", order_by="ContractYear.season", cascade="all, delete-orphan"
    )

    @property
    def years_total(self) -> int:
        return self.contract_end - self.contract_start + 1
