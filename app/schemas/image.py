import uuid
from datetime import datetime
from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: uuid.UUID
    sample_unit_id: uuid.UUID
    public_url: str
    cloudinary_public_id: str
    original_filename: str
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    format: str | None
    is_original: bool
    is_annotated: bool

    class Config:
        from_attributes = True
