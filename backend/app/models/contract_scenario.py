from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

CAP_ENGINE_VERSION = "cap-engine-v1.0"


class ContractScenario(Base):
    """An audit record of one simulated scenario (release, restructure,
    extension, or trade). Every scenario endpoint writes one of these rows
    so a past "what if" run stays reproducible: the exact assumptions and
    the exact result are both preserved, tagged with the cap-engine version
    that produced them (see project brief section 43, Auditability).
    """

    __tablename__ = "contract_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)

    scenario_type: Mapped[str] = mapped_column(String(24), nullable=False)
    # release | restructure | extension | trade

    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default=CAP_ENGINE_VERSION)
    assumptions: Mapped[dict] = mapped_column(JSON, nullable=False)
    results: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    player: Mapped["Player"] = relationship()
    team: Mapped["Team"] = relationship()
    contract: Mapped["Contract"] = relationship()
