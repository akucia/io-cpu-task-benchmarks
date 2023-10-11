import asyncio
import logging
import pathlib
import time

import PIL
import click
import numpy as np
from tqdm import trange

from mixed_io_cpu_task.cropping import crop_with_pil_async
from mixed_io_cpu_task.io_utils import (
    remove_dir,
    download_crops_and_image_async,
    save_image_buffers_async,
    remove_dir_async,
)
from mixed_io_cpu_task.logging_utils import configure_logger


@click.command()
@click.argument("input_image", type=click.Path(path_type=str))
@click.argument("crops", type=click.Path(path_type=str))
@click.argument("output_dir", type=click.Path(path_type=str))
@click.option("--num-repeats", "-r", default=1, help="Number of repeats")
@click.option("--remove", "-rm", is_flag=True, help="Remove output dir before running")
def asynchronous(
    input_image: str,
    crops: str,
    output_dir: str,
    num_repeats: int,
    remove: bool,
):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _async_main(crops, input_image, num_repeats, output_dir, remove)
    )


async def _async_main(crops, input_image, num_repeats, output_dir, remove):
    # configure logger
    logging.basicConfig()
    logger = logging.getLogger("default")
    log_filename = "asynchronous"
    if "gs://" in output_dir:
        log_filename += "-remote"
    else:
        log_filename += "-local"
    configure_logger(logger, log_filename)
    logger.debug(f"PIL: {PIL.__version__}")
    logger.debug(f"NumPy: {np.__version__}")
    logger.info(f"input image {input_image}, input crops {crops}")

    # cleanup old data
    if remove and not output_dir.startswith("gs://"):
        logger.debug(f"Removing output dir {output_dir}")
        remove_dir(output_dir)
    elif remove and output_dir.startswith("gs://"):
        logger.debug(f"Removing output dir {output_dir}")
        await remove_dir_async(output_dir)
    if not output_dir.startswith("gs://"):
        pathlib.Path(output_dir).mkdir(exist_ok=True, parents=True)
    # start benchmark
    start = time.perf_counter()
    tasks = []
    for i in trange(num_repeats):
        task = _process_task_async(crops, i, input_image, output_dir)
        tasks.append(task)
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    logger.info(
        f"Elapsed {elapsed:.2f} seconds, average {num_repeats / elapsed:.2f} img/s"
    )


async def _process_task_async(crops, i, input_image, output_dir):
    image_buffer, crops_to_cut = await download_crops_and_image_async(
        crops, input_image, trace_id=str(i)
    )
    buffers = await crop_with_pil_async(image_buffer, crops_to_cut, trace_id=str(i))
    await save_image_buffers_async(buffers, output_dir, trace_id=str(i))
