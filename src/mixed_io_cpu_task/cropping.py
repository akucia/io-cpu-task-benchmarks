import asyncio
import logging
from io import BytesIO
from typing import List, Tuple

from PIL import Image


logger = logging.getLogger("default")


def crop_with_pil(
    image_buffer: BytesIO, crops_to_cut: List[Tuple[int, int, int, int]], trace_id: str
) -> List[BytesIO]:
    """Crops image with PIL encode to JPEG"""
    logger.debug(f"Opening image with PIL", extra={"trace_id": trace_id})
    image_buffer.seek(0)
    image = Image.open(image_buffer)
    buffers = []
    crops = []
    logger.debug(f"Cropping image with PIL", extra={"trace_id": trace_id})
    for x, y, w, h in crops_to_cut:
        crop = image.crop((x, y, x + w, y + h))
        crops.append(crop)
    logger.debug(f"Cut {len(crops)} crops", extra={"trace_id": trace_id})
    for crop in crops:
        buffer = BytesIO()
        crop.save(buffer, format="JPEG")
        buffer.seek(0)
        buffers.append(buffer)
    logger.debug(f"Encoded {len(buffers)} jpg images", extra={"trace_id": trace_id})
    return buffers


async def crop_with_pil_async(
    image_buffer: BytesIO, crops_to_cut: List[Tuple[int, int, int, int]], trace_id: str
) -> List[BytesIO]:
    """Crops image with PIL encode to JPEG"""
    logger.debug(f"Cropping image with PIL", extra={"trace_id": trace_id})
    image_buffer.seek(0)
    image = Image.open(image_buffer)
    await asyncio.sleep(0)
    logger.debug(f"Opened image with PIL", extra={"trace_id": trace_id})
    buffers = []
    crops = []
    for x, y, w, h in crops_to_cut:
        crop = image.crop((x, y, x + w, y + h))
        crops.append(crop)
        await asyncio.sleep(0)
    logger.debug(f"Cut {len(crops)} crops", extra={"trace_id": trace_id})
    for crop in crops:
        buffer = BytesIO()
        crop.save(buffer, format="JPEG")
        buffer.seek(0)
        buffers.append(buffer)
        await asyncio.sleep(0)
    logger.debug(f"Encoded {len(buffers)} jpg images", extra={"trace_id": trace_id})
    return buffers
