import logging
import pathlib
import time

import PIL
import click
import numpy as np
from tqdm import trange

from mixed_io_cpu_task.cropping import crop_with_pil
from mixed_io_cpu_task.io_utils import (
    download_crops_and_image,
    save_image_buffers,
    remove_dir,
)

from mixed_io_cpu_task.logging_utils import configure_logger


@click.command()
@click.argument("input_image", type=click.Path(path_type=str))
@click.argument("crops", type=click.Path(path_type=str))
@click.argument("output_dir", type=click.Path(path_type=str))
@click.option("--num-repeats", "-r", default=1, help="Number of repeats")
@click.option("--remove", "-rm", is_flag=True, help="Remove output dir before running")
def serial(
    input_image: str,
    crops: str,
    output_dir: str,
    num_repeats: int,
    remove: bool,
):
    logging.basicConfig()
    logger = logging.getLogger("default")

    if "gs://" in output_dir:
        log_filename = "serial-remote"
    else:
        log_filename = "serial"
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

    for i in trange(num_repeats):
        image_buffer, crops_to_cut = download_crops_and_image(
            crops, input_image, trace_id=str(i)
        )
        buffers = crop_with_pil(image_buffer, crops_to_cut, trace_id=str(i))
        save_image_buffers(buffers, output_dir, trace_id=str(i))

    elapsed = time.perf_counter() - start
    logger.info(
        f"Elapsed {elapsed:.2f} seconds, average {num_repeats/elapsed:.2f} img/s"
    )
