import asyncio
import concurrent.futures
import logging
import pathlib
import uuid
from io import BytesIO
from shutil import rmtree
from typing import Union, List, Tuple, Optional
import os
from google.cloud import storage

from gcloud.aio.storage import Storage, Blob

from mixed_io_cpu_task.async_utils import limit_concurrency

logger = logging.getLogger("default")
storage_client = storage.Client()


def _remove_local_dir(dir: str):
    """Removes local dir"""
    logger.debug(f"Removing local dir {dir}")
    if os.path.exists(dir):
        rmtree(dir)


def _remove_gs_dir(dir: str):
    """Removes gs dir"""
    logger.debug(f"Removing gs dir {dir}")
    bucket_name = dir.split("/")[2]
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix="/".join(dir.split("/")[3:]))
    for blob in blobs:
        blob.delete()


async def _remove_gs_dir_async(dir: str):
    """Removes gs dir"""
    logger.debug(f"Removing gs dir {dir}")
    bucket_name = dir.split("/")[2]
    async with Storage() as client:
        bucket = client.get_bucket(bucket_name)
        blobs = await bucket.list_blobs(prefix="/".join(dir.split("/")[3:]))
        tasks = []
        for blob in blobs:
            task = client.delete(bucket_name, blob)
            tasks.append(task)
        await asyncio.gather(*tasks)


def remove_dir(dir: str):
    """Removes dir"""
    if dir.startswith("gs://"):
        _remove_gs_dir(dir)
    else:
        _remove_local_dir(dir)


async def remove_dir_async(dir: str):
    """Removes dir"""
    if dir.startswith("gs://"):
        await _remove_gs_dir_async(dir)
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
        f"Downloading crops csv and image",
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


async def download_crops_and_image_async(
    crops_path: str, image_path: str, trace_id: str
) -> Tuple[BytesIO, List[Tuple[int, int, int, int]]]:
    logger.debug(
        f"Downloading crops csv and image",
        extra={"trace_id": trace_id},
    )
    if image_path.startswith("gs://"):
        image_buffer = await _load_gs_image_async(image_path)
    else:
        image_buffer = _load_local_image(image_path)
    if crops_path.startswith("gs://"):
        lines = await _load_gs_crops_async(crops_path)

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


async def _load_gs_crops_async(crops_path: str) -> List[str]:
    bucket_name = crops_path.split("/")[2]
    async with Storage() as client:
        bucket = client.get_bucket(bucket_name)
        blob = await bucket.get_blob("/".join(crops_path.split("/")[3:]))
        lines = (await blob.download()).decode().split("\n")[1:]
        return lines


def _load_gs_image(image_path: str) -> BytesIO:
    bucket_name = image_path.split("/")[2]
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob("/".join(image_path.split("/")[3:]))
    image_buffer = BytesIO(blob.download_as_bytes())
    return image_buffer


async def _load_gs_image_async(image_path: str) -> BytesIO:
    bucket_name = image_path.split("/")[2]
    async with Storage() as client:
        bucket = client.get_bucket(bucket_name)
        blob: Blob = await bucket.get_blob("/".join(image_path.split("/")[3:]))
        image_buffer = BytesIO(await blob.download())
        return image_buffer


def save_image_buffers_with_threadpool(
    buffers: List[BytesIO], save_dir: str, trace_id: str, max_threads: int = None
):
    """Saves image buffers to save_dir with random uuid as filename"""
    logger.debug(
        f"Saving {len(buffers)} images to {save_dir}", extra={"trace_id": trace_id}
    )
    # use ThreadPoolExecutor to save files in parallel
    if max_threads is None:
        max_threads = os.cpu_count() // 2
    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        futures = []
        for buffer in buffers:
            filename = f"{uuid.uuid4()}.jpg"
            if save_dir.startswith("gs://"):
                task = executor.submit(_save_gs_file, buffer, save_dir, filename)
            else:
                task = executor.submit(_save_local_file, buffer, save_dir, filename)
            futures.append(task)
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            future.result()
            if i % 25 == 0:
                logger.debug(f"Saved crop {i} to storage", extra={"trace_id": trace_id})
    logger.debug(f"Saved all images", extra={"trace_id": trace_id})


def _save_local_file(buffer: BytesIO, save_dir: str, filename: str) -> str:
    with open(os.path.join(save_dir, filename), "wb") as f:
        f.write(buffer.read())
        return f.name


async def _save_local_file_async(buffer: BytesIO, save_dir: str, filename: str) -> str:
    # Use thread to save a file asynchronously
    await asyncio.to_thread(_save_local_file, buffer, save_dir, filename)


def _save_gs_file(buffer: BytesIO, save_dir: str, filename: str) -> str:
    bucket_name = save_dir.split("/")[2]
    bucket = storage_client.bucket(bucket_name)
    blob_name = "/".join(save_dir.split("/")[3:] + [filename])
    blob = bucket.blob(blob_name)
    blob.upload_from_file(buffer)
    return blob.path


async def _save_gs_file_async(buffer: BytesIO, save_dir: str, filename: str) -> str:
    bucket_name = save_dir.split("/")[2]
    async with Storage() as client:
        blob_name = "/".join(save_dir.split("/")[3:] + [filename])
        await client.upload(bucket_name, blob_name, buffer)
        return blob_name


async def save_image_buffers_async(
    buffers: List[BytesIO],
    save_dir: str,
    trace_id: str,
    max_concurrency: Optional[int] = None,
):
    """Saves image buffers to save_dir with random uuid as filename"""
    if max_concurrency is None:
        max_concurrency = os.cpu_count() // 2
    logger.debug(
        f"Saving {len(buffers)} images to save_dir", extra={"trace_id": trace_id}
    )
    tasks = []
    for buffer in buffers:
        filename = f"{uuid.uuid4()}.jpg"
        if save_dir.startswith("gs://"):
            task = _save_gs_file_async(buffer, save_dir, filename)
        else:
            task = _save_local_file_async(buffer, save_dir, filename)
        tasks.append(task)
    done_counter = 0
    async for _ in limit_concurrency(tasks, max_concurrency):
        if done_counter % 25 == 0:
            logger.debug(
                f"Saved crop {done_counter} to storage", extra={"trace_id": trace_id}
            )
        done_counter += 1

    for buffer in buffers:
        buffer.close()
        await asyncio.sleep(0)
    logger.debug(f"Saved all images", extra={"trace_id": trace_id})
