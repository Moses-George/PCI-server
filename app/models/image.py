import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Column
from sqlalchemy.orm import relationship
from .base import BaseModel  # your declarative base


class Image(BaseModel):
    __tablename__ = "images"

    sample_unit_id = Column(
        ForeignKey("sample_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # R2 storage info
    cloudinary_public_id = Column(String, nullable=False, unique=True)
    cloudinary_asset_id = Column(String, nullable=True)
    public_url = Column(String, nullable=False)

    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # File metadata
    original_filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    format = Column(String, nullable=True)  # jpg, png, etc

    # Image role
    is_original = Column(Boolean, default=True)
    is_annotated = Column(Boolean, default=False)

    # Relationship back to SampleUnit
    sample_unit = relationship("SampleUnit", back_populates="images")
