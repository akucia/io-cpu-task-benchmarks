import logging
import os
import pathlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor

import PIL
import click
import numpy as np
from tqdm import tqdm

from mixed_io_cpu_task.cropping import crop_with_pil
from mixed_io_cpu_task.io_utils import (
    download_crops_and_image,
    save_image_buffers,
    remove_dir,
)
from mixed_io_cpu_task.logging_utils import configure_logger


def run(i, crops, input_image, output_dir):
    image_buffer, crops_to_cut = download_crops_and_image(
        crops, input_image, trace_id=str(i)
    )
    buffers = crop_with_pil(image_buffer, crops_to_cut, trace_id=str(i))
    save_image_buffers(buffers, output_dir, trace_id=str(i))


@click.command()
@click.argument("input_image", type=click.Path(path_type=str))
@click.argument("crops", type=click.Path(path_type=str))
@click.argument("output_dir", type=click.Path(path_type=str))
@click.option("--num-repeats", "-r", default=1, help="Number of repeats")
@click.option("--remove", "-rm", is_flag=True, help="Remove output dir before running")
@click.option(
    "--executor",
    "-e",
    default="thread",
    help="Executor to use",
    type=click.Choice(["thread", "process"]),
)
def multithreading(
    input_image: str,
    crops: str,
    output_dir: str,
    num_repeats: int,
    remove: bool,
    executor: str,
):
    logging.basicConfig()
    logger = logging.getLogger("default")
    log_filename = f"multi-{executor}"
    if "gs://" in output_dir:
        log_filename += "-remote"
    configure_logger(logger, log_filename)
    logger.debug(f"PIL: {PIL.__version__}")
    logger.debug(f"NumPy: {np.__version__}")
    start = time.perf_counter()
    logger.info(f"input image {input_image}, input crops {crops}")
    if remove:
        logger.debug(f"Removing output dir {output_dir}")
        remove_dir(output_dir)
    if not output_dir.startswith("gs://"):
        pathlib.Path(output_dir).mkdir(exist_ok=True, parents=True)

    logger.info(f"CPU count: {os.cpu_count()}")
    if executor == "process":
        Executor = ProcessPoolExecutor
    else:
        Executor = ThreadPoolExecutor

    with Executor(os.cpu_count() // 2) as executor:
        futures = []
        for i in range(num_repeats):
            futures.append(executor.submit(run, i, crops, input_image, output_dir))
        for future in tqdm(as_completed(futures), total=len(futures)):
            future.result()

    elapsed = time.perf_counter() - start
    logger.info(
        f"Elapsed {elapsed:.2f} seconds, average {num_repeats/elapsed:.2f} img/s"
    )
