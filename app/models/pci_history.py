from sqlalchemy import Column, Float, Integer, UUID, ForeignKey, JSON, String
from sqlalchemy.orm import relationship
from .base import BaseModel


class PCIHistory(BaseModel):
    __tablename__ = "pci_history"

    section_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    final_pci = Column(Float, nullable=False)
    condition_rating = Column(String, nullable=False)
    max_cdv = Column(Float, nullable=False)
    tdv_start = Column(Float, nullable=False)
    deduct_values = Column(JSON, nullable=True)
    observations = Column(JSON, nullable=False)
    all_cdvs = Column(JSON, nullable=False)
    all_tdvs = Column(JSON, nullable=False)

    section = relationship("Section", back_populates="pci_history")
