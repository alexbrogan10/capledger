from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ContractYear(Base):
    """A single season's financial breakdown within a contract.

    ``dead_cap_value`` is the amount that would accelerate onto the cap as
    dead money if the player were released/traded *before* this season,
    under a standard (non-June-1) release. It is precomputed by the cap
    engine from the contract's remaining signing-bonus proration and any
    guaranteed base salary as of this season, and is what the Release
    Calculator reads for a "release before season X" scenario.
    """

    __tablename__ = "contract_years"
    __table_args__ = (UniqueConstraint("contract_id", "season", name="uq_contract_year_season"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    season: Mapped[int] = mapped_column(nullable=False, index=True)

    base_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    signing_bonus_proration: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    roster_bonus: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    incentives: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    cap_hit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cash_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    dead_cap_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # Guaranteed base salary for this specific season (subset of the
    # contract's total guaranteed_money attributable to this year).
    guaranteed_base_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    contract: Mapped["Contract"] = relationship(back_populates="years")
