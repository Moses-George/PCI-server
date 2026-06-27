from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class PCIObservation(BaseModel):
    distress_type: str
    severity: str
    density: float
    count: int
    deduct_value: float


class PCIRequest(BaseModel):
    section_id: UUID


class PCIResponse(BaseModel):
    section_id: UUID
    final_pci: float
    condition_rating: str
    max_cdv: float
    tdv_start: float
    deduct_values: List[float]
    observations: List[PCIObservation]
    all_cdvs: List[float]
    all_tdvs: List[float]
    calculated_at: datetime


class PCIHistoryResponse(PCIResponse):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
