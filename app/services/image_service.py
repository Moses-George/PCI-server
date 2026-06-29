import asyncio
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.image import Image
from app.core.cloudinary_client import (
    CloudinaryUploadResult,
    delete_images_from_cloudinary,
    delete_images_from_cloudinary_sync,
)

logger = logging.getLogger(__name__)


def _image_from_result(
    sample_unit_id: UUID,
    result: CloudinaryUploadResult,
    is_original: bool,
    is_annotated: bool,
) -> Image:
    return Image(
        sample_unit_id=sample_unit_id,
        cloudinary_public_id=result.public_id,
        cloudinary_asset_id=result.asset_id,
        public_url=result.public_url,
        width=result.width,
        height=result.height,
        original_filename=result.original_filename,
        mime_type=result.mime_type,
        size_bytes=result.size_bytes,
        format=result.format,
        is_original=is_original,
        is_annotated=is_annotated,
    )


async def save_image_record(
    db: AsyncSession,
    sample_unit_id: UUID,
    result: CloudinaryUploadResult,
    is_original: bool = True,
    is_annotated: bool = False,
) -> Image:
    image = _image_from_result(sample_unit_id, result, is_original, is_annotated)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


def save_image_record_sync(
    db: Session,
    sample_unit_id: UUID,
    result: CloudinaryUploadResult,
    is_original: bool = True,
    is_annotated: bool = False,
) -> Image:
    image = _image_from_result(sample_unit_id, result, is_original, is_annotated)
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


async def delete_images_for_ids(db: AsyncSession, sample_unit_ids: list[UUID]) -> None:
    """
    Deletes all Cloudinary resources and DB rows for a list of sample unit IDs.
    Used by both section and network delete endpoints.
    """
    if not sample_unit_ids:
        return

    stmt = select(Image).where(Image.sample_unit_id.in_(sample_unit_ids))
    result = await db.execute(stmt)
    images = result.scalars().all()

    if not images:
        return

    public_ids = [img.cloudinary_public_id for img in images]

    try:
        await delete_images_from_cloudinary(public_ids)
    except RuntimeError:
        logger.error(f"Cloudinary cleanup failed for {len(public_ids)} resources — orphaned")

    for img in images:
        await db.delete(img)
    await db.commit()
    logger.info(f"Deleted {len(images)} image records for {len(sample_unit_ids)} sample units")