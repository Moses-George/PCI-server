import uuid

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from uuid import UUID
import os
import shutil
from datetime import datetime
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.models.detection_result import DetectionResult
from app.models.sample_unit import SampleUnit
from app.models.section import Section
from app.schemas.sample_unit import (
    SampleUnitCreate,
    SampleUnitUpdate,
    SampleUnitResponse,
)
from app.services.pci.pci_utilities import normalizeClass
import logging

from app.tasks.yolo_tasks import run_yolo_inference

logging.basicConfig(level=logging.INFO)


router = APIRouter(prefix="/sample-units", tags=["Sample Units"])


# @router.get("/section/{section_id}", response_model=List[SampleUnitResponse])
# async def get_sample_units_by_section(
#     section_id: UUID, db: AsyncSession = Depends(get_db)
# ):
#     stmt = (
#         select(SampleUnit)
#         .where(SampleUnit.section_id == section_id)
#         .options(selectinload(SampleUnit.detections))   # Eager load detections
#         .order_by(SampleUnit.created_at.desc())
#     )
#     result = await db.execute(stmt)
#     return result.scalars().all()


from sqlalchemy.orm import selectinload


@router.post(
    "/", response_model=SampleUnitResponse, status_code=status.HTTP_201_CREATED
)
async def create_sample_unit(
    section_id: UUID = Form(...),
    name: str = Form(...),
    distress_type: Optional[str] = Form(None),
    severity: Optional[str] = Form(None),
    pothole_depth: Optional[float] = Form(None),
    note: Optional[str] = Form(None),
    pixel_to_mm_factor: Optional[float] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    # Validation: either image or distress_type must be provided
    # Clean and normalize optional fields
    distress_type = distress_type.strip() if distress_type else None
    severity = severity.strip() if severity else None

    # Treat "null" as None (in case it slips through)
    if distress_type == "null":
        distress_type = None
    if severity == "null":
        severity = None

    # Validation
    has_file = image_file is not None and image_file.filename
    has_manual = distress_type is not None and distress_type != ""

    if not has_file and not has_manual:
        raise HTTPException(
            status_code=400,
            detail="Either select an image or manually specify distress type and severity.",
        )
    if has_manual and not severity:
        raise HTTPException(
            status_code=400,
            detail="Please select a severity level for the distress.",
        )

    # Verify section exists
    section = await db.get(Section, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Handle optional image upload
    original_image_path = None
    if image_file and image_file.filename:
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        file_ext = os.path.splitext(image_file.filename)[1]
        filename = (
            f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{file_ext}"
        )
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        original_image_path = os.path.join(os.getcwd(), filepath)

    # Normalize distress type
    normalized_class = normalizeClass(distress_type) if distress_type else None

    # Create sample unit
    db_sample = SampleUnit(
        section_id=section_id,
        name=name,
        distress_type=distress_type,
        severity=severity,
        pothole_depth=pothole_depth,
        note=note,
        pixel_to_mm_factor=pixel_to_mm_factor or section.pixel_to_mm_factor,
        original_image=original_image_path,
        normalized_class=normalized_class,
    )
    db.add(db_sample)
    section.sample_unit_count += 1
    await db.commit()
    await db.refresh(db_sample)  # load scalar fields

    if image_file and image_file.filename:
        # Run YOLO simulation (creates detections)
        run_yolo_inference.delay(str(db_sample.id))

    # ✅ Re‑fetch the sample unit with detections eagerly loaded
    stmt = (
        select(SampleUnit)
        .where(SampleUnit.id == db_sample.id)
        .options(selectinload(SampleUnit.detections))
    )
    result = await db.execute(stmt)
    db_sample = result.scalar_one()

    return db_sample


# @router.patch("/{sample_unit_id}", response_model=SampleUnitResponse)
# async def update_sample_unit(
#     sample_unit_id: UUID, update: SampleUnitUpdate, db: AsyncSession = Depends(get_db)
# ):
#     sample = await db.get(SampleUnit, sample_unit_id)
#     if not sample:
#         raise HTTPException(status_code=404, detail="Sample unit not found")
#     for key, value in update.model_dump(exclude_unset=True).items():
#         setattr(sample, key, value)
#     await db.commit()
#     await db.refresh(sample)
#     return sample


@router.patch("/{sample_unit_id}", response_model=SampleUnitResponse)
async def update_sample_unit(
    sample_unit_id: UUID,
    name: str = Form(...),
    distress_type: Optional[str] = Form(None),
    severity: Optional[str] = Form(None),
    pothole_depth: Optional[float] = Form(None),
    note: Optional[str] = Form(None),
    pixel_to_mm_factor: Optional[float] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch existing sample unit
    sample = await db.get(SampleUnit, sample_unit_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample unit not found")

    # 2. Build update dict from provided fields
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if distress_type is not None:
        update_data["distress_type"] = distress_type
        normalized_class = normalizeClass(distress_type)
        update_data["normalized_class"] = normalized_class
    if severity is not None:
        update_data["severity"] = severity
    if pothole_depth is not None:
        update_data["pothole_depth"] = pothole_depth
    if note is not None:
        update_data["note"] = note
    if pixel_to_mm_factor is not None:
        update_data["pixel_to_mm_factor"] = float(pixel_to_mm_factor)

    # Apply updates
    print(update_data)
    for key, value in update_data.items():
        setattr(sample, key, value)

    # 3. Handle image replacement
    if image_file and image_file.filename:
        # Delete old image file if it exists on disk
        if sample.original_image and os.path.exists(sample.original_image):
            os.remove(sample.original_image)

        # Save new image
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        file_ext = os.path.splitext(image_file.filename)[1]
        filename = (
            f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{file_ext}"
        )
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)

        sample.original_image = os.path.join(os.getcwd(), filepath)
        sample.predicted_image = None  # will be set by inference

        # Delete all existing detection results for this sample unit
        await db.execute(
            delete(DetectionResult).where(
                DetectionResult.sample_unit_id == sample_unit_id
            )
        )

        # Run inference on the new image (simulated YOLO)
        run_yolo_inference.delay(str(sample.id))

    # 4. Commit changes
    await db.commit()
    await db.refresh(sample)  # refresh scalar fields

    # 5. Re-fetch with detections eager‑loaded to avoid greenlet errors
    stmt = (
        select(SampleUnit)
        .where(SampleUnit.id == sample_unit_id)
        .options(selectinload(SampleUnit.detections))
    )
    result = await db.execute(stmt)
    sample = result.scalar_one()

    return sample


@router.delete("/{sample_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample_unit(sample_unit_id: UUID, db: AsyncSession = Depends(get_db)):
    sample = await db.get(SampleUnit, sample_unit_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample unit not found")
    # Optionally delete image files
    await db.delete(sample)
    section = await db.get(Section, sample.section_id)
    if section.sample_unit_count > 0:
        section.sample_unit_count -= 1
    await db.commit()
