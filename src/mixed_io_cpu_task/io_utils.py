import logging
import pathlib
import uuid
from io import BytesIO
from shutil import rmtree
from typing import Union, List, Tuple
import os
from google.cloud import storage


logger = logging.getLogger("default")
storage_client = storage.Client()


def _remove_local_dir(dir: str):
    """Removes local dir"""
    logger.debug(f"Removing local dir {dir}")
    rmtree(dir)


def _remove_gs_dir(dir: str):
    """Removes gs dir"""
    logger.debug(f"Removing gs dir {dir}")
    bucket_name = dir.split("/")[2]
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix="/".join(dir.split("/")[3:]))
    for blob in blobs:
        blob.delete()


def remove_dir(dir: str):
    """Removes dir"""
    if dir.startswith("gs://"):
        _remove_gs_dir(dir)
    else:
        _remove_local_dir(dir)


def _load_local_image(image: Union[pathlib.Path, str]) -> BytesIO:
    """Loads image and returns bytes IO buffer"""
    with open(image, "rb") as f:
        image = f.read()
    image_buffer = BytesIO(image)
    image_buffer.seek(0)
    return image_buffer


def download_crops_and_image(
    crops_path: str, image_path: str, trace_id: str
) -> Tuple[BytesIO, List[Tuple[int, int, int, int]]]:
    logger.debug(
        f"Downloading crops {crops_path} and image {image_path}",
        extra={"trace_id": trace_id},
    )
    if image_path.startswith("gs://"):
        image_buffer = _load_gs_image(image_path)
    else:
        image_buffer = _load_local_image(image_path)
    if crops_path.startswith("gs://"):
        lines = _load_gs_crops(crops_path)

    else:
        lines = _load_local_crops(crops_path)
    crops_to_cut = [tuple(map(int, line.split(","))) for line in lines if line]
    logger.debug(f"Loaded {len(crops_to_cut)} crops", extra={"trace_id": trace_id})
    return image_buffer, crops_to_cut


def _load_local_crops(crops_path: Union[str, pathlib.Path]) -> List[str]:
    with open(crops_path, "r") as f:
        lines = f.readlines()[1:]
    return lines


def _load_gs_crops(crops_path: str) -> List[str]:
    bucket_name = crops_path.split("/")[2]
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob("/".join(crops_path.split("/")[3:]))
    lines = blob.download_as_bytes().decode().split("\n")[1:]
    return lines


def _load_gs_image(image_path: str) -> BytesIO:
    bucket_name = image_path.split("/")[2]
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob("/".join(image_path.split("/")[3:]))
    image_buffer = BytesIO(blob.download_as_bytes())
    return image_buffer


def save_image_buffers(buffers: List[BytesIO], save_dir: str, trace_id: str):
    """Saves image buffers to save_dir with random uuid as filename"""
    logger.debug(
        f"Saving {len(buffers)} images to {save_dir}", extra={"trace_id": trace_id}
    )
    for i, buffer in enumerate(buffers):
        filename = f"{uuid.uuid4()}.jpg"
        if save_dir.startswith("gs://"):
            _save_gs_file(buffer, save_dir, filename)
        else:
            _save_local_file(buffer, save_dir, filename)
        # log every 10 images:
        if i % 10 == 0:
            logger.debug(f"Saved crop {i} to storage", extra={"trace_id": trace_id})
        buffer.close()
    logger.debug(f"Saved {len(buffers)} images", extra={"trace_id": trace_id})


def _save_local_file(buffer: BytesIO, save_dir: str, filename: str) -> str:
    with open(os.path.join(save_dir, filename), "wb") as f:
        f.write(buffer.read())
        return f.name


def _save_gs_file(buffer: BytesIO, save_dir: str, filename: str) -> str:
    bucket_name = save_dir.split("/")[2]
    bucket = storage_client.bucket(bucket_name)
    blob_name = "/".join(save_dir.split("/")[3:] + [filename])
    blob = bucket.blob(blob_name)
    blob.upload_from_file(buffer)
    return blob.path
